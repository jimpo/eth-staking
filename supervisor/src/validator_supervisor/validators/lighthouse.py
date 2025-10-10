from __future__ import annotations

import logging
import os
from typing import List

from .base import BeaconNodePortMap, ValidatorRunner

LOG = logging.getLogger(__name__)


class LighthouseValidator(ValidatorRunner):
    async def _launch_docker_opts(self, port_map: BeaconNodePortMap) -> List[str]:
        return [
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"FEE_RECIPIENT={self.fee_recipient}",
            '-e', f"BEACON_NODES=http://localhost:{port_map.lighthouse_rpc}",
            '--volume', f"{os.path.abspath(self.datadir)}:/app/canonical",
            '--tmpfs', "/app/lighthouse",
        ]

    @classmethod
    def _beacon_node_api_port(cls, port_map: BeaconNodePortMap) -> int:
        return port_map.lighthouse_rpc
