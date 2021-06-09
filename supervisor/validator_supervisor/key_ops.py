from __future__ import annotations

from dataclasses import dataclass
import nacl.encoding
from nacl.encoding import RawEncoder
import nacl.exceptions
from nacl.hash import BLAKE2B_BYTES, BLAKE2B_PERSONALBYTES, blake2b
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
import secrets
from typing import Optional, Tuple


KEY_CHECKSUM_PERSON = blake2b(
    b"VALIDATOR SUPERVISOR KEY CHECKSUM",
    digest_size=BLAKE2B_PERSONALBYTES,
    encoder=RawEncoder,
)
KEY_DERIVATION_PERSON = blake2b(
    b"VALIDATOR SUPERVISOR KEY DERIVATION",
    digest_size=BLAKE2B_PERSONALBYTES,
    encoder=RawEncoder,
)
DEFAULT_ALGO = 'argon2id'


class IncorrectPassword(Exception):
    pass


class InvalidKeyDescriptor(Exception):
    pass


@dataclass
class RootKey(object):
    """
    A cryptographically secure root key from which other keys are derived.

    The key derivation function is Blake2b with various personalizations.
    """
    SIZE = 16
    BACKUP_KEY_TAG = b'BACKUP KEY'

    data: bytes

    def derive(self, tag: bytes, size: int) -> bytes:
        """
        Derive a deterministic subkey corresponding to the tag and size.

        :param tag: a tag in the derivation path
        :param size: the key size in bytes
        :return: the subkey
        """
        return blake2b(
            tag,
            digest_size=size,
            key=self.data,
            person=KEY_DERIVATION_PERSON,
            encoder=RawEncoder,
        )

    def derive_backup_key(self) -> bytes:
        """
        Derive the backup archive encryption subkey.

        See backup_archive module for more information.

        :return: the backup subkey
        """
        return self.derive(self.BACKUP_KEY_TAG, SecretBox.KEY_SIZE)

    def hex(self) -> str:
        """
        Get a hex representation of the root key.

        :return: a hex string
        """
        return self.data.hex()


@dataclass
class KeyDescriptor:
    """
    Descriptor for password-protected root cryptographic key.

    This is a commitment to a cryptographically secure root key from which other keys are derived.
    The root key can be recovered from a password using an appropriate password hash function like
    Argon2.

    *Both the key descriptor and the password are necessary to recover the key. If either are
    entirely lost, the root key is too.*
    """
    CHECKSUM_SIZE = BLAKE2B_BYTES

    algo: str
    "The PKDF hash algorithm (from PyNaCl/libsodium). Currently supported: argon2id, argon2id_weak."

    salt: bytes
    checksum: bytes

    def open(self, password: str) -> RootKey:
        """
        Derive the matching root key using the password.

        :param password: the password
        :return: the matching root key
        :raise InvalidKeyDescriptor:
        :raise IncorrectPassword:
        """
        if self.algo == 'argon2id':
            opslimit = argon2id.OPSLIMIT_SENSITIVE
            memlimit = argon2id.MEMLIMIT_SENSITIVE
        elif self.algo == 'argon2id_weak':
            opslimit = argon2id.OPSLIMIT_MIN
            memlimit = argon2id.MEMLIMIT_MIN
        else:
            raise InvalidKeyDescriptor("algo must be one of {argon2id, argon2id_weak}")

        if len(self.salt) != argon2id.SALTBYTES:
            raise InvalidKeyDescriptor("salt is incorrect length")
        if len(self.checksum) != self.CHECKSUM_SIZE:
            raise InvalidKeyDescriptor("checksum is incorrect length")

        key = argon2id.kdf(RootKey.SIZE, password.encode(), self.salt, opslimit, memlimit)
        root_key = self.check_key(key)
        if root_key is None:
            raise IncorrectPassword()
        return root_key

    def check_key(self, key_data: bytes) -> Optional[RootKey]:
        """
        Check if the key matches the key descriptor.

        :param key_data: the key
        :return: a root if the descriptor matches
        """
        if not secrets.compare_digest(self.checksum, self._checksum(key_data)):
            return None
        return RootKey(key_data)

    @classmethod
    def generate(cls, password: str, algo: str = DEFAULT_ALGO) -> Tuple[KeyDescriptor, RootKey]:
        """
        Generate a new, randomized root key and descriptor from a password.

        :param password: a password protecting the root key
        :param algo: a PKDF hash algorithm (from PyNaCl/libsodium), currently supported:
            argon2id, argon2id_weak
        :return: a key descriptor and matching root key
        """
        if algo == 'argon2id':
            opslimit = argon2id.OPSLIMIT_SENSITIVE
            memlimit = argon2id.MEMLIMIT_SENSITIVE
        elif algo == 'argon2id_weak':
            opslimit = argon2id.OPSLIMIT_MIN
            memlimit = argon2id.MEMLIMIT_MIN
        else:
            raise ValueError("algo must be one of {argon2id, argon2id_weak}")

        salt = nacl.utils.random(argon2id.SALTBYTES)
        key_data = argon2id.kdf(RootKey.SIZE, password.encode(), salt, opslimit, memlimit)
        checksum = cls._checksum(key_data)
        return cls(algo, salt, checksum), RootKey(key_data)

    @staticmethod
    def _checksum(key_data: bytes) -> bytes:
        return blake2b(b'', key=key_data, person=KEY_CHECKSUM_PERSON, encoder=RawEncoder)
