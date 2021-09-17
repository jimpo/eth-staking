"""
Command line interface for manipulating configuration file.
"""

import getpass
import os
import sys
from typing import Optional, Tuple

from .backup_archive import make_validator_data_backup
from .config import \
    DEFAULT_VALIDATOR_RELEASE, DEFAULT_BACKUP_FILENAME, Config, InvalidConfig, \
    read_config, write_config
from .exceptions import MissingValidatorData
from .key_ops import KeyDescriptor, IncorrectPassword, RootKey
from .rpc.auth import gen_user_key

DEFAULT_PORT_RANGE = (13000, 14000)


def read_yesno(prompt: str) -> bool:
    answer = input(prompt + " (y/n) ")
    while True:
        if answer in {'y', 'Y'}:
            return True
        elif answer in {'n', 'N'}:
            return False
        else:
            answer = input("Enter (y/n): ")


def read_str(prompt: str, default: Optional[str] = None) -> str:
    if default:
        answer = input(f"{prompt} (default: {default}): ")
        if not answer:
            answer = default
    else:
        answer = input(f"{prompt}: ")
        while not answer:
            print(f"{prompt} cannot be blank")
            answer = input(f"{prompt}: ")
    return answer


def read_int(prompt: str, default: Optional[int] = None) -> int:
    while True:
        answer_str = read_str(prompt, str(default) if default is not None else None)
        try:
            return int(answer_str)
        except ValueError:
            print(f"{prompt} must be an integer")


def perform_setup(config_path: str):
    config, key = init_config(config_path)
    backup_path = os.path.join(config.data_dir, config.backup_filename)
    if os.path.isfile(backup_path):
        return

    init_backup = read_yesno("No supervisor backup found locally. Create one?")
    if not init_backup:
        return

    validator_canonical_dir = read_str(
        "Initialize the canonical validator data directory and enter the path"
    )
    try:
        make_validator_data_backup(key.derive_backup_key(), config.backup_path, validator_canonical_dir)
        print("Saved backup!")
    except MissingValidatorData as err:
        print(f"The directory {validator_canonical_dir} is missing required files: {err.args}")
        print("Initialize it yourself (carefully!) and re-run setup to create a supervisor "
              "backup.")


def init_config(config_path: str) -> Tuple[Config, RootKey]:
    if os.path.isfile(config_path):
        try:
            old_config: Optional[Config] = read_config(config_path)
        except InvalidConfig as err:
            sys.stderr.write(
                f"Existing config at path {config_path} is invalid: {err}\n"
                "Manually fix or delete the existing one to continue"
            )
            sys.exit(1)
    else:
        old_config = None

    key_desc = None
    if old_config:
        keep_existing = read_yesno("A key has already been set. Keep the existing one?")
        if keep_existing:
            key_desc = old_config.key_desc

    if key_desc is None:
        password = getpass.getpass('Enter a passphrase: ')
        key_desc, _key = KeyDescriptor.generate(password)

    password = getpass.getpass('Confirm passphrase: ')
    while True:
        try:
            key = key_desc.open(password)
            break
        except IncorrectPassword:
            password = getpass.getpass('Incorrect. Confirm passphrase: ')

    eth2_network = read_str(
        "Ethereum 2.0 network",
        old_config.eth2_network if old_config else None
    )

    # Doesn't seem necessary to integrate this into the interactive setup.
    print("Nodes can be manually edited in config.yaml")
    nodes = old_config.nodes if old_config else []

    data_dir = read_str(
        "Data directory absolute path",
        old_config.data_dir if old_config else None
    )
    logs_dir = read_str(
        "Logs directory absolute path",
        old_config.logs_dir if old_config else None
    )
    ssl_cert_file = old_config.ssl_cert_file if old_config else None
    ssl_key_file = old_config.ssl_key_file if old_config else None
    port_range = old_config.port_range if old_config else DEFAULT_PORT_RANGE
    rpc_users = old_config.rpc_users if old_config else {}
    validator_release = old_config.validator_release if old_config else DEFAULT_VALIDATOR_RELEASE
    backup_filename = old_config.backup_filename if old_config else DEFAULT_BACKUP_FILENAME

    updated = False
    add_user = read_yesno("Add a new RPC user?")
    while add_user:
        user = read_str("User ID")
        auth_key = gen_user_key()
        rpc_users[user] = auth_key
        print(f"User {user} has auth key: {auth_key}")
        updated = True
        add_user = read_yesno("Add another RPC user?")

    config = Config(
        eth2_network=eth2_network,
        key_desc=key_desc,
        nodes=nodes,
        data_dir=data_dir,
        logs_dir=logs_dir,
        ssl_cert_file=ssl_cert_file,
        ssl_key_file=ssl_key_file,
        port_range=port_range,
        rpc_users=rpc_users,
        validator_release=validator_release,
        backup_filename=backup_filename,
    )
    if not updated and config == old_config:
        return config, key

    overwrite_config = read_yesno("Overwrite the existing config?")
    if not overwrite_config:
        sys.exit(1)

    write_config(config_path, config)
    print("Wrote new config!")
    return config, key
