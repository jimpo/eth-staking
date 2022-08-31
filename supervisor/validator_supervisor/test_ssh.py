import asyncio
import os
import signal
import subprocess
import tempfile
import unittest

from .ssh import SSHForward, SSHConnInfo, SSHClient, SSHTunnel, TcpSocket


class SSHTunnelTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.known_hosts_file = tempfile.NamedTemporaryFile(prefix='ssh_known_hosts')
        self.known_hosts_lock = asyncio.Lock()
        self.client = SSHClient(
            SSHConnInfo(
                host='localhost',
                user='somebody',
                port=2222,
                identity_file='test/config/ssh_id.key',
            ),
            self.known_hosts_file.name,
            self.known_hosts_lock,
        )
        self.tunnel = SSHTunnel(
            self.client,
            [
                SSHForward(TcpSocket.localhost(3005), TcpSocket('loki', 3100)),
                SSHForward(TcpSocket.localhost(8005), TcpSocket.localhost(8000), reverse=True),
            ],
        )

    async def asyncTearDown(self) -> None:
        self.tunnel.stop()
        await self.tunnel.watch()
        self.known_hosts_file.close()

    async def test_open(self):
        await self.tunnel.start()
        ssh_pid = self.tunnel.get_pid()
        self.assertIsNotNone(ssh_pid)

        result_proc = subprocess.run(
            ["ps", "--pid", str(ssh_pid), "-o", "command"],
            check=True,
            capture_output=True,
        )
        output = result_proc.stdout.decode()
        output_lines = output.splitlines()
        self.assertEqual(2, len(output_lines))
        self.assertRegex(
            output_lines[1].strip(),
            r"ssh -o UserKnownHostsFile=\S+ -o IdentitiesOnly=yes "
            r"-i test/config/ssh_id\.key -p 2222 "
            r"-L localhost:3005:loki:3100 -R localhost:8000:localhost:8005 somebody@localhost"
        )

    async def test_open_to_down_server(self):
        self.tunnel.node.port = 2221
        await self.tunnel.start()
        await asyncio.wait_for(self.tunnel.watch(), timeout=2)
        self.assertFalse(self.tunnel.is_running())

    async def test_watch_for_premature_exit(self):
        await self.tunnel.start()
        ssh_pid = self.tunnel.get_pid()
        self.assertIsNotNone(ssh_pid)

        os.kill(ssh_pid, signal.SIGTERM)
        await asyncio.wait_for(self.tunnel.watch(), timeout=2)

    async def test_reopen_connection(self):
        await self.tunnel.start()
        ssh_pid = self.tunnel.get_pid()
        self.assertIsNotNone(ssh_pid)

        os.kill(ssh_pid, signal.SIGTERM)
        await asyncio.wait_for(self.tunnel.watch(), timeout=2)

        await self.tunnel.start()
        self.assertTrue(self.tunnel.is_running())

    async def test_open_with_configured_pubkey(self):
        self.tunnel.node.pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMfl/a1iZNSzntFF9sYVb/SHsJGu2gcFj/0UTo5F8vnr root@3582f17071b0"
        await self.tunnel.start()
        ssh_pid = self.tunnel.get_pid()
        self.assertIsNotNone(ssh_pid)

        os.kill(ssh_pid, signal.SIGTERM)
        await asyncio.wait_for(self.tunnel.watch(), timeout=2)

        await self.tunnel.start()
        self.assertTrue(self.tunnel.is_running())


if __name__ == '__main__':
    unittest.main()
