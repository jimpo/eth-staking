import asyncio
from contextlib import asynccontextmanager
import json
import os.path
import tempfile
from typing import AsyncGenerator, Optional
import unittest

from .auth import gen_user_key
from .client import BadRpcResponse, RpcClient, RpcClientConnection, RpcError
from .jsonrpc import JsonRpcRequest, JsonRpcResponse


class RpcClientTest(unittest.IsolatedAsyncioTestCase):
    """
    The client unit tests mostly test error handling since the happy path cases are covered by
    client-server integration tests.
    """
    server_reader: Optional[asyncio.StreamReader]
    server_writer: Optional[asyncio.StreamWriter]

    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sock_path = os.path.join(self.tmpdir.name, 'validator_supervisor.sock')
        self.connected_cond = asyncio.Condition()
        self.server_reader = None
        self.server_writer = None

        async def on_client_connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            async with self.connected_cond:
                self.server_reader = reader
                self.server_writer = writer
                self.connected_cond.notify()

        self.server = await asyncio.start_unix_server(on_client_connect, self.sock_path)
        self.auth_key = gen_user_key()
        self.client = RpcClient('admin', self.auth_key, self.sock_path)

    async def asyncTearDown(self) -> None:
        self.server.close()
        await self.server.wait_closed()
        self.tmpdir.cleanup()

    async def test_malformed_json(self):
        async with self.connect() as conn:
            request_task = asyncio.create_task(conn.get_health())
            _ = await self.server_reader.readline()
            self.server_writer.write(b"{\n")
            await self.server_writer.drain()
            with self.assertRaises(BadRpcResponse):
                await request_task

    async def test_malformed_jsonrpc_resp(self):
        async with self.connect() as conn:
            request_task = asyncio.create_task(conn.get_health())
            _ = await self.server_reader.readline()
            self.server_writer.write(b'{"jsonrpc":"1.0"}\n')
            await self.server_writer.drain()
            with self.assertRaises(BadRpcResponse):
                await request_task

    async def test_incorrect_response_id(self):
        async with self.connect() as conn:
            request_task = asyncio.create_task(conn.get_health())
            req_line = await self.server_reader.readline()
            req = JsonRpcRequest.from_json(json.loads(req_line))
            resp = JsonRpcResponse(call_id=req.call_id + 1, result=None)

            self.server_writer.write(json.dumps(resp.to_json()).encode() + b"\n")
            await self.server_writer.drain()
            with self.assertRaises(BadRpcResponse):
                await request_task

    async def test_rpc_error(self):
        async with self.connect() as conn:
            request_task = asyncio.create_task(conn.get_health())
            req_line = await self.server_reader.readline()
            req = JsonRpcRequest.from_json(json.loads(req_line))
            resp = JsonRpcResponse(call_id=req.call_id, result=None, is_error=True)

            self.server_writer.write(json.dumps(resp.to_json()).encode() + b"\n")
            await self.server_writer.drain()
            with self.assertRaises(RpcError):
                await request_task

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[RpcClientConnection, None]:
        async with self.connected_cond:
            async with self.client.connect() as conn:
                await self.connected_cond.wait()
                assert self.server_reader is not None
                assert self.server_writer is not None
                server_writer = self.server_writer

                yield conn

                server_writer.close()
                await server_writer.wait_closed()
                self.server_reader = None
                self.server_writer = None


if __name__ == '__main__':
    unittest.main()
