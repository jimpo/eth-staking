"""
The util file.

What, you think a project could exist without one?
"""

import asyncio
import signal
from asyncio import Task, FIRST_COMPLETED
from collections.abc import Iterable
import logging
from pkg_resources import resource_filename
import prctl
from subprocess import PIPE
from typing import Awaitable, Dict, Optional

from .exceptions import DockerBuildException

LOG = logging.getLogger(__name__)


async def either_or_interrupt(
        awaitable: Awaitable,
        interrupts: Iterable[Awaitable],
) -> Optional[Task]:
    """
    Wait for either the given awaitable or for an interrupt event. If the interrupt happens first,
    return the pending task. All interrupts must be cancellable.

    :param awaitable:
    :param interrupts: a collection of cancellable interrupts
    :return: the pending task if exited early or None if it completed
    """
    main_task = asyncio.ensure_future(awaitable)
    wait_tasks = list(map(asyncio.ensure_future, interrupts))
    wait_tasks.append(main_task)
    _done, pending = await asyncio.wait(wait_tasks, return_when=FIRST_COMPLETED)
    for interrupt_task in pending - {main_task}:
        interrupt_task.cancel()
    return main_task if main_task in pending else None


class ExitMixin(object):
    _exit_event: asyncio.Event

    async def _either_or_exit(self, awaitable: Awaitable) -> Optional[Task]:
        """
        Wait for either the given awaitable or for this to exit. If the exit happens first, return
        the pending task.

        :param awaitable:
        :return: the pending task if exited early or None if it completed
        """
        return await either_or_interrupt(awaitable, interrupts=[self._exit_event.wait()])

    @property
    def _exited(self) -> bool:
        return self._exit_event.is_set()


async def build_docker_image(
        image_name: str,
        version: str,
        build_args: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build a Docker image from a context in the images/ directory.

    Tags the image with the version.

    :param image_name: name of the image in the images/ directory
    :param version: a version string
    :param build_args: a mapping of build args
    :return: the Docker image ID
    """
    image_tag = f"validator-supervisor/{image_name}:{version}"
    context_dir = resource_filename('validator_supervisor', f"images/{image_name}")
    LOG.debug(f"Building Docker image {image_tag}...")

    build_cmd = ['docker', 'build', '--pull']
    if build_args:
        for key, val in build_args.items():
            build_cmd.extend(['--build-arg', f"{key}={val}"])
    build_cmd.extend(['-t', image_tag, context_dir, '--quiet'])
    build_proc = await asyncio.create_subprocess_exec(*build_cmd, stdout=PIPE, stderr=PIPE)

    image_id_encoded, err_encoded = await build_proc.communicate()
    if build_proc.returncode != 0:
        raise DockerBuildException(
            f"docker build for {image_name} failed with exit code {build_proc.returncode}",
            err_encoded,
        )

    image_id = image_id_encoded.decode().strip()
    LOG.debug(f"Built Docker image {image_tag}: {image_id}")
    return image_id


def set_sighup_on_parent_exit():
    """
    Use prctl to deliver SIGHUP to this process when the parent process exits.

    This is intended to be run as the preexec_fn when spawning a subprocess.

    See http://linux.die.net/man/2/prctl
    """
    prctl.set_pdeathsig(signal.SIGHUP)
