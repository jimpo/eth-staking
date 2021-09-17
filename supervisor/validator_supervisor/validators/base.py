from abc import ABC
from dataclasses import dataclass
from typing import List, Optional

from ..subprocess import SimpleSubprocess
from ..util import build_docker_image


@dataclass
class ValidatorRelease:
    impl_name: str
    version: str
    # SHA256 checksum of the precompiled binary release
    checksum: str


@dataclass
class BeaconNodePortMap:
    lighthouse_rpc: int
    prysm_rpc: int
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
