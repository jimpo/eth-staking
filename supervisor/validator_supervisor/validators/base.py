from __future__ import annotations

from abc import ABC, abstractmethod
import aiohttp
import asyncio.subprocess
from asyncio.subprocess import Process
from dataclasses import dataclass
import logging
import marshmallow
from marshmallow import fields, post_load
import os
from typing import IO, List, Optional, Tuple

from ..backup_archive import check_validator_data_dir
from ..subprocess import HealthCheck, SimpleSubprocess
from ..util import build_docker_image, set_sighup_on_parent_exit

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
    # Host name, port tuple for SSH connection
    host_id: Tuple[str, int]
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
            container_name: str,
    ):
        super().__init__(out_log_filepath, err_log_filepath)
        self.eth2_network = eth2_network
        self.datadir = datadir
        self.release = release
        self.beacon_node_ports = beacon_node_ports
        self._beacon_node_port: Optional[BeaconNodePortMap] = None
        self.container_name = container_name

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

        docker_image_id = await self.build_docker_image()
        docker_opts = await self._launch_docker_opts(self._beacon_node_port)
        return await asyncio.subprocess.create_subprocess_exec(
            'docker', 'run', '--rm',
            # Docker container name acts like a simple mutex
            '--name', self.container_name,
            *docker_opts,
            '--net', 'host',
            '--user', str(os.getuid()),
            docker_image_id,
            stdout=out_log_file,
            stderr=err_log_file,
            preexec_fn=set_sighup_on_parent_exit,
        )

    @abstractmethod
    async def _launch_docker_opts(self, port_map: BeaconNodePortMap) -> List[str]:
        pass

    @classmethod
    async def _beacon_node_healthy(cls, port_map: BeaconNodePortMap) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                api_port = cls._beacon_node_api_port(port_map)
                syncing_url = f"http://localhost:{api_port}/eth/v1/node/syncing"
                async with session.get(syncing_url) as response:
                    if response.status != 200:
                        return False

                    payload = await response.json()
                    if not isinstance(payload, dict):
                        return False

                    data = payload.get('data')
                    if not isinstance(data, dict):
                        return False

                    return data.get('is_syncing', None) is False

        except aiohttp.ClientConnectionError:
            LOG.debug('Connection error')
            return False

        except asyncio.TimeoutError:
            LOG.debug('Timeout error')
            return False

    @classmethod
    @abstractmethod
    def _beacon_node_api_port(cls, port_map: BeaconNodePortMap) -> int:
        pass

    def health_check(self) -> Optional[HealthCheck]:
        return self._HealthCheck(self, interval=10, retries=2)

    def get_connected_node_host(self) -> Optional[Tuple[str, int]]:
        return self._beacon_node_port.host_id if self._beacon_node_port else None

    class _HealthCheck(HealthCheck):
        def __init__(self, validator: ValidatorRunner, interval: float, retries: int):
            super().__init__(interval, retries)
            self.validator = validator

        async def is_ok(self) -> bool:
            if self.validator._beacon_node_port is None:
                return False
            return await self.validator._beacon_node_healthy(self.validator._beacon_node_port)
