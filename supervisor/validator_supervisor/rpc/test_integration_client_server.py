import asyncio
import os.path
import ssl
import tempfile
import unittest
from unittest.mock import AsyncMock

from .auth import gen_user_key
from .client import RpcClient, RpcError
from .server import RpcServer, RpcTarget


class MockRpcTarget(RpcTarget):
    start_validator = AsyncMock()
    stop_validator = AsyncMock()
    get_health = AsyncMock()
    set_validator_release = AsyncMock()
    connect_eth2_node = AsyncMock()
    unlock = AsyncMock()
    shutdown = AsyncMock()


class RpcServerClientIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.sock_path = os.path.join(self.tmpdir.name, 'validator_supervisor.sock')

        server_ssl = ssl.SSLContext()
        server_ssl.load_cert_chain('test/config/cert.pem', 'test/config/key.pem')
        client_ssl = ssl.SSLContext()
        client_ssl.load_verify_locations('test/config/cert.pem')
        client_ssl.verify_mode = ssl.CERT_REQUIRED

        self.exit_event = asyncio.Event()
        self.target = MockRpcTarget()
        self.auth_key = gen_user_key()
        self.server = RpcServer(self.target, {'admin': self.auth_key}, self.sock_path, server_ssl)
        self.client = RpcClient('admin', self.auth_key, self.sock_path, client_ssl)

        await self.server.start()

    async def asyncTearDown(self) -> None:
        self.exit_event.set()
        await self.server.stop()
        self.tmpdir.cleanup()

    async def test_handle_multiple_calls(self) -> None:
        expected_result = {
            'is_running': True,
        }
        self.target.get_health.return_value = expected_result
        get_health_result = await self.client.get_health()
        self.assertEqual(expected_result, get_health_result)

        self.target.start_validator.return_value = True
        start_validator_result = await self.client.start_validator()
        self.assertTrue(start_validator_result)

    async def test_unlock_with_good_password(self) -> None:
        self.target.unlock.return_value = True
        success = await self.client.unlock("good password")
        self.assertTrue(success)
        self.target.unlock.assert_awaited_with("good password")

    async def test_unlock_with_bad_password(self) -> None:
        self.target.unlock.return_value = False
        success = await self.client.unlock("bad password")
        self.assertFalse(success)
        self.target.unlock.assert_awaited_with("bad password")

    async def test_handler_exception(self):
        self.target.get_health.side_effect = Exception("WHY? OH WHY?")
        with self.assertRaises(RpcError):
            await self.client.get_health()


if __name__ == '__main__':
    unittest.main()
