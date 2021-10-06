from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio.subprocess import Process
from dataclasses import dataclass
import logging
import marshmallow
from marshmallow import fields, post_load
from typing import IO, List, Optional

from ..backup_archive import check_validator_data_dir
from ..subprocess import HealthCheck, SimpleSubprocess
from ..util import build_docker_image

LOG = logging.getLogger(__name__)


@dataclass
class ValidatorRelease:
    impl_name: str
    version: str
    # SHA256 checksum of the precompiled binary release
    checksum: str


class ValidatorReleaseSchema(marshmallow.Schema):
    """
    Serialization schema for ValidatorRelease.
    """
    impl_name = fields.Str(required=True)
    version = fields.Str(required=True)
    checksum = fields.Str(required=True)

    @post_load
    def build(self, data, **_kwargs) -> ValidatorRelease:
        return ValidatorRelease(**data)


@dataclass
class BeaconNodePortMap:
    lighthouse_rpc: int
    prysm_http: int
    prysm_grpc: int


class ValidatorRunner(SimpleSubprocess, ABC):
    def __init__(
            self,
            eth2_network: str,
            datadir: str,
            out_log_filepath: str,
            err_log_filepath: str,
            beacon_node_ports: List[BeaconNodePortMap],
            release: ValidatorRelease,
    ):
        super().__init__(out_log_filepath, err_log_filepath)
        self.eth2_network = eth2_network
        self.datadir = datadir
        self.release = release
        self.beacon_node_ports = beacon_node_ports
        self._beacon_node_port: Optional[BeaconNodePortMap] = None

    async def build_docker_image(self) -> str:
        return await build_docker_image(
            self.release.impl_name,
            self.release.version,
            build_args={
                'VERSION': self.release.version,
                'CHECKSUM': self.release.checksum,
            },
        )

    async def _find_healthy_beacon_node(self) -> Optional[BeaconNodePortMap]:
        for port_map in self.beacon_node_ports:
            if await self._beacon_node_healthy(port_map):
                return port_map
        return None

    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        check_validator_data_dir(self.datadir)

        self._beacon_node_port = await self._find_healthy_beacon_node()
        if self._beacon_node_port is None:
            LOG.warning("No healthy beacon nodes found")
            return None

        image_id = await self.build_docker_image()
        return await self._launch_validator(
            image_id,
            self._beacon_node_port,
            out_log_file,
            err_log_file,
        )

    @abstractmethod
    async def _launch_validator(
            self,
            docker_image_id: str,
            beacon_node_port: BeaconNodePortMap,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        pass

    @classmethod
    @abstractmethod
    async def _beacon_node_healthy(cls, port_map: BeaconNodePortMap) -> bool:
        pass

    def health_check(self) -> Optional[HealthCheck]:
        return self._HealthCheck(self, interval=10, retries=2)

    class _HealthCheck(HealthCheck):
        def __init__(self, validator: ValidatorRunner, interval: float, retries: int):
            super().__init__(interval, retries)
            self.validator = validator

        async def is_ok(self) -> bool:
            if self.validator._beacon_node_port is None:
                return False
            return await self.validator._beacon_node_healthy(self.validator._beacon_node_port)
