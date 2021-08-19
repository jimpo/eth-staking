"""
The module exporting the ValidatorSupervisor.

This module is the main interface for the validator supervisor which is the top level object
managing the Ethereum 2.0 validator and other supporting subprocesses, as well as the remote
control RPC interface.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os.path
import shutil
from ssl import SSLContext
import tempfile
from typing import Dict, List, Optional, Union

from .backup_archive import BackupArchive, LockedArchiveCorrupted, make_validator_data_backup
from .config import Config
from .exceptions import ValidatorRunning, UnlockRequired
from .key_ops import RootKey, IncorrectPassword
from .promtail import Promtail
from .rpc.server import RpcServer, RpcTarget
from .ssh import SSHForward, SSHClient, SSHTunnel, TcpSocket, UnixSocket
from .subprocess import start_supervised, start_supervised_multi
from .validators import LighthouseValidator, ValidatorRunner

LOG = logging.getLogger(__name__)

CANONICAL_DIR_NAME = 'canonical'
SSH_KNOWN_HOSTS_FILENAME = 'ssh_known_hosts'
CONTROL_RPC_SOCKNAME = 'rpc.sock'
RETRY_DELAY = 10


class ScpFailure(Exception):
    pass


class OutOfPorts(Exception):
    pass


class ValidatorSupervisor(RpcTarget):
    """
    ValidatorSupervisor is the top level object managing the Ethereum 2.0 validator and other
    supporting subprocesses, as well as the remote control RPC interface.

    The ValidatorSupervisor initializes and supervises a number of subprocesses, such as SSH
    connections, restarting them if they error or go down. The supervisor opens SSH connections to
    all remote nodes for forwarding local logs to Loki using Promtail and creating a reverse SSH
    tunnel from the remote node to the local JSON-RPC over TCP interface. The supervisor also
    configures and starts the Promtail process and the RPC interface. Most importantly, the
    supervisor selects one remote node at a time to create a SSH tunnel to the beacon node and runs
    a local Ethereum 2.0 validator which connects to the beacon node through that tunnel.

    The ValidatorSupervisor also loads and saves archives of the validator state, which are
    encrypted by a key that is only ever stored in RAM on the validator machine. The decryption key
    is provided on initialization, and the supervisor loads the latest backup on startup and saves
    the latest validator state to a new archive on shutdown. These archives are timestamped and
    stored both locally on disk and uploaded to the remote nodes via SCP.
    """

    _root_key: Optional[RootKey]
    _backup_key: Optional[bytes]
    _validator: ValidatorRunner
    _exit_event: asyncio.Event

    def __init__(
            self,
            config: Config,
            root_key: Optional[RootKey],
            exit_event: asyncio.Event,
            enable_promtail: bool = False,
    ):
        self.nodes = config.nodes
        self.config = config
        self.root_key = root_key
        self._next_port, self._end_port = config.port_range

        if not config.nodes:
            raise ValueError("config must have at least one node")

        self._validator_data_tmpdir = tempfile.TemporaryDirectory(
            prefix='validator_supervisor-validator_data',
            dir='/dev/shm',  # Create tempdir in tmpfs
        )
        self._validator_canonical_dir = \
            os.path.join(self._validator_data_tmpdir.name, CANONICAL_DIR_NAME)

        known_hosts_file = os.path.join(self.config.data_dir, SSH_KNOWN_HOSTS_FILENAME)
        known_hosts_lock = asyncio.Lock()
        self.rpc_sock_path = os.path.abspath(
            os.path.join(self.config.data_dir, CONTROL_RPC_SOCKNAME),
        )

        port_maps: List[List[Union[SSHForward]]] = [
            [
                SSHForward(TcpSocket.localhost(self._alloc_port()), TcpSocket('prysm', 3500)),
                SSHForward(TcpSocket.localhost(self._alloc_port()), TcpSocket('prysm', 4000)),
                SSHForward(TcpSocket.localhost(self._alloc_port()), TcpSocket('lighthouse', 5052)),
                SSHForward(TcpSocket.localhost(self._alloc_port()), TcpSocket('loki', 3100)),
                # Reverse tunnel to local SSH server
                SSHForward(TcpSocket.localhost(22), TcpSocket.localhost(2222), reverse=True),
                # Reverse tunnel to RPC server
                SSHForward(UnixSocket(self.rpc_sock_path), TcpSocket.localhost(8000), reverse=True),
            ]
            for _ in self.config.nodes
        ]
        _prysm_gateway_tunnels, _prysm_rpc_tunnels, lighthouse_rpc_tunnels, loki_tunnels, _, _ = \
            zip(*port_maps)
        self._ssh_clients = [
            SSHClient(node, known_hosts_file, known_hosts_lock)
            for node in config.nodes
        ]
        self._ssh_tunnels = [
            SSHTunnel(client, tunnels)
            for client, tunnels in zip(self._ssh_clients, port_maps)
        ]
        if enable_promtail:
            log_paths = {
                'validator_supervisor': self.config.supervisor_log_path,
                'lighthouse': self.config.lighthouse_log_path,
                'prysm': self.config.prysm_log_path,
            }
            self._promtails = [
                Promtail(
                    node.host,
                    forward.local.port,
                    self.config.logs_dir,
                    log_paths,
                )
                for node, forward in zip(config.nodes, loki_tunnels)
            ]
        else:
            LOG.debug("Promtail disabled")
            self._promtails = []
        self._validator = LighthouseValidator(
            self.eth2_network,
            os.path.join(self._validator_canonical_dir),
            out_log_filepath=self.config.lighthouse_log_path,
            err_log_filepath=self.config.lighthouse_log_path,
            beacon_node_ports=[tunnel.local.port for tunnel in lighthouse_rpc_tunnels],
        )
        self._validator_stop_event = asyncio.Event()
        self._validator_task: Optional[asyncio.Task] = None

        ssl = None
        if config.ssl_cert_file:
            ssl = SSLContext()
            ssl.load_cert_chain(config.ssl_cert_file, config.ssl_key_file)
        self._rpc_server = RpcServer(self, config.rpc_users, self.rpc_sock_path, ssl)
        self._exit_event = exit_event

    def _alloc_port(self) -> int:
        if self._next_port == self._end_port:
            raise OutOfPorts()
        port = self._next_port
        self._next_port += 1
        return port

    @property
    def eth2_network(self) -> str:
        """The name of the Ethereum 2.0 network to validate on. (eg. mainnet, pyrmont, etc.)"""
        return self.config.eth2_network

    async def run(self) -> None:
        """
        Activate the supervisor, starting the RPC server, SSH tunnels, and other subprocesses.

        If the supervisor is already unlocked, this starts the validator subprocess as well.

        See class documentation for supervisor responsibilities.
        """
        await self._rpc_server.start()

        stop_ssh_tunnels = asyncio.Event()
        ssh_tunnel_tasks = await start_supervised_multi(
            [(f"SSH tunnel to {ssh_tunnel.client.node}", ssh_tunnel)
             for ssh_tunnel in self._ssh_tunnels],
            RETRY_DELAY,
            stop_ssh_tunnels,
        )

        stop_promtails = asyncio.Event()
        promtail_tasks = await start_supervised_multi(
            [(f"promtail to {promtail.node}", promtail) for promtail in self._promtails],
            RETRY_DELAY,
            stop_promtails,
        )

        try:
            await self.start_validator()
        except UnlockRequired:
            LOG.info("Waiting for supervisor to be unlocked")

        await self._exit_event.wait()
        LOG.debug("Exiting")

        # Shutdown time.
        await self._rpc_server.stop()
        await self.stop_validator()

        # Give Promtail a bit of time to finish uploading logs.
        await asyncio.sleep(3)

        LOG.debug("Stopping Promtails")
        stop_promtails.set()
        if promtail_tasks:
            await asyncio.wait(promtail_tasks)

        LOG.debug("Stopping SSH tunnels")
        stop_ssh_tunnels.set()
        if ssh_tunnel_tasks:
            await asyncio.wait(ssh_tunnel_tasks)

        self._validator_data_tmpdir.cleanup()

    async def load_backup(self) -> bool:
        """
        Load the latest backup archive containing validator state.

        This checks all reachable remote nodes for backups as well as the backup stored locally,
        then decrypts and unpacks the most recent.

        :return: whether a backup archive was successfully found and loaded
        :raises UnlockRequired: if supervisor needs to be unlocked
        :raises ValidatorRunning: if the validator is currently running
        """
        if self._backup_key is None:
            raise UnlockRequired()
        if self._validator.is_running():
            raise ValidatorRunning()

        latest_backup = None
        if os.path.isfile(self._backup_path):
            with open(self._backup_path, 'rb') as f:
                try:
                    LOG.info(f"On disk backup {self._backup_path} len is {len(f.read())}")
                    f.seek(0)
                    latest_backup = BackupArchive.unlock(self._backup_key, f)
                except LockedArchiveCorrupted:
                    LOG.error("On disk backup is corrupt!")

        for client in self._ssh_clients:
            with tempfile.NamedTemporaryFile(prefix="supervisor-backup", suffix=".bin", mode="w+b") as downloaded_f:
                try:
                    remote_path = f"~/{self._backup_filename}"
                    if not await client.copy_remote_to_local(remote_path, downloaded_f.name):
                        LOG.warning(f"Failed to download scp backup from {client.node}")
                        continue

                    downloaded_f.seek(0)
                    LOG.info(f"Downloaded len is {len(downloaded_f.read())}")
                    downloaded_f.seek(0)
                    new_backup = BackupArchive.unlock(self._backup_key, downloaded_f)
                    if latest_backup is None or latest_backup.timestamp < new_backup.timestamp:
                        latest_backup = new_backup
                        shutil.copy(downloaded_f.name, self._backup_path)
                except LockedArchiveCorrupted:
                    LOG.warning(f"Backup archive on node {client.node} is corrupt!")

        if latest_backup is None:
            LOG.error("Could not find any valid backups")
            return False

        backup_time = datetime.datetime.fromtimestamp(latest_backup.timestamp)
        LOG.info(f"Loading backup from {backup_time.isoformat()}")
        latest_backup.unpack(self._validator_canonical_dir)
        return True

    async def save_backup(self) -> None:
        """
        Save the current validator state to a backup archive.

        This saves the new encrypted archive persistently and uploads to all reachable remote
        nodes via SCP.

        :raises UnlockRequired: if supervisor needs to be unlocked
        :raises ValidatorRunning: if the validator is currently running
        """
        if self._backup_key is None:
            raise UnlockRequired()
        if self._validator.is_running():
            raise ValidatorRunning()

        LOG.debug(f"Saving backup to {self._backup_filename}")
        make_validator_data_backup(self._backup_key, self._backup_path, self._validator_canonical_dir)
        for client in self._ssh_clients:
            remote_path = f"~/{self._backup_filename}"
            if await client.copy_local_to_remote(self._backup_path, remote_path):
                LOG.debug(f"Uploaded scp backup to {client.node}")
            else:
                LOG.warning(f"Failed to upload scp backup to {client.node}")

    async def start_validator(self) -> bool:
        """
        Start the validator subprocess.

        Loads the latest backup before launching.

        :return: true if validator was not running and is now started, false if already running
        :raises UnlockRequired: if the supervisor is not unlocked
        """
        if self._validator_task is not None:
            return False

        await self.load_backup()
        self._validator_stop_event = asyncio.Event()
        self._validator_task = await start_supervised(
            'validator',
            self._validator,
            RETRY_DELAY,
            self._validator_stop_event,
        )
        return True

    async def stop_validator(self) -> bool:
        """
        Stop the validator subprocess if currently running.

        Saves the latest backup after exiting.

        :return: true if validator was running and is now stopped, false if not running
        """
        if self._validator_task is None:
            return False

        self._validator_stop_event.set()
        await self._validator_task
        self._validator_task = None
        await self.save_backup()
        return True

    async def connect_eth2_node(self, host: str, port: Optional[int]):
        """
        Connect the validator to the beacon node running on a particular remote host.

        This only prioritizes this specified node. If the host:port destination is either not in
        the config file or not reachable, the supervisor will fall back to another configured
        beacon node.

        :param host: the hostname or IP address of the destination
        :param port: the port to the SSH server on the destination
        """
        # TODO: implement this
        pass

    async def get_health(self) -> Dict[str, object]:
        """
        Returns a dictionary of supervisor status info.

        :return: a dictionary of status info
        """
        return {
            'unlocked': self.root_key is not None,
            'validator_running': self._validator_task is not None,
        }

    async def unlock(self, password: str) -> bool:
        """
        Unlock the root key with the password.

        Required to load backups and start validator.

        :param password: the password
        :return: true if unlock was successful, false on incorrect password
        """
        try:
            self.root_key = self.config.key_desc.open(password)
            return True
        except IncorrectPassword:
            return False

    async def shutdown(self) -> None:
        """Executes the poweroff command on the system and powers down the machine."""
        asyncio.create_task(self._poweroff_command())

    async def _poweroff_command(self) -> None:
        LOG.info("Executing poweroff to shut down the host")
        proc = await asyncio.create_subprocess_exec("poweroff")
        await proc.wait()
        LOG.info(f"poweroff exited with status {proc.returncode}")

    @property
    def _backup_filename(self):
        return self.config.backup_filename

    @property
    def _backup_path(self) -> str:
        return os.path.join(self.config.data_dir, self._backup_filename)

    @property
    def root_key(self) -> Optional[RootKey]:
        return self._root_key

    @root_key.setter
    def root_key(self, root_key: Optional[RootKey]):
        self._root_key = root_key
        if root_key is None:
            self._backup_key = None
        else:
            self._backup_key = root_key.derive_backup_key()
