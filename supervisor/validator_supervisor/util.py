"""
The util file.

What, you think a project could exist without one?
"""

import asyncio
from asyncio import FIRST_COMPLETED
import logging
from pkg_resources import resource_filename
from subprocess import PIPE
from typing import Awaitable, Optional

from .exceptions import DockerBuildException

LOG = logging.getLogger(__name__)


class ExitMixin(object):
    _exit_event: asyncio.Event

    async def _either_or_exit(self, awaitable: Awaitable) -> Optional[Awaitable]:
        """
        Wait for either the given awaitable or for this to exit. If the exit happens first, return
        the pending task as an awaitable.

        :param awaitable:
        :return:
        """
        _done, pending = await asyncio.wait(
            [awaitable, self._exit_event.wait()],
            return_when=FIRST_COMPLETED,
        )
        if self._exit_event.is_set() and pending:
            assert len(pending) == 1
            return list(pending)[0]
        return None

    @property
    def _exited(self) -> bool:
        return self._exit_event.is_set()


async def build_docker_image(image_name: str, version: str) -> str:
    """
    Build a Docker image from a context in the images/ directory.

    Tags the image with the version.

    :param image_name: name of the image in the images/ directory
    :param version: a version string
    :return: the Docker image ID
    """
    image_tag = f"validator-supervisor/{image_name}:{version}"
    context_dir = resource_filename('validator_supervisor', f"images/{image_name}")
    LOG.debug(f"Building Docker image {image_tag}...")
    build_proc = await asyncio.create_subprocess_exec(
        'docker', 'build', '-t', image_tag, context_dir, '--quiet',
        stdout=PIPE, stderr=PIPE,
    )
    image_id_encoded, err_encoded = await build_proc.communicate()
    if build_proc.returncode != 0:
        raise DockerBuildException(
            f"docker build for {image_name} failed with exit code {build_proc.returncode}",
            err_encoded,
        )

    image_id = image_id_encoded.decode().strip()
    LOG.debug(f"Built Docker image {image_tag}: {image_id}")
    return image_id
