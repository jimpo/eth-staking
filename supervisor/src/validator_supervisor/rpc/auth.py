"""
User authentication protocol support.

Uses Blake2b as a MAC on random challenge strings for authentication.
"""

from nacl.encoding import RawEncoder
from nacl.hash import BLAKE2B_PERSONALBYTES, blake2b
import nacl.utils
import secrets

CHALLENGE_SIZE = 16
AUTH_KEY_SIZE = 16
AUTH_PERSON = blake2b(
    b"VALIDATOR SUPERVISOR RPC AUTH",
    digest_size=BLAKE2B_PERSONALBYTES,
    encoder=RawEncoder,
)


def gen_user_key() -> str:
    return nacl.utils.random(AUTH_KEY_SIZE).hex()


def gen_auth_challenge() -> str:
    return nacl.utils.random(CHALLENGE_SIZE).hex()


def auth_response(key: str, challenge: str) -> str:
    return blake2b(
        challenge.encode(),
        key=key.encode(),
        person=AUTH_PERSON,
        encoder=RawEncoder,
    ).hex()


def check_auth_response(key: str, challenge: str, response: str) -> bool:
    return secrets.compare_digest(auth_response(key, challenge), response)
