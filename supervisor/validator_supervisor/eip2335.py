from dataclasses import dataclass
import marshmallow
from marshmallow import fields, post_load
from typing import Optional


@dataclass
class EIP2335Module:
    function: str
    params: object
    message: str


@dataclass
class EIP2335KeystoreCrypto:
    kdf: EIP2335Module
    checksum: EIP2335Module
    cipher: EIP2335Module


@dataclass
class EIP2335Keystore:
    crypto: EIP2335KeystoreCrypto
    name: Optional[str]
    description: Optional[str]
    path: str
    pubkey: str
    uuid: str
    version: int


class EIP2335ModuleSchema(marshmallow.Schema):
    function = fields.Str(required=True)
    params = fields.Dict(keys=fields.Str(), required=True)
    message = fields.Str(required=True)

    @post_load
    def build(self, data, **_kwargs) -> EIP2335Module:
        return EIP2335Module(**data)


class EIP2335KeystoreCryptoSchema(marshmallow.Schema):
    kdf = fields.Nested(EIP2335ModuleSchema, required=True)
    checksum = fields.Nested(EIP2335ModuleSchema, required=True)
    cipher = fields.Nested(EIP2335ModuleSchema, required=True)

    @post_load
    def build(self, data, **_kwargs) -> EIP2335KeystoreCrypto:
        return EIP2335KeystoreCrypto(**data)


class EIP2335KeystoreSchema(marshmallow.Schema):
    crypto = fields.Nested(EIP2335KeystoreCryptoSchema, required=True)
    description = fields.Str()
    name = fields.Str(allow_none=True)
    path = fields.Str(required=True)
    version = fields.Int(required=True)
    pubkey = fields.Str(required=True)
    uuid = fields.UUID(required=True)

    @post_load
    def build(self, data, **_kwargs) -> EIP2335Keystore:
        return EIP2335Keystore(**data)
