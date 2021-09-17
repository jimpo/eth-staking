"""JSON-RPC 2.0 support code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import random
from typing import Dict, Optional

from ..validators import ValidatorRelease

ID_LIMIT = 10000
BEGIN_UNLOCK_RESULT = "ENTER PASSPHRASE"


class MalformedJsonRpc(Exception):
    pass


@dataclass
class JsonRpcRequest(object):
    """A JSON-RPC 2.0 request payload."""
    method: str
    call_id: int
    params: object

    def __init__(
            self,
            method: str,
            call_id: Optional[int] = None,
            params: Optional[object] = None,
    ):
        self.method = method
        self.call_id = call_id if call_id is not None else generate_random_call_id()
        self.params = params if params is not None else []

    def to_json(self) -> object:
        """Returns a JSON-serializable dict."""
        return {
            'jsonrpc': '2.0',
            'method': self.method,
            'params': self.params,
            'id': self.call_id,
        }

    @classmethod
    def from_json(cls, msg: object) -> JsonRpcRequest:
        """Parses from a JSON-deserialized dict."""
        if (not isinstance(msg, dict) or
                msg.get('jsonrpc', None) != '2.0'):
            raise MalformedJsonRpc(msg)

        method = msg.get('method', None)
        call_id = msg.get('id', None)
        params = msg.get('params', None)

        if (not isinstance(method, str) or
                not isinstance(call_id, int) or
                params is None):
            raise MalformedJsonRpc(msg)

        return cls(
            method,
            call_id,
            params,
        )


@dataclass
class JsonRpcResponse:
    """A JSON-RPC 2.0 response payload."""
    call_id: Optional[int]
    result: object
    is_error: bool = False

    def to_json(self) -> object:
        """Returns a JSON-serializable dict."""
        json_obj: Dict[str, object] = {
            'jsonrpc': '2.0',
            'id': self.call_id,
        }
        if self.is_error:
            json_obj['error'] = self.result
        else:
            json_obj['result'] = self.result
        return json_obj

    @classmethod
    def from_json(cls, msg: object) -> JsonRpcResponse:
        """Parses from a JSON-deserialized dict."""
        if (not isinstance(msg, dict) or
                msg.get('jsonrpc', None) != '2.0'):
            raise MalformedJsonRpc(msg)

        try:
            call_id = msg['id']
        except KeyError:
            raise MalformedJsonRpc(msg)
        if not (call_id is None or isinstance(call_id, int)):
            raise MalformedJsonRpc(msg)

        if 'result' in msg and 'error' not in msg:
            is_error = False
            result = msg['result']
        elif 'error' in msg and 'result' not in msg:
            is_error = True
            result = msg['error']
        else:
            raise MalformedJsonRpc(msg)

        return cls(
            call_id,
            result,
            is_error,
        )


def generate_random_call_id() -> int:
    return random.randrange(ID_LIMIT)


class RpcTarget(ABC):
    """
    Abstract interface representing the RpcServer's view of the ValidatorSupervisor.

    See ValidatorSupervisor for method documentation.
    """

    @abstractmethod
    async def get_health(self) -> Dict[str, object]:
        pass

    @abstractmethod
    async def start_validator(self) -> bool:
        pass

    @abstractmethod
    async def stop_validator(self) -> bool:
        pass

    @abstractmethod
    async def connect_eth2_node(self, host: str, port: Optional[int]):
        pass

    @abstractmethod
    async def set_validator_release(self, release: ValidatorRelease):
        pass

    @abstractmethod
    async def unlock(self, password: str) -> bool:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass
