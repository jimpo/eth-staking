import aiohttp
import asyncio
from asyncio.subprocess import Process
import logging
import os.path
from typing import IO, Optional

from ..util import set_sighup_on_parent_exit
from .base import BeaconNodePortMap, ValidatorRunner

LOG = logging.getLogger(__name__)


class PrysmValidator(ValidatorRunner):
    async def _launch_validator(
            self,
            docker_image_id: str,
            beacon_node_port: BeaconNodePortMap,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        return await asyncio.subprocess.create_subprocess_exec(
            'docker', 'run', '--rm',
            # Docker container name acts like a simple mutex
            '--name', f"validator-supervisor_validator",
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"BEACON_HTTP_ENDPOINT=localhost:{beacon_node_port.prysm_http}",
            '-e', f"BEACON_GRPC_ENDPOINT=localhost:{beacon_node_port.prysm_grpc}",
            '--net', 'host',
            '--volume', f"{os.path.abspath(self.datadir)}:/app/canonical",
            '--tmpfs', "/app/prysm",
            '--user', str(os.getuid()),
            docker_image_id,
            stdout=out_log_file,
            stderr=err_log_file,
            preexec_fn=set_sighup_on_parent_exit,
        )

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
