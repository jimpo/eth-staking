from __future__ import annotations

import aiohttp
import logging
import os
from typing import List

from .base import BeaconNodePortMap, ValidatorRunner

LOG = logging.getLogger(__name__)


class LighthouseValidator(ValidatorRunner):
    async def _launch_docker_opts(self, port_map: BeaconNodePortMap) -> List[str]:
        return [
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"BEACON_NODES=http://localhost:{port_map.lighthouse_rpc}",
            '--volume', f"{os.path.abspath(self.datadir)}:/app/canonical",
            '--tmpfs', "/app/lighthouse",
        ]

    @classmethod
    async def _beacon_node_healthy(cls, port_map: BeaconNodePortMap) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                syncing_url = f"http://localhost:{port_map.lighthouse_rpc}/eth/v1/node/syncing"
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
