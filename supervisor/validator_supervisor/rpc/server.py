"""
The module exporting the RpcServer.

See RpcServer class documentation for more details.
"""

import asyncio
import json
import logging
import os
from ssl import SSLContext
from typing import Dict, Optional, Tuple

from .auth import gen_auth_challenge, check_auth_response
from .jsonrpc import \
    BEGIN_UNLOCK_RESULT, JsonRpcRequest, JsonRpcResponse, MalformedJsonRpc, RpcTarget
from ..util import ExitMixin
from ..validators import ValidatorRelease, ValidatorReleaseSchema

LOG = logging.getLogger(__name__)


class RpcServer(object):
    """
    JSON-RPC over Unix socket server which controls a ValidatorSupervisor.

    The RpcServer listens on a Unix domain socket (or a TCP connection proxied through one) for
    JSON-RPC requests, newline-separated, and processes and responds to them.

    There's one tricky part of this RPC protocol for unlocking the supervisor with the password.
    Since this password is *very* sensitive and I'm afraid it would get accidentally logged if put
    in a JSON-RPC request, I go out of the way to put it on its own logic which is read separately.

    There is an authentication protocol on a per-connection basis. This provides only marginal
    benefit currently, but we may want to have different users with different RPC privilege levels.

    TLS is left as a non-mandatory option since remote connections already come through an SSH
    tunnel.
    """
    _server: Optional[asyncio.AbstractServer]

    def __init__(
            self,
            target: RpcTarget,
            user_keys: Dict[str, str],
            sock_path: str,
            ssl: Optional[SSLContext] = None,
    ):
        self.target = target
        self.user_keys = user_keys
        self.sock_path = sock_path
        self._ssl = ssl
        self._server = None
        self._handler_lock = asyncio.Lock()
        self._session_exit_event = asyncio.Event()

    async def start(self) -> None:
        if self._server is not None:
            return

        self._session_exit_event = asyncio.Event()
        self._server = await asyncio.start_unix_server(
            self._client_connected,
            self.sock_path,
            ssl=self._ssl,
        )
        # Any user on the host can connect
        os.chmod(self.sock_path, 0o777)
        LOG.info(f"Started RPC server on UNIX domain socket at path {self.sock_path}")

    async def stop(self) -> None:
        if self._server is None:
            return

        LOG.info("Shutting down RPC server")
        self._session_exit_event.set()
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _client_connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        session = self._Session(
            self.target,
            self.user_keys,
            reader,
            writer,
            self._handler_lock,
            self._session_exit_event,
        )
        await session.run()

    class _Session(ExitMixin):
        METHODS = {'get_health', 'start_validator', 'stop_validator', 'connect', 'shutdown',
                   'begin_unlock', 'check_unlock', 'get_auth_challenge', 'auth',
                   'set_validator_release'}
        UNAUTHENTICATED_METHODS = {'get_auth_challenge', 'auth'}

        _password: Optional[bytes]

        def __init__(
                self,
                target: RpcTarget,
                user_keys: Dict[str, str],
                reader: asyncio.StreamReader,
                writer: asyncio.StreamWriter,
                handler_lock: asyncio.Lock,
                exit_event: asyncio.Event,
        ):
            self.target = target
            self.user_keys = user_keys
            self.reader = reader
            self.writer = writer
            self._handler_lock = handler_lock
            self._exit_event = exit_event

            self._unlocking = False
            self._password = None
            self._auth_challenge = gen_auth_challenge()
            self.user: Optional[str] = None

        async def run(self) -> None:
            try:
                while not self._exited:
                    read_task = asyncio.create_task(self.reader.readline())
                    await self._either_or_exit(read_task)
                    if self._exited:
                        return
                    line = read_task.result()
                    if not line:
                        return

                    if self._unlocking:
                        self._password = line
                        self._unlocking = False
                    else:
                        response = await self._handle_request(line)
                        self.writer.write(json.dumps(response.to_json()).encode())
                        self.writer.write(b"\n")
                        await self.writer.drain()
            finally:
                self.writer.close()
                await self.writer.wait_closed()

        async def _handle_request(self, request_ser: bytes) -> JsonRpcResponse:
            try:
                msg = json.loads(request_ser)
            except json.decoder.JSONDecodeError as e:
                msg = f"Failed to parse request body JSON: {e}"
                LOG.warning(msg)
                return JsonRpcResponse(call_id=None, result=msg, is_error=True)

            try:
                request = JsonRpcRequest.from_json(msg)
            except MalformedJsonRpc as e:
                msg = f"Received malformed JSON-RPC request: {e}"
                LOG.warning(msg)
                return JsonRpcResponse(call_id=None, result=msg, is_error=True)

            return await self._handle_rpc(request)

        async def _handle_rpc(self, request: JsonRpcRequest) -> JsonRpcResponse:
            LOG.debug(f"Received request: {request}")
            if request.method in self.METHODS:
                handler = getattr(self, f"_handle_{request.method}")
            else:
                LOG.error(f"Unknown JSON-RPC command: {request.method}")
                return JsonRpcResponse(request.call_id, "Unknown JSON-RPC command", is_error=True)

            if self.user is not None or request.method in self.UNAUTHENTICATED_METHODS:
                try:
                    async with self._handler_lock:
                        success, result = await handler(request.params)
                except Exception as err:
                    LOG.warning(f"Exception occurred handling request {request}: {repr(err)}")
                    success = False
                    result = repr(err)
            else:
                success = False
                result = f"{request.method} requires authentication"

            return JsonRpcResponse(request.call_id, result, is_error=not success)

        async def _handle_get_auth_challenge(self, _params: object):
            return True, self._auth_challenge

        async def _handle_auth(self, params: object):
            if not (isinstance(params, list) and len(params) == 2):
                return False, "params must be an array [USER, AUTH_RESPONSE]"

            user = params[0]
            if not isinstance(user, str):
                return False, "user must be a string"

            auth_response = params[1]
            if not isinstance(auth_response, str):
                return False, "auth response must be a string"

            try:
                user_key = self.user_keys[user]
            except KeyError:
                return False, "user not found"

            if not check_auth_response(user_key, self._auth_challenge, auth_response):
                return False, "denied"

            self.user = user
            return True, "accepted"

        async def _handle_begin_unlock(self, _params: object):
            self._unlocking = True
            return True, BEGIN_UNLOCK_RESULT

        async def _handle_check_unlock(self, _params: object):
            if self._password is None:
                return False, "Must first call begin_unlock"

            password_bytes = self._password
            self._password = None

            try:
                password = password_bytes.decode('utf-8').strip()
            except UnicodeDecodeError:
                return False, "Password is not valid UTF-8"

            success = await self.target.unlock(password)
            return True, success

        async def _handle_start_validator(self, _params: object) -> Tuple[bool, object]:
            result = await self.target.start_validator()
            return True, result

        async def _handle_stop_validator(self, _params: object) -> Tuple[bool, object]:
            result = await self.target.stop_validator()
            return True, result

        async def _handle_connect(self, params: object) -> Tuple[bool, object]:
            if not (isinstance(params, list) and len(params) in {1, 2}):
                return False, "params must be an array [HOST, [PORT]]"

            host = params[0]
            if not isinstance(host, str):
                return False, "host must be a string"

            if len(params) == 2:
                port = params[1]
                if not isinstance(port, int):
                    return False, "port must be an int"
            else:
                port = None

            await self.target.connect_eth2_node(host, port)
            return True, "OK"

        async def _handle_shutdown(self, _params: object) -> Tuple[bool, object]:
            await self.target.shutdown()
            return True, None

        async def _handle_get_health(self, _params: object) -> Tuple[bool, object]:
            result = await self.target.get_health()
            return True, result

        async def _handle_set_validator_release(self, params: object) -> Tuple[bool, object]:
            if not isinstance(params, dict):
                return False, "params must be an JSON object"

            release = ValidatorReleaseSchema().load(params)
            await self.target.set_validator_release(release)
            return True, None
