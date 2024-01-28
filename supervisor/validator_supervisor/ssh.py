"""
SSH bastion node client and SSH tunnel subprocess.
"""

from __future__ import annotations

import asyncio
from asyncio.subprocess import Process
from dataclasses import dataclass
import logging
import re
from subprocess import PIPE, DEVNULL
from typing import Iterable, IO, List, Optional, Union

from .exceptions import InvalidSSHPubkey
from .subprocess import SimpleSubprocess
from .util import set_sighup_on_parent_exit

SSH_DEFAULT_PORT = 22
"SSH protocol default port"

DEFAULT_BASTION_SSH_USER = 'somebody'
DEFAULT_BASTION_SSH_PORT = 2222
"SSH port that remote public node bastion listens on"

LOG = logging.getLogger(__name__)


class SSHKeyscanFailure(Exception):
    pass


@dataclass
class TcpSocket:
    addr: str
    port: int

    @classmethod
    def localhost(cls, port: int) -> TcpSocket:
        return cls('localhost', port)

    def __str__(self) -> str:
        return f"{self.addr}:{self.port}"


@dataclass
class UnixSocket:
    path: str

    def __str__(self) -> str:
        return self.path


Socket = Union[TcpSocket, UnixSocket]


@dataclass
class SSHForward:
    local: Socket
    remote: Socket
    reverse: bool = False

    def ssh_flags(self) -> List[str]:
        if self.reverse:
            return ['-R', f"{self.remote}:{self.local}"]
        else:
            return ['-L', f"{self.local}:{self.remote}"]

    def __str__(self) -> str:
        if self.reverse:
            arrow = "<-"
        else:
            arrow = "->"
        return f"{self.local}{arrow}{self.remote}"


@dataclass
class SSHConnInfo:
    """
    Specification for connections to an SSH bastion node.
    """
    host: str
    "host domain name or IP address"

    user: str = DEFAULT_BASTION_SSH_USER
    port: int = DEFAULT_BASTION_SSH_PORT
    pubkey: Optional[str] = None
    "optional static SSH host public key"

    identity_file: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.user}@{self.host}:{self.port}"


class SSHClient(object):
    """
    A bastion SSH client.

    We pin host keys and modify the known_hosts carefully here. Since SSH usually has an
    interactive process for accepting SSH host keys and modifying known_hosts files, the client has
    extra logic to add host keys to a separate known_hosts file before connecting. The SSHConnInfo
    may have a host public key configured, in which case it is added to the known_hosts file,
    removing any existing entries. Otherwise, this uses ssh-keyscan, trusting on first use (TOFU).
    """
    def __init__(self, node: SSHConnInfo, known_hosts_file: str, known_hosts_lock: asyncio.Lock):
        self.node = node
        self.known_hosts_file = known_hosts_file
        self.known_hosts_lock = known_hosts_lock

    async def copy_remote_to_local(self, remote_path: str, local_path: str) -> bool:
        return await self._copy(remote_path, local_path, True)

    async def copy_local_to_remote(self, local_path: str, remote_path: str) -> bool:
        return await self._copy(remote_path, local_path, False)

    async def _copy(self, remote_path: str, local_path: str, remote_to_local: bool) -> bool:
        if not await self.check_host_key():
            return False

        cmd = [
            'scp',
            '-o', f"UserKnownHostsFile={self.known_hosts_file}",
            '-o', 'IdentitiesOnly=yes',
        ]
        if self.node.identity_file:
            cmd.extend(['-i', self.node.identity_file])
        if self.node.port != SSH_DEFAULT_PORT:
            cmd.extend(['-P', str(self.node.port)])

        full_remote_path = f"{self.node.user}@{self.node.host}:{remote_path}"
        if remote_to_local:
            cmd.append(full_remote_path)
            cmd.append(local_path)
        else:
            cmd.append(local_path)
            cmd.append(full_remote_path)

        proc = await asyncio.create_subprocess_exec(*cmd)
        retcode = await proc.wait()
        if retcode != 0:
            cmd_str = " ".join(cmd)
            LOG.warning(f"Command \"{cmd_str}\" failed with status {retcode}")
            return False
        return True

    async def check_host_key(self) -> bool:
        async with self.known_hosts_lock:
            proc = await asyncio.create_subprocess_exec(
                "ssh-keygen", "-f", self.known_hosts_file, "-F", self._known_hosts_ssh_host,
                stdout=PIPE,
                stderr=DEVNULL,
            )
            stdout, _stderr = await proc.communicate()
            if proc.returncode == 0:
                configured_pubkey = self._configured_pubkey()
                if not configured_pubkey or configured_pubkey.encode() in stdout:
                    return True

                # Remove the existing known_hosts entry for this endpoint
                proc = await asyncio.create_subprocess_exec(
                    "ssh-keygen", "-f", self.known_hosts_file, "-R", self._known_hosts_ssh_host,
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                )
                await proc.wait()

            try:
                await self._register_host_key()
            except SSHKeyscanFailure as err:
                LOG.warning(err)
                return False
            return True

    async def _register_host_key(self) -> None:
        configured_pubkey = self._configured_pubkey()
        if configured_pubkey:
            line = f"{self._known_hosts_ssh_host} {configured_pubkey}\n".encode()
        else:
            line = await self._ssh_keyscan()

        with open(self.known_hosts_file, 'ab') as f:
            f.write(line)

    async def _ssh_keyscan(self) -> bytes:
        cmd = ["ssh-keyscan", "-t", "ed25519"]
        if self.node.port != SSH_DEFAULT_PORT:
            cmd.extend(["-p", str(self.node.port)])
        cmd.append(self.node.host)
        cmd_str = ' '.join(cmd)

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise SSHKeyscanFailure(f"{cmd_str} failed with status {proc.returncode}: {stderr!r}")
        if not stdout:
            raise SSHKeyscanFailure(f"{cmd_str} exited with no output")
        return stdout

    def _configured_pubkey(self) -> Optional[str]:
        pubkey_raw = self.node.pubkey
        if not pubkey_raw:
            return None

        # Ignore the comment that may follow the pubkey.
        match = re.match(r"[a-z0-9\-]+ \S+", pubkey_raw)
        if not match:
            raise InvalidSSHPubkey(self.node.pubkey)
        return match[0]

    def ssh_command(self, forwards: Iterable[SSHForward]) -> List[str]:
        cmd = [
            'ssh',
            '-o', f"UserKnownHostsFile={self.known_hosts_file}",
        ]
        if self.node.identity_file:
            cmd.extend([
                '-i', self.node.identity_file,
                '-o', 'IdentitiesOnly=yes',
            ])
        if self.node.port != 22:
            cmd.extend(['-p', str(self.node.port)])
        for tunnel in forwards:
            cmd.extend(tunnel.ssh_flags())
        cmd.append(f"{self.node.user}@{self.node.host}")
        return cmd

    @property
    def _known_hosts_ssh_host(self) -> str:
        if self.node.port == SSH_DEFAULT_PORT:
            return self.node.host
        else:
            return f"[{self.node.host}]:{self.node.port}"


class SSHTunnel(SimpleSubprocess):
    """
    A subprocess which opens an SSH tunnel with several port forwards.
    """

    def __init__(self, client: SSHClient, forwards: List[SSHForward]):
        super().__init__(out_log_filepath=None, err_log_filepath=None)
        self.client = client
        self.forwards = forwards

    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        if not await self.client.check_host_key():
            return None

        cmd = self.client.ssh_command(self.forwards)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=DEVNULL,
            preexec_fn=set_sighup_on_parent_exit
        )

        # Tell type checker that stdout is defined since stdout=PIPE in create_subprocess_exec call.
        assert proc.stdout is not None
        # Block waiting for the first character to be printed, signifying the connection is open.
        await proc.stdout.read(1)

        if proc.returncode is not None:
            cmd_str = ' '.join(cmd)
            LOG.warning(f"\"{cmd_str}\" exited with status {proc.returncode}")
        else:
            LOG.info(f"Connected to {self.node}, forwarding ports {self._ports_str}")

        return proc

    async def _request_terminate(self, proc: Process):
        await proc.communicate(b'')

    async def _cleanup(self, proc: Process, stopped: bool) -> None:
        if stopped:
            LOG.info(f"Disconnected from {self.node}, closing ports {self._ports_str}")
        else:
            LOG.warning(
                f"Unexpectedly disconnected from {self.node}, closing ports {self._ports_str}"
            )

    @property
    def node(self) -> SSHConnInfo:
        return self.client.node

    @property
    def _ports_str(self) -> str:
        return ', '.join(map(str, self.forwards))
