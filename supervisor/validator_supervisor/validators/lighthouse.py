from __future__ import annotations

import aiohttp
import asyncio
from asyncio.subprocess import Process
import logging
import os
from typing import IO, Optional

from ..backup_archive import check_validator_data_dir
from ..subprocess import HealthCheck
from ..util import build_docker_image, set_sighup_on_parent_exit
from .base import ValidatorRunner

LOG = logging.getLogger(__name__)


class LighthouseValidator(ValidatorRunner):
    async def _find_healthy_beacon_node(self) -> Optional[int]:
        for port in self.beacon_node_ports:
            if await _beacon_node_healthy(port):
                return port
        return None

    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        check_validator_data_dir(self.datadir)

        self._beacon_node_port = await self._find_healthy_beacon_node()
        if self._beacon_node_port is None:
            LOG.warning("No healthy lighthouse beacon nodes found")
            return None

        image_id = await self.build_docker_image()
        return await asyncio.subprocess.create_subprocess_exec(
            'docker', 'run', '--rm',
            '--name', f"validator-supervisor_{os.getpid()}_lighthouse",
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"BEACON_NODES=http://localhost:{self._beacon_node_port}",
            '--net', 'host',
            '--volume', f"{os.path.abspath(self.datadir)}:/app/canonical",
            '--tmpfs', "/app/lighthouse",
            '--user', str(os.getuid()),
            image_id,
            stdout=out_log_file,
            stderr=err_log_file,
            preexec_fn=set_sighup_on_parent_exit,
        )

    def health_check(self) -> Optional[HealthCheck]:
        return self._HealthCheck(self, interval=10, retries=2)

    class _HealthCheck(HealthCheck):
        def __init__(self, validator: LighthouseValidator, interval: float, retries: int):
            super().__init__(interval, retries)
            self.validator = validator

        async def is_ok(self) -> bool:
            if self.validator._beacon_node_port is None:
                return False
            return await _beacon_node_healthy(self.validator._beacon_node_port)


async def _beacon_node_healthy(beacon_node_port: int) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            syncing_url = f"http://localhost:{beacon_node_port}/lighthouse/syncing"
            async with session.get(syncing_url) as response:
                if response.status != 200:
                    return False

                payload = await response.json()
                return isinstance(payload, dict) and payload.get('data') == 'Synced'

    except aiohttp.ClientConnectionError:
        return False
