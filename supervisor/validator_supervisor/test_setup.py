import os.path
import tempfile
import unittest
from unittest.mock import patch

from .config import Config, write_config, read_root_key
from .exceptions import UnlockRequired
from .key_ops import KeyDescriptor
#from .setup import perform_unlock

PASSWORD = 'password123'


# class UnlockTest(unittest.TestCase):
#     def setUp(self) -> None:
#         self.tmpdir = tempfile.TemporaryDirectory()
#         self.data_dir = os.path.join(self.tmpdir.name, 'data')
#         self.logs_dir = os.path.join(self.tmpdir.name, 'logs')
#
#         self.key_desc, self.key = KeyDescriptor.generate(PASSWORD, 'argon2id_weak')
#         config = Config(
#             eth2_network='pyrmont',
#             key_desc=self.key_desc,
#             nodes=[],
#             data_dir=self.data_dir,
#             logs_dir=self.logs_dir,
#         )
#         write_config(self.configs_dir.name, config)
#
#     def tearDown(self) -> None:
#         self.tmpdir.cleanup()
#
#     @patch('getpass.getpass')
#     def test_perform_unlock_with_good_password(self, mock_getpass):
#         with self.assertRaises(UnlockRequired):
#             read_root_key(self.key_desc, self.ephemeral_dir.name)
#         mock_getpass.return_value = PASSWORD
#         success = perform_unlock(self.configs_dir.name, self.ephemeral_dir.name)
#         self.assertTrue(success)
#         self.assertEqual(self.key, read_root_key(self.key_desc, self.ephemeral_dir.name))
#
#     @patch('getpass.getpass')
#     def test_perform_unlock_with_bad_password(self, mock_getpass):
#         mock_getpass.return_value = "bad password"
#         success = perform_unlock(self.configs_dir.name, self.ephemeral_dir.name)
#         self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()
