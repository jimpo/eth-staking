"""
A shell interface for controlling a validator supervisor daemon.

The control shell can either connect to a validator supervisor daemon running on the same host
through a Unix domain socket or can connect through an SSH tunnel to a bastion node that the
supervisor is also connected to. The validator supervisor creates reverse SSH tunnels from the
bastion to its RPC interface so that a remote control shell can connect.
"""

from __future__ import annotations

import asyncio
import cmd
from contextlib import asynccontextmanager
from functools import wraps
import getpass
import os
import pprint
import ssl
from tempfile import TemporaryDirectory
from typing import AsyncGenerator, Callable, Coroutine, Optional, Union

from .config import SSHConnInfo
from .rpc.client import RpcClient, RpcClientConnection, BadRpcResponse, RpcError
from .ssh import SSHClient, SSHForward, SSHTunnel, TcpSocket, UnixSocket


@asynccontextmanager
async def _rpc_client(
        endpoint: Union[UnixSocket, SSHConnInfo],
        user: str,
        auth_key: str,
        ssl: Optional[ssl.SSLContext],
) -> AsyncGenerator[RpcClient, None]:
    if isinstance(endpoint, UnixSocket):
        yield RpcClient(user, auth_key, endpoint.path, ssl)
    if isinstance(endpoint, SSHConnInfo):
        with TemporaryDirectory(prefix='validator_supervisor_control_') as tmpdir:
            sock_path = os.path.join(tmpdir, 'rpc.sock')
            known_hosts_file = os.path.join(os.environ['HOME'], '.ssh', 'known_hosts')
            known_hosts_lock = asyncio.Lock()
            ssh_tunnel = SSHTunnel(
                SSHClient(endpoint, known_hosts_file, known_hosts_lock),
                [SSHForward(UnixSocket(sock_path), TcpSocket.localhost(8000))],
            )
            await ssh_tunnel.start()
            try:
                yield RpcClient(user, auth_key, sock_path, ssl)
            finally:
                ssh_tunnel.stop()
                await ssh_tunnel.watch()


def _rpc_command(f: Callable[..., Coroutine[None, None, None]]):
    async def async_wrapper(shell: ControlShell, *args):
        async with _rpc_client(shell.endpoint, shell.user, shell.auth_key, shell.ssl) as client:
            async with client.connect_and_auth() as conn:
                try:
                    await f(shell, conn, *args)
                except BadRpcResponse as err:
                    print(f"Validator supervisor sent bad response: {err}")
                except RpcError as err:
                    print(f"Validator supervisor internal error: {err}")

    @wraps(f)
    def sync_wrapper(*args):
        asyncio.run(async_wrapper(*args))

    return sync_wrapper


class ControlShell(cmd.Cmd):
    """
    Control shell for local or remote validator supervisor daemon.

    See module documentation for further details.
    """

    intro = 'Control shell for the validator supervisor. Type help or ? to list commands.\n'
    prompt = '>>> '

    def __init__(
            self,
            endpoint: Union[UnixSocket, SSHConnInfo],
            ssl_cert_file: Optional[str],
            user: Optional[str],
            auth_key: Optional[str],
    ):
        super().__init__()
        self.endpoint = endpoint
        if ssl_cert_file:
            self.ssl: Optional[ssl.SSLContext] = ssl.SSLContext()
            self.ssl.load_verify_locations(ssl_cert_file)
            self.ssl.verify_mode = ssl.CERT_REQUIRED
        else:
            self.ssl = None
        if user is None:
            user = input("Auth user: ")
        if auth_key is None:
            auth_key = getpass.getpass("Auth key: ")
        self.user = user
        self.auth_key = auth_key.strip()

    @_rpc_command
    async def do_get_health(self, conn: RpcClientConnection, _arg) -> None:
        health_info = await conn.get_health()
        pprint.pp(health_info)

    @_rpc_command
    async def do_start_validator(self, conn: RpcClientConnection, _arg) -> None:
        if await conn.start_validator():
            print("Validator has been started")
        else:
            print("Validator is already running")

    @_rpc_command
    async def do_stop_validator(self, conn: RpcClientConnection, _arg) -> None:
        if await conn.stop_validator():
            print("Validator has been stopped")
        else:
            print("Validator is not running")

    @_rpc_command
    async def do_unlock(self, conn: RpcClientConnection, _arg) -> None:
        password = getpass.getpass('Passphrase: ')
        if await conn.unlock(password):
            print("Validator supervisor has been unlocked")
        else:
            print("Password is incorrect")

    @_rpc_command
    async def do_shutdown(self, conn: RpcClientConnection, _arg) -> None:
        await conn.shutdown()
        print("OK")

    def do_quit(self, _arg):
        return True

    def do_EOF(self, _arg):
        return True
