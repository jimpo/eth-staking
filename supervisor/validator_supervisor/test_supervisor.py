import asyncio
import os
import random
import tempfile
import unittest

from .backup_archive import make_validator_data_backup
from .config import Config
from .exceptions import MissingValidatorData
from .key_ops import KeyDescriptor
from .ssh import SSHConnInfo
from .supervisor import ValidatorSupervisor
from .validators import ValidatorRelease

ETH2_NETWORK = 'pyrmont'
PASSWORD = 'password123'
TEST_MNEMONIC = b'clog dust clip zone cute decrease correct quantum forget climb buffalo ' \
    b'girl plunge fuel together warfare space cost memory able evolve rebel orient check'


class ValidatorSupervisorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.tmpdir.name, 'data')
        self.logs_dir = os.path.join(self.tmpdir.name, 'logs')
        for dirpath in [self.data_dir, self.logs_dir]:
            os.mkdir(dirpath)

        # Generate randomized backup filename because SSH server where backups are stored via SCP
        # is not cleared after each test.
        backup_filename_rand_tag = hex(random.getrandbits(32))[2:]
        self.backup_filename = f"supervisor-backup_{backup_filename_rand_tag}.bin"

        key_desc, self.root_key = KeyDescriptor.generate(PASSWORD, 'argon2id_weak')
        self.supervisor = ValidatorSupervisor(
            config=Config(
                eth2_network=ETH2_NETWORK,
                key_desc=key_desc,
                nodes=[
                    SSHConnInfo(
                        host='localhost',
                        user='somebody',
                        port=2222,
                        identity_file='test/config/ssh_id.key',
                    ),
                ],
                data_dir=self.data_dir,
                logs_dir=self.logs_dir,
                ssl_cert_file='test/config/cert.pem',
                ssl_key_file='test/config/key.pem',
                backup_filename=self.backup_filename,
                port_range=(13000, 14000),
                rpc_users={},
            ),
            root_key=self.root_key,
            exit_event=asyncio.Event(),
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _generate_initial_backup(self) -> None:
        make_validator_data_backup(
            self.root_key.derive_backup_key(),
            os.path.join(self.data_dir, self.backup_filename),
            'test/validator_data',
        )

    async def test_load_backup_missing_backup(self):
        success = await self.supervisor.load_backup()
        self.assertFalse(success)

    async def test_save_with_missing_data(self):
        with self.assertRaises(MissingValidatorData):
            await self.supervisor.save_backup()

    async def test_load_local_backup(self):
        self._generate_initial_backup()
        success = await self.supervisor.load_backup()
        self.assertTrue(success)

    async def test_save_and_load_local_backup(self):
        self._generate_initial_backup()
        success = await self.supervisor.load_backup()
        self.assertTrue(success)
        os.unlink(os.path.join(self.data_dir, self.backup_filename))

        await self.supervisor.save_backup()
        self.assertTrue(os.path.exists(os.path.join(self.data_dir, self.backup_filename)))
        success = await self.supervisor.load_backup()
        self.assertTrue(success)

    async def test_save_and_load_remote_backup(self):
        self._generate_initial_backup()
        success = await self.supervisor.load_backup()
        self.assertTrue(success)
        os.unlink(os.path.join(self.data_dir, self.backup_filename))

        await self.supervisor.save_backup()
        os.unlink(os.path.join(self.data_dir, self.backup_filename))
        success = await self.supervisor.load_backup()
        self.assertTrue(success)

    async def test_set_validator_release(self):
        old_release = ValidatorRelease(
            impl_name='lighthouse',
            version='v1.5.1',
            checksum='a44ecaf9a5f956e9e43928252d6471a2eb6dc59245a5747e4fb545d512522768',
        )
        await self.supervisor.set_validator_release(old_release)
        self.assertEqual(self.supervisor.config.validator_release, old_release)


if __name__ == '__main__':
    unittest.main()
