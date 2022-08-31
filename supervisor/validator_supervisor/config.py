"""
Configuration data structures and serialization/deserialization code.
"""

from dataclasses import dataclass
import marshmallow
from marshmallow import fields, post_load
import os.path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml
import yaml.parser

from .key_ops import KeyDescriptor, RootKey
from .exceptions import UnlockRequired
from .ssh import SSHConnInfo, DEFAULT_BASTION_SSH_USER, DEFAULT_BASTION_SSH_PORT
from .validators import ValidatorRelease, ValidatorReleaseSchema

CONFIG_VERSION = 1
SUPERVISOR_LOG_NAME = 'supervisor.log'
DEFAULT_BACKUP_FILENAME = 'supervisor-backup.bin'
DEFAULT_VALIDATOR_RELEASE = ValidatorRelease(
    impl_name='lighthouse',
    version='v3.0.0',
    checksum='23e898614d370f16144f5f3c8f3d3e387fed10caa17bad2bb24395d76f18cbc9',
)


class InvalidConfig(Exception):
    pass


class HexDataField(fields.String):
    default_error_messages = {
        "invalid_hex": "Not a hex-encoded string.",
    }

    def _serialize(self, value, attr, obj, **kwargs) -> Optional[str]:
        return super()._serialize(value.hex() if value is not None else None, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs) -> Any:
        hex_value = super()._deserialize(value, attr, data, **kwargs)
        try:
            return bytes.fromhex(hex_value) if hex_value is not None else None
        except ValueError as err:
            raise self.make_error('invalid_hex') from err


def validate_ethereum_address(value: str):
    # Does not validate checksum because I don't want to pull in a dependency for that
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise marshmallow.exceptions.ValidationError("Value must be an Ethereum address")


@dataclass
class Config:
    """
    Validator supervisor daemon configuration data.
    """
    eth2_network: str
    key_desc: KeyDescriptor
    fee_recipient: str
    nodes: List[SSHConnInfo]
    data_dir: str
    logs_dir: str
    ssl_cert_file: Optional[str]
    ssl_key_file: Optional[str]
    port_range: Tuple[int, int]
    rpc_users: Dict[str, str]
    backup_filename: str = DEFAULT_BACKUP_FILENAME

    @property
    def backup_path(self) -> str:
        return os.path.join(self.data_dir, self.backup_filename)

    @property
    def supervisor_log_path(self) -> str:
        return os.path.join(self.logs_dir, SUPERVISOR_LOG_NAME)

    def validator_log_path(self, validator_impl: str) -> str:
        return os.path.join(self.logs_dir, f"{validator_impl}.log")


@dataclass
class DynamicConfig:
    """
    Validator supervisor configuration that can change dynamically at runtime.

    This acts like a database of configuration state.
    """
    validator_release: ValidatorRelease = DEFAULT_VALIDATOR_RELEASE


class KeyDescriptorSchema(marshmallow.Schema):
    """
    Serialization schema for KeyDescriptor.
    """
    algo = fields.Str(required=True)
    salt = HexDataField(required=True)
    checksum = HexDataField(required=True)

    @post_load
    def build(self, data, **_kwargs) -> KeyDescriptor:
        return KeyDescriptor(**data)


class SSHConnInfoSchema(marshmallow.Schema):
    """
    Serialization schema for SSHConnInfo.
    """
    host = fields.Str(required=True)
    user = fields.Str(missing=DEFAULT_BASTION_SSH_USER)
    port = fields.Int(missing=DEFAULT_BASTION_SSH_PORT)
    pubkey = fields.Str(allow_none=True)
    identity_file = fields.Str(allow_none=True)

    @post_load
    def build(self, data, **_kwargs) -> SSHConnInfo:
        return SSHConnInfo(**data)


class ConfigSchema(marshmallow.Schema):
    """
    Serialization schema for Config..
    """
    eth2_network = fields.Str(required=True)
    key_desc = fields.Nested(KeyDescriptorSchema, required=True, data_key='key_descriptor')
    fee_recipient = fields.Str(required=True, validate=validate_ethereum_address)
    nodes = fields.List(fields.Nested(SSHConnInfoSchema), required=True)
    data_dir = fields.Str(required=True)
    logs_dir = fields.Str(required=True)
    ssl_cert_file = fields.Str(missing=None)
    ssl_key_file = fields.Str(missing=None)
    port_range = fields.Tuple((fields.Int(), fields.Int()), required=True)
    rpc_users = fields.Dict(keys=fields.Str(), values=fields.Str())
    backup_filename = fields.Str(default=DEFAULT_BACKUP_FILENAME)

    @post_load
    def build(self, data, **_kwargs) -> Config:
        return Config(**data)


class DynamicConfigSchema(marshmallow.Schema):
    """
    Serialization schema for DynamicConfig..
    """
    validator_release = fields.Nested(ValidatorReleaseSchema, default=DEFAULT_VALIDATOR_RELEASE)

    @post_load
    def build(self, data, **_kwargs) -> DynamicConfig:
        return DynamicConfig(**data)


def read_config(config_path: str) -> Config:
    """
    Read and deserialize configuration struct from a YAML file.

    :param config_path: path to YAML file
    :return: config struct
    """
    try:
        with open(config_path, 'rb') as f:
            config_dict = yaml.load(f, Loader=yaml.Loader)
    except FileNotFoundError:
        raise InvalidConfig(f"config file not found at {config_path}")
    except yaml.parser.ParserError:
        raise InvalidConfig("config file is not valid YAML")

    version = config_dict.pop('version', 1)
    if version == 1:
        try:
            return ConfigSchema().load(config_dict)
        except marshmallow.exceptions.ValidationError as err:
            raise InvalidConfig(err.args) from err
    else:
        raise InvalidConfig(f"unsupported config version {version}")


def write_config(config_path: str, config: Config):
    """
    Serialize and write configuration struct to a YAML file.

    :param config_path: path to the YAML file
    :param config: config struct
    """
    config_dict = ConfigSchema().dump(config)
    config_dict['version'] = 1
    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f)


def read_dynamic_config(path: str) -> DynamicConfig:
    """
    Read and deserialize dynamic configuration state from a YAML file.

    :param path: path to YAML file
    :return: dynamic config struct
    """
    try:
        with open(path, 'rb') as f:
            config_dict = yaml.load(f, Loader=yaml.Loader)
    except FileNotFoundError:
        raise InvalidConfig(f"dynamic config file not found at {path}")
    except yaml.parser.ParserError:
        raise InvalidConfig("dynamic config file is not valid YAML")

    version = config_dict.pop('version', 1)
    if version == 1:
        try:
            return DynamicConfigSchema().load(config_dict)
        except marshmallow.exceptions.ValidationError as err:
            raise InvalidConfig(err.args) from err
    else:
        raise InvalidConfig(f"unsupported dynamic config version {version}")


def write_dynamic_config(path: str, config: DynamicConfig):
    """
    Serialize and write configuration struct to a YAML file.

    :param path: path to the YAML file
    :param config: dynamic config struct
    """
    config_dict = DynamicConfigSchema().dump(config)
    config_dict['version'] = 1
    with open(path, 'w') as f:
        yaml.dump(config_dict, f)


def read_root_key(key_desc: KeyDescriptor, root_key_path: str) -> RootKey:
    """
    Read a hex-encoded root key from a text file.

    :param key_desc: the descriptor committing to the key
    :param root_key_path: the file with the hex-encoded key
    :return: the root key
    """
    try:
        with open(root_key_path, 'r') as f:
            key = bytes.fromhex(f.read())
    except FileNotFoundError:
        raise UnlockRequired()

    root_key = key_desc.check_key(key)
    if root_key is None:
        raise UnlockRequired()
    return root_key


def write_root_key(root_key: RootKey, root_key_path: str):
    """
    Write a hex-encoded root key to a text file.

    :param root_key: the root key
    :param root_key_path: the file to write the hex-encoded key to
    """
    if not os.path.isfile(root_key_path):
        with open(root_key_path, 'w') as _:
            pass
    os.chmod(root_key_path, 0o600)

    with open(root_key_path, 'w') as f:
        f.write(root_key.hex())
