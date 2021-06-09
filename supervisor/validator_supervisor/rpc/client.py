"""
The module exporting the RpcClient and RpcClientConnection.

See RpcClient class documentation for more details.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
from ssl import SSLContext
from typing import Any, AsyncGenerator, Dict, Optional

from .auth import auth_response
from .jsonrpc import \
    BEGIN_UNLOCK_RESULT, JsonRpcRequest, JsonRpcResponse, RpcTarget, MalformedJsonRpc


class BadRpcResponse(Exception):
    pass


class RpcError(Exception):
    pass


class RpcClient(RpcTarget):
    """
    JSON-RPC over Unix socket client for a server controlling a ValidatorSupervisor.

    See RpcServer class documentation for more details.
    """
    def __init__(
            self,
            user: str,
            auth_key: str,
            sock_path: str,
            ssl: Optional[SSLContext] = None,
    ):
        self.user = user
        self.auth_key = auth_key
        self.sock_path = sock_path
        self._ssl = ssl

    async def get_health(self) -> Dict[str, object]:
        async with self.connect_and_auth() as conn:
            return await conn.get_health()

    async def start_validator(self) -> bool:
        async with self.connect_and_auth() as conn:
            return await conn.start_validator()

    async def stop_validator(self) -> bool:
        async with self.connect_and_auth() as conn:
            return await conn.stop_validator()

    async def connect_eth2_node(self, host: str, port: Optional[int]):
        async with self.connect_and_auth() as conn:
            return await conn.connect_eth2_node(host, port)

    async def unlock(self, password: str) -> bool:
        async with self.connect_and_auth() as conn:
            return await conn.unlock(password)

    async def shutdown(self) -> None:
        async with self.connect_and_auth() as conn:
            return await conn.shutdown()

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[RpcClientConnection, None]:
        kwargs: Dict[str, Any] = {}
        if self._ssl:
            kwargs.update(
                ssl=self._ssl,
                # Since this is for use with self-signed certificates, omit server hostname.
                server_hostname='',
            )
        reader, writer = await asyncio.open_unix_connection(self.sock_path, **kwargs)
        try:
            yield RpcClientConnection(reader, writer)
        finally:
            writer.close()
            await writer.wait_closed()
            _ = await reader.read()

    @asynccontextmanager
    async def connect_and_auth(self) -> AsyncGenerator[RpcClientConnection, None]:
        async with self.connect() as conn:
            await conn.auth(self.user, self.auth_key)
            yield conn


class RpcClientConnection(RpcTarget):
    """
    JSON-RPC over Unix socket client connection to a server controlling a ValidatorSupervisor.

    See RpcServer class documentation for more details.
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer

    async def auth(self, user: str, auth_key: str) -> None:
        auth_challenge = await self._rpc_call('get_auth_challenge')
        if not isinstance(auth_challenge, str):
            raise BadRpcResponse("expected string")
        token = auth_response(auth_key, auth_challenge)
        await self._rpc_call('auth', [user, token])

    async def get_health(self) -> Dict[str, object]:
        result = await self._rpc_call('get_health')
        if not isinstance(result, dict):
            raise BadRpcResponse("expected dict", result)
        return result

    async def start_validator(self) -> bool:
        result = await self._rpc_call('start_validator')
        if not isinstance(result, bool):
            raise BadRpcResponse("expected bool", result)
        return result

    async def stop_validator(self) -> bool:
        result = await self._rpc_call('stop_validator')
        if not isinstance(result, bool):
            raise BadRpcResponse("expected bool", result)
        return result

    async def connect_eth2_node(self, host: str, port: Optional[int]):
        pass

    async def unlock(self, password: str) -> bool:
        if "\n" in password:
            raise ValueError("password cannot contain newlines")

        begin_result = await self._rpc_call('begin_unlock')
        if begin_result != BEGIN_UNLOCK_RESULT:
            raise BadRpcResponse(f"expected {BEGIN_UNLOCK_RESULT}", begin_result)

        self._writer.write(password.encode())
        self._writer.write(b"\n")
        await self._writer.drain()

        result = await self._rpc_call('check_unlock')
        if not isinstance(result, bool):
            raise BadRpcResponse("expected bool", result)
        return result

    async def shutdown(self) -> None:
        await self._rpc_call('shutdown')

    async def _rpc_call(self, method: str, params: Optional[object] = None) -> object:
        request = JsonRpcRequest(method, params=params)
        self._writer.write(json.dumps(request.to_json()).encode())
        self._writer.write(b"\n")
        await self._writer.drain()
        response_ser = await self._reader.readline()

        try:
            msg = json.loads(response_ser)
            response = JsonRpcResponse.from_json(msg)
        except json.decoder.JSONDecodeError as err:
            raise BadRpcResponse("malformed JSON response") from err
        except MalformedJsonRpc as err:
            raise BadRpcResponse("malformed JSON-RPC response") from err

        if response.call_id != request.call_id:
            raise BadRpcResponse(f"response id does not match request id", request, response)
        if response.is_error:
            raise RpcError(response.result)
        return response.result
