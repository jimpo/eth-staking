import asyncio
from asyncio.subprocess import Process
import logging
import os.path
from typing import IO, Optional

from ..backup_archive import check_validator_data_dir
from ..util import build_docker_image
from .base import ValidatorRunner

LOG = logging.getLogger(__name__)
PRYSM_VERSION = "v1.4.3"


class PrysmValidator(ValidatorRunner):
    """
    NOTE: This doesn't work yet.
    """
    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        check_validator_data_dir(self.datadir)

        image_id = await build_docker_image('prysm', PRYSM_VERSION)
        return await asyncio.subprocess.create_subprocess_exec(
            'docker', 'run', '--rm',
            '--name', f"validator-supervisor_{os.getpid()}_prysm",
            '-e', f"ETH2_NETWORK={self.eth2_network}",
            '-e', f"BEACON_NODES=http://localhost:5052",
            '--net', 'host',
            '--volume', f"{os.path.abspath(self.datadir)}:/home/somebody/canonical",
            '--user', str(os.getuid()),
            image_id,
            stdout=out_log_file,
            stderr=err_log_file,
        )
