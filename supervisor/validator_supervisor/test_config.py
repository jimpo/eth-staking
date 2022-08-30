import os.path
import secrets
import tempfile
import unittest
import yaml

import marshmallow.exceptions

from .config import \
    Config, ConfigSchema, KeyDescriptorSchema, SSHConnInfo, read_config, write_config
from .key_ops import KeyDescriptor


TEST_ETH_ADDRESS = '0x60c19370a8d1A2Bf9fA9dDb25B4516229D04E5bb'


class ConfigTest(unittest.TestCase):
    def test_read_write(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        try:
            config_path = os.path.join(tmpdir.name, 'config.yaml')
            config = Config(
                eth2_network='pyrmont',
                key_desc=KeyDescriptor(
                    algo='argon2id',
                    salt=secrets.token_bytes(16),
                    checksum=secrets.token_bytes(16),
                ),
                fee_recipient=TEST_ETH_ADDRESS,
                nodes=[
                    SSHConnInfo(
                        host='localhost',
                        user='somebody',
                        port=2222,
                        identity_file='test/config/ssh_id.key',
                    ),
                ],
                data_dir='/var/lib/validator-supervisor',
                logs_dir='/var/log/validator-supervisor',
                ssl_cert_file=None,
                ssl_key_file=None,
                port_range=(13000, 14000),
                rpc_users={},
            )
            write_config(config_path, config)
            config_copy = read_config(config_path)
            self.assertEqual(config, config_copy)
        finally:
            tmpdir.cleanup()

    def test_serialize_deserialize(self) -> None:
        config = Config(
            eth2_network='pyrmont',
            key_desc=KeyDescriptor(
                algo='argon2id',
                salt=secrets.token_bytes(16),
                checksum=secrets.token_bytes(16),
            ),
            fee_recipient=TEST_ETH_ADDRESS,
            nodes=[
                SSHConnInfo(
                    host='localhost',
                    user='somebody',
                    port=2222,
                    identity_file='test/config/ssh_id.key',
                ),
            ],
            data_dir='/var/lib/validator-supervisor',
            logs_dir='/var/log/validator-supervisor',
            ssl_cert_file=None,
            ssl_key_file=None,
            port_range=(13000, 14000),
            rpc_users={},
        )
        config_dict = ConfigSchema().dump(config)
        config_copy = ConfigSchema().load(config_dict)
        self.assertEqual(config, config_copy)

    def test_serialize_deserialize_to_yaml(self) -> None:
        config = Config(
            eth2_network='pyrmont',
            key_desc=KeyDescriptor(
                algo='argon2id',
                salt=secrets.token_bytes(16),
                checksum=secrets.token_bytes(16),
            ),
            fee_recipient=TEST_ETH_ADDRESS,
            nodes=[
                SSHConnInfo(
                    host='localhost',
                    user='somebody',
                    port=2222,
                    identity_file='test/config/ssh_id.key',
                ),
            ],
            data_dir='/var/lib/validator-supervisor',
            logs_dir='/var/log/validator-supervisor',
            ssl_cert_file=None,
            ssl_key_file=None,
            port_range=(13000, 14000),
            rpc_users={},
        )
        config_dict = ConfigSchema().dump(config)
        config_yaml = yaml.dump(config_dict)
        config_dict_copy = yaml.load(config_yaml, Loader=yaml.Loader)
        config_copy = ConfigSchema().load(config_dict_copy)
        self.assertEqual(config, config_copy)

    def test_deserialize_missing_field(self) -> None:
        key_desc_dict = {
            'salt': b'mmm salty'.hex(),
            'checksum': b'mmm hash'.hex(),
        }
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            KeyDescriptorSchema().load(key_desc_dict)

    def test_deserialize_wrong_field_type(self) -> None:
        key_desc_dict = {
            'algo': 1,
            'salt': b'mmm salty'.hex(),
            'checksum': b'mmm hash'.hex(),
        }
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            KeyDescriptorSchema().load(key_desc_dict)

    def test_deserialize_bad_hex(self):
        key_desc_dict = {
            'algo': 'argon2id',
            'salt': 'mmm tasty',
            'checksum': b"mmm tasty".hex(),
        }
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            KeyDescriptorSchema().load(key_desc_dict)

    def test_deserialize_hex_wrong_type(self):
        key_desc_dict = {
            'algo': 'argon2id',
            'salt': 1,
            'checksum': b"mmm tasty".hex(),
        }
        with self.assertRaises(marshmallow.exceptions.ValidationError):
            KeyDescriptorSchema().load(key_desc_dict)


if __name__ == '__main__':
    unittest.main()
