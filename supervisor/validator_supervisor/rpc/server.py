"""
The module exporting the RpcServer.

See RpcServer class documentation for more details.
"""

from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass
import json
import logging
import os
from ssl import SSLContext
from typing import Dict, List, Optional, Type

from .auth import gen_auth_challenge, check_auth_response
from .jsonrpc import \
    BEGIN_UNLOCK_RESULT, JsonRpcRequest, JsonRpcResponse, MalformedJsonRpc, RpcTarget
from ..util import ExitMixin
from ..validators import ValidatorReleaseSchema

LOG = logging.getLogger(__name__)


@dataclass
class RpcResult:
    success: bool
    result: object
    check_password: Optional[Type[RpcOperationPasswordCheck]] = None


@dataclass
class RpcContext:
    target: RpcTarget
    user_keys: Dict[str, str]
    user: Optional[str]
    auth_challenge: str


class RpcOperation(abc.ABC):
    authenticated = True

    @classmethod
    @property
    @abc.abstractmethod
    def method(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        pass


class RpcOperationPasswordCheck(abc.ABC):
    @classmethod
    @property
    @abc.abstractmethod
    def method(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    async def handle(cls, ctx: RpcContext, password: bytes, params: object) -> RpcResult:
        pass


class GetAuthChallengeOp(RpcOperation):
    method = 'get_auth_challenge'
    authenticated = False

    @classmethod
    async def handle(cls, ctx: RpcContext, _params: object) -> RpcResult:
        return RpcResult(True, ctx.auth_challenge)


class AuthOp(RpcOperation):
    method = 'auth'
    authenticated = False

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        if not (isinstance(params, list) and len(params) == 2):
            return RpcResult(False, "params must be an array [USER, AUTH_RESPONSE]")

        user = params[0]
        if not isinstance(user, str):
            return RpcResult(False, "user must be a string")

        auth_response = params[1]
        if not isinstance(auth_response, str):
            return RpcResult(False, "auth response must be a string")

        try:
            user_key = ctx.user_keys[user]
        except KeyError:
            return RpcResult(False, "user not found")

        if not check_auth_response(user_key, ctx.auth_challenge, auth_response):
            return RpcResult(False, "denied")

        ctx.user = user
        return RpcResult(True, "accepted")


class GetHealthOp(RpcOperation):
    method = 'get_health'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        result = await ctx.target.get_health()
        return RpcResult(True, result)


class BeginUnlockOp(RpcOperation):
    method = 'begin_unlock'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        return RpcResult(True, BEGIN_UNLOCK_RESULT, CheckUnlockOp)


class CheckUnlockOp(RpcOperationPasswordCheck):
    method = 'check_unlock'

    @classmethod
    async def handle(cls, ctx: RpcContext, password_bytes: bytes, params: object) -> RpcResult:
        try:
            password = password_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            return RpcResult(False, "Password is not valid UTF-8")

        success = await ctx.target.unlock(password)
        return RpcResult(True, success)


class StartValidatorOp(RpcOperation):
    method = 'start_validator'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        result = await ctx.target.start_validator()
        return RpcResult(True, result)


class StopValidatorOp(RpcOperation):
    method = 'stop_validator'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        result = await ctx.target.stop_validator()
        return RpcResult(True, result)


class ConnectOp(RpcOperation):
    method = 'connect'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        if not (isinstance(params, list) and len(params) in {1, 2}):
            return RpcResult(False, "params must be an array [HOST, [PORT]]")

        host = params[0]
        if not isinstance(host, str):
            return RpcResult(False, "host must be a string")

        if len(params) == 2:
            port = params[1]
            if not isinstance(port, int):
                return RpcResult(False, "port must be an int")
        else:
            port = None

        await ctx.target.connect_eth2_node(host, port)
        return RpcResult(True, "OK")


class ShutdownOp(RpcOperation):
    method = 'shutdown'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        await ctx.target.shutdown()
        return RpcResult(True, None)


class SetValidatorReleaseOp(RpcOperation):
    method = 'set_validator_release'

    @classmethod
    async def handle(cls, ctx: RpcContext, params: object) -> RpcResult:
        if not isinstance(params, dict):
            return RpcResult(False, "params must be an JSON object")

        release = ValidatorReleaseSchema().load(params)
        await ctx.target.set_validator_release(release)
        return RpcResult(True, None)


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
        OPERATIONS: List[Type[RpcOperation]] = [
            GetHealthOp,
            StartValidatorOp,
            StopValidatorOp,
            ConnectOp,
            ShutdownOp,
            BeginUnlockOp,
            GetAuthChallengeOp,
            AuthOp,
            SetValidatorReleaseOp,
        ]

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
            self.ctx = RpcContext(
                target=target,
                user_keys=user_keys,
                user=None,
                auth_challenge=gen_auth_challenge(),
            )
            self.reader = reader
            self.writer = writer
            # TODO: Figure out why mypy thinks op.method is a Callable, not a str
            self._operations: Dict[str, Type[RpcOperation]] = \
                {op.method: op for op in self.OPERATIONS}  # type: ignore
            self._handler_lock = handler_lock
            self._exit_event = exit_event
            self._password: Optional[bytes] = None
            self._password_check: Optional[Type[RpcOperationPasswordCheck]] = None

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

                    if self._password_check is not None and self._password is None:
                        self._password = line
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

            result = await self._handle_rpc(request)
            self._password_check = result.check_password
            return JsonRpcResponse(request.call_id, result.result, is_error=not result.success)

        async def _handle_rpc(self, request: JsonRpcRequest) -> RpcResult:
            LOG.debug(f"Received request: {request}")

            if self._password_check:
                # _password is populated in run
                assert self._password is not None
                password = self._password
                password_check = self._password_check

                self._password = None
                self._password_check = None

                if request.method != password_check.method:
                    return RpcResult(False, f"Expected method {password_check.method}")

                try:
                    async with self._handler_lock:
                        return await password_check.handle(self.ctx, password, request.params)
                except Exception as err:
                    LOG.warning(f"Exception occurred handling request {request}: {repr(err)}")
                    return RpcResult(False, repr(err))

            try:
                operation = self._operations[request.method]
            except KeyError:
                LOG.error(f"Unknown JSON-RPC command: {request.method}")
                return RpcResult(False, "Unknown JSON-RPC command")

            if self.ctx.user is None and operation.authenticated:
                return RpcResult(False, f"{request.method} requires authentication")

            try:
                async with self._handler_lock:
                    return await operation.handle(self.ctx, request.params)
            except Exception as err:
                LOG.warning(f"Exception occurred handling request {request}: {repr(err)}")
                return RpcResult(False, repr(err))
