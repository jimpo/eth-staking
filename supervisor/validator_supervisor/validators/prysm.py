from __future__ import annotations

import logging
import os.path
from typing import List

from .base import BeaconNodePortMap, ValidatorRunner

LOG = logging.getLogger(__name__)


class PrysmValidator(ValidatorRunner):
    async def _launch_docker_opts(self, port_map: BeaconNodePortMap) -> List[str]:
        return [
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"BEACON_HTTP_ENDPOINT=localhost:{port_map.prysm_http}",
            '-e', f"BEACON_GRPC_ENDPOINT=localhost:{port_map.prysm_grpc}",
            '--volume', f"{os.path.abspath(self.datadir)}:/app/canonical",
            '--tmpfs', "/app/prysm",
        ]

    @classmethod
    def _beacon_node_api_port(cls, port_map: BeaconNodePortMap) -> int:
        return port_map.prysm_http
