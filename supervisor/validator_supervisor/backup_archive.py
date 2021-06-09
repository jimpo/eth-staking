"""
Module for encrypted archive of validator state backups.

The full state required for a validator to safely resume operation is packed up and backup up in
encrypted archives which can be stored persistently on disk or in the cloud. The backup is designed
to be agnostic to validator implementation, using Ethereum 2.0 interoperable standards such as
EIP-2335 keystores for voting and EIP-3076 slashing protection databases. The files are packed into
tar archives, compressed with xz, and encrypted using libsodium's secret box authenticated
encryption. The archives also contain an authenticated timestamp of the creation time.

The unpacked archive has the following structure:

    slashing-protection.json                        EIP-3076 slashing protection JSON records
    validators/{VALIDATOR_PUBKEY}/keystore.json     EIP-2335 password-protected voting keystore
    validators/{VALIDATOR_PUBKEY}/password.txt      Plaintext password for corresponding keystore
"""

from __future__ import annotations

import logging
import time
import io
import nacl.encoding
import nacl.exceptions
from nacl.secret import SecretBox
import os.path
import re
import struct
import tarfile
from typing import IO, Optional

from .exceptions import MissingValidatorData

LOG = logging.getLogger(__name__)


class LockedArchiveCorrupted(Exception):
    pass


class BackupArchive(object):
    """
    A data IO wrapper over an unencrypted backup.

    This is independent of any particular archived directory layout.
    See module documentation for further details.
    """
    KEY_SIZE = SecretBox.KEY_SIZE

    def __init__(self, data: IO[bytes], timestamp: int):
        self.data = data
        self.timestamp = timestamp

    def lock(self, key: bytes, dst: IO[bytes]) -> int:
        """
        Lock the archive, encrypting the contents to a destination buffer.

        :param key: encryption key
        :param dst: destination buffer
        :return: number of bytes written
        """
        self.data.seek(0)
        plaintext = struct.pack("<I", self.timestamp) + self.data.read()
        msg = SecretBox(key).encrypt(plaintext)
        dst.write(msg.nonce)
        dst.write(msg.ciphertext)
        return len(msg.nonce) + len(msg.ciphertext)

    @classmethod
    def unlock(cls, key: bytes, src: IO[bytes], file: Optional[IO[bytes]] = None) -> BackupArchive:
        """
        Unlock an archive, decrypting the contents from a source buffer.

        :param key: the encryption key
        :param src: buffer containing locked archive contents
        :param file: a buffer to use for the unlocked archive contents, defaults to an in-memory
            byte buffer
        :return: the backup archive
        :raise LockedArchiveCorrupted: if decryption fails
        """
        data = file if file is not None else io.BytesIO()
        nonce = src.read(SecretBox.NONCE_SIZE)
        ciphertext = src.read()
        try:
            plaintext = SecretBox(key).decrypt(ciphertext, nonce)
        except nacl.exceptions.CryptoError:
            raise LockedArchiveCorrupted()
        timestamp, = struct.unpack("<I", plaintext[:4])
        data.write(plaintext[4:])
        return BackupArchive(data, timestamp)

    @classmethod
    def pack(cls, root_dir: str, file: Optional[IO[bytes]] = None) -> BackupArchive:
        """
        Create an archive from an expanded directory structure.

        :param root_dir: directory to archive
        :param file: a buffer to use for the unlocked archive contents, defaults to an in-memory
            byte buffer
        :return: the backup archive
        """
        data = file if file is not None else io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:xz') as tar:
            for path in os.listdir(root_dir):
                tar.add(os.path.join(root_dir, path), path)
        return cls(data, int(time.time()))

    def unpack(self, root_dir: str):
        """
        Unpack the archive to an empty directory.

        :param root_dir: the directory to write archived files to
        """
        self.data.seek(0)
        with tarfile.open(fileobj=self.data, mode='r:xz') as tar:
            tar.extractall(root_dir)


def check_validator_data_dir(data_dir: str):
    """
    Checks a validator state directory for proper structure.

    Does not check for extraneous files, only missing files.
    TODO: ^Would be nice to add a strict mode that does this though.

    :param data_dir: Directory containing validator state files
    :raise MissingValidatorData: if any validator state files are missing
    """
    if not os.path.isdir(data_dir):
        raise MissingValidatorData('missing validator data directory')
    if not os.path.isfile(os.path.join(data_dir, 'slashing-protection.json')):
        raise MissingValidatorData('missing slashing-protection.json file')

    validators_dir = os.path.join(data_dir, 'validators')
    if not os.path.isdir(validators_dir):
        raise MissingValidatorData('missing validators directory')
    for validator_name in os.listdir(validators_dir):
        if not re.fullmatch(r"0x[0-9a-f]{96}", validator_name):
            continue

        validator_dir = os.path.join(validators_dir, validator_name)
        if not os.path.isdir(validator_dir):
            continue

        if not os.path.isfile(os.path.join(validator_dir, 'keystore.json')):
            raise MissingValidatorData(f"missing keystore.json for {validator_name}")
        if not os.path.isfile(os.path.join(validator_dir, 'password.txt')):
            raise MissingValidatorData(f"missing password.txt for {validator_name}")


def make_validator_data_backup(backup_key: bytes, backup_path: str, data_dir: str):
    """
    Create a new backup archive with the latest validator state.

    :param backup_key: the encryption key for the backup
    :param backup_path: path for the created archive file
    :param data_dir: directory containing validator state files
    :raise MissingValidatorData: if any validator state files are missing
    """
    check_validator_data_dir(data_dir)

    with open(backup_path, 'wb') as dst:
        archive = BackupArchive.pack(data_dir)
        bytes_written = archive.lock(backup_key, dst)
    LOG.debug(f"Wrote backup to {backup_path}, {bytes_written} bytes")
