import tempfile

import asyncio
import json
import os.path
import unittest
from unittest.mock import AsyncMock

from .auth import gen_user_key
from .jsonrpc import JsonRpcRequest, JsonRpcResponse
from .server import RpcServer, RpcTarget


class MockRpcTarget(RpcTarget):
    start_validator = AsyncMock()
    stop_validator = AsyncMock()
    get_health = AsyncMock()
    connect_eth2_node = AsyncMock()
    unlock = AsyncMock()
    shutdown = AsyncMock()


class RpcServerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sock_path = os.path.join(self.tmpdir.name, 'validator_supervisor.sock')

        self.target = MockRpcTarget()
        self.auth_key = gen_user_key()
        self.server = RpcServer(self.target, {'admin': self.auth_key}, self.sock_path)

        await self.server.start()
        self.reader, self.writer = await asyncio.open_unix_connection(self.sock_path)

    async def asyncTearDown(self) -> None:
        await self.server.stop()
        self.writer.close()
        await self.writer.wait_closed()
        self.tmpdir.cleanup()

    async def test_unknown_call(self):
        request = JsonRpcRequest("unknown_method")
        self.writer.write(json.dumps(request.to_json()).encode() + b"\n")
        await self.writer.drain()

        response_ser = await self.reader.readline()
        response = JsonRpcResponse.from_json(json.loads(response_ser))

        self.assertEqual(response.call_id, request.call_id)
        self.assertTrue(response.is_error)

    async def test_malformed_json(self):
        self.writer.write(b"{\n")
        await self.writer.drain()

        response_ser = await self.reader.readline()
        response = JsonRpcResponse.from_json(json.loads(response_ser))

        self.assertIsNone(response.call_id)
        self.assertTrue(response.is_error)

    async def test_malformed_jsonrpc_req(self):
        self.writer.write(b'{"jsonrpc":"1.0"}\n')
        await self.writer.drain()

        response_ser = await self.reader.readline()
        response = JsonRpcResponse.from_json(json.loads(response_ser))

        self.assertIsNone(response.call_id)
        self.assertTrue(response.is_error)

    async def test_stop_closes_client_connections(self):
        await self.server.stop()
        data = await self.reader.read()
        self.assertFalse(data)

    async def test_bad_auth(self):
        request = JsonRpcRequest("auth", params=["admin", "abcd"])
        self.writer.write(json.dumps(request.to_json()).encode() + b"\n")
        await self.writer.drain()

        response_ser = await self.reader.readline()
        response = JsonRpcResponse.from_json(json.loads(response_ser))

        self.assertEqual(response.call_id, request.call_id)
        self.assertTrue(response.is_error)
        self.assertEqual(response.result, "denied")

    async def test_unauthenticated_call(self):
        request = JsonRpcRequest("get_health")
        self.writer.write(json.dumps(request.to_json()).encode() + b"\n")
        await self.writer.drain()

        response_ser = await self.reader.readline()
        response = JsonRpcResponse.from_json(json.loads(response_ser))

        self.assertEqual(response.call_id, request.call_id)
        self.assertTrue(response.is_error)
        self.assertEqual(response.result, "get_health requires authentication")


if __name__ == '__main__':
    unittest.main()
