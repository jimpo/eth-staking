import filecmp
import io
import os
import os.path
import secrets
import shutil
import tempfile
import time
import unittest

from .backup_archive import \
    BackupArchive, LockedArchiveCorrupted, check_validator_data_dir, make_validator_data_backup
from .exceptions import MissingValidatorData


class BackupArchiveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.src_dir = tempfile.TemporaryDirectory(prefix="BackupArchiveTest_src_dir")
        self.dst_dir = tempfile.TemporaryDirectory(prefix="BackupArchiveTest_dst_dir")
        self.key = secrets.token_bytes(BackupArchive.KEY_SIZE)

        with open(os.path.join(self.src_dir.name, 'hello.txt'), 'w') as f:
            f.write("hello world")

    def tearDown(self) -> None:
        self.src_dir.cleanup()
        self.dst_dir.cleanup()

    def test_pack_timestamp(self):
        time_lo_bound = int(time.time())
        archive = BackupArchive.pack(self.src_dir.name)
        time_hi_bound = time.time()

        self.assertGreaterEqual(archive.timestamp, time_lo_bound)
        self.assertLessEqual(archive.timestamp, time_hi_bound)

    def test_pack_unpack(self):
        archive = BackupArchive.pack(self.src_dir.name)
        archive.unpack(self.dst_dir.name)

        self.assertEqual(os.listdir(self.dst_dir.name), ['hello.txt'])
        with open(os.path.join(self.dst_dir.name, 'hello.txt'), 'r') as f:
            self.assertEqual(f.read(), "hello world")

    def test_pack_lock_unlock_unpack(self):
        archive = BackupArchive.pack(self.src_dir.name)
        locked_archive = io.BytesIO()
        archive.lock(self.key, locked_archive)

        locked_archive.seek(0)
        archive_copy = BackupArchive.unlock(self.key, locked_archive)
        self.assertEqual(archive_copy.timestamp, archive.timestamp)

        archive.unpack(self.dst_dir.name)
        self.assertEqual(os.listdir(self.dst_dir.name), ['hello.txt'])
        with open(os.path.join(self.dst_dir.name, 'hello.txt'), 'r') as f:
            self.assertEqual(f.read(), "hello world")

    def test_unlock_with_wrong_key(self):
        archive = BackupArchive.pack(self.src_dir.name)
        locked_archive = io.BytesIO()
        archive.lock(self.key, locked_archive)

        wrong_key = secrets.token_bytes(BackupArchive.KEY_SIZE)
        locked_archive.seek(0)
        with self.assertRaises(LockedArchiveCorrupted):
            BackupArchive.unlock(wrong_key, locked_archive)


class CheckValidatorDataTest(unittest.TestCase):
    TEST_VALIDATOR_ID = "0x928c6edad1bba366686ff795d0c604a22759e434049e1372ace295c01601f05cb15215d8bdf29681a2d49d208900bfbf"

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ValidatorDataArchiveTest_src_dir")
        self.validator_data_dir = os.path.join(self.tmpdir.name, 'validator_data')
        shutil.copytree('test/validator_data', self.validator_data_dir)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_check_valid_data_dir(self):
        check_validator_data_dir(self.validator_data_dir)

    def test_missing_data_dir(self):
        shutil.rmtree(self.validator_data_dir)
        with self.assertRaises(MissingValidatorData):
            check_validator_data_dir(self.validator_data_dir)

    def test_missing_slashing_protection(self):
        os.unlink(os.path.join(self.validator_data_dir, 'slashing-protection.json'))
        with self.assertRaises(MissingValidatorData):
            check_validator_data_dir(self.validator_data_dir)

    def test_missing_validators_dir(self):
        shutil.rmtree(os.path.join(self.validator_data_dir, 'validators'))
        with self.assertRaises(MissingValidatorData):
            check_validator_data_dir(self.validator_data_dir)

    def test_missing_keystore(self):
        os.unlink(os.path.join(
            self.validator_data_dir, 'validators', self.TEST_VALIDATOR_ID, 'keystore.json'
        ))
        with self.assertRaises(MissingValidatorData):
            check_validator_data_dir(self.validator_data_dir)

    def test_missing_keystore_password(self):
        os.unlink(os.path.join(
            self.validator_data_dir, 'validators', self.TEST_VALIDATOR_ID, 'password.txt'
        ))
        with self.assertRaises(MissingValidatorData):
            check_validator_data_dir(self.validator_data_dir)


class MakeValidatorBackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="ValidatorDataArchiveTest_dst_dir")
        self.backup_tempfile = tempfile.NamedTemporaryFile(prefix='supervisor-backup', suffix='.bin')
        self.key = secrets.token_bytes(BackupArchive.KEY_SIZE)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        self.backup_tempfile.close()

    def test_make_validator_backup(self):
        timestamp_lo_bound = int(time.time())
        make_validator_data_backup(self.key, self.backup_tempfile.name, 'test/validator_data')
        timestamp_hi_bound = int(time.time())

        archive = BackupArchive.unlock(self.key, self.backup_tempfile)
        self.assertGreaterEqual(archive.timestamp, timestamp_lo_bound)
        self.assertLessEqual(archive.timestamp, timestamp_hi_bound)

        archive.unpack(self.tmpdir.name)
        dircmp = filecmp.dircmp('test/validator_data', self.tmpdir.name)
        self.assertEqual(len(dircmp.diff_files), 0)


if __name__ == '__main__':
    unittest.main()
