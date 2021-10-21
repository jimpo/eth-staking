import aiohttp
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
    async def _beacon_node_healthy(cls, port_map: BeaconNodePortMap) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                syncing_url = f"http://localhost:{port_map.prysm_http}/eth/v1/node/syncing"
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
            return False
