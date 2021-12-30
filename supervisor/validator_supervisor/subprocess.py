"""
Interfaces and logic for running supervised, concurrent subprocesses.

Supervised subprocesses are restarted automatically when they exit unexpectedly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from asyncio import FIRST_EXCEPTION
from asyncio.subprocess import Process
import logging
import os.path
import time
from typing import Awaitable, IO, List, Optional, Tuple

from .util import either_or_interrupt, set_sighup_on_parent_exit

LOG = logging.getLogger(__name__)
FIRST_GRACE_PERIOD = 2
FINAL_GRACE_PERIOD = 10


class AlreadyRunningException(Exception):
    pass


class Subprocess(ABC):
    """
    Interface for a concurrent subprocess.

    Implementations should be able to restart after being stopped (and watching for exit).
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Start the subprocess.

        Expected to exit after the subprocess is successfully launched or fails to.
        """
        pass

    @abstractmethod
    async def watch(self) -> None:
        """
        Watch the subprocess execution and return when it exits.

        If the subprocess is stopped, watch is also responsible for terminating and cleaning up
        the subprocess.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Signal for the process to be stopped asynchronously.

        The caller should watch the subprocess after calling stop to wait for exit and cleanup.

        :return:
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Return whether the subprocess is running."""
        pass

    def health_check(self) -> Optional[HealthCheck]:
        """Return a health check."""
        return None


class SimpleSubprocess(Subprocess, ABC):
    def __init__(
            self,
            out_log_filepath: Optional[str] = None,
            err_log_filepath: Optional[str] = None,
    ):
        self.out_log_filepath = out_log_filepath
        self.err_log_filepath = err_log_filepath
        self._out_log_file: Optional[IO[str]] = None
        self._err_log_file: Optional[IO[str]] = None
        self._proc: Optional[Process] = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self.is_running():
            raise AlreadyRunningException()

        if self.out_log_filepath is not None:
            self._out_log_file = open(self.out_log_filepath, 'a')
        if self.err_log_filepath is not None:
            if self._out_and_err_logs_aliased():
                self._err_log_file = self._out_log_file
            else:
                self._err_log_file = open(self.err_log_filepath, 'a')
        self._stop = asyncio.Event()
        self._proc = await self._launch(self._out_log_file, self._err_log_file)

    async def watch(self) -> None:
        if self._proc is not None:
            proc_wait_task = await either_or_interrupt(self._proc.wait(), [self._stop.wait()])
            if proc_wait_task is not None:
                await self._robust_terminate(self._proc, proc_wait_task)

            await self._cleanup(self._proc, self._stop.is_set())
            self._proc = None

        if self._out_log_file:
            self._out_log_file.close()
            self._out_log_file = None

        if self._err_log_file:
            if not self._out_and_err_logs_aliased():
                self._err_log_file.close()
            self._err_log_file = None

    async def _robust_terminate(self, proc: Process, proc_wait_task: asyncio.Task):
        try:
            await self._request_terminate(proc)
        except ProcessLookupError:
            pass

        pending_proc_task = await either_or_interrupt(
            proc_wait_task,
            interrupts=[asyncio.sleep(FIRST_GRACE_PERIOD)],
        )
        if pending_proc_task is None:
            return

        LOG.warning(f"Did not terminate within {FIRST_GRACE_PERIOD} seconds, retrying SIGTERM")
        try:
            proc.terminate()
        except ProcessLookupError:
            pass

        pending_proc_task = await either_or_interrupt(
            proc_wait_task,
            interrupts=[asyncio.sleep(FINAL_GRACE_PERIOD)],
        )
        if pending_proc_task is None:
            return

        LOG.warning(
            f"Did not terminate after another {FINAL_GRACE_PERIOD} seconds, sending SIGKILL"
        )
        try:
            proc.kill()
        except ProcessLookupError:
            LOG.error(f"proc_wait_task did not complete, but subprocess {proc.pid} is not found")
            return

        await proc_wait_task

    async def _request_terminate(self, proc: Process):
        proc.terminate()

    def stop(self) -> None:
        if self._proc is None:
            return

        # Both set the stop event and send terminate signal. The stop event signals to the watch
        # coroutine to begin the stop sequence. Send the terminate signal here as well because we
        # still want the process to terminate even if watch hasn't been called yet.
        self._stop.set()
        try:
            self._proc.terminate()
        except ProcessLookupError:
            pass

    def health_check(self) -> Optional[HealthCheck]:
        return None

    def is_running(self) -> bool:
        return self._proc is not None

    def get_pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

    @abstractmethod
    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Optional[Process]:
        pass

    async def _cleanup(self, proc: Process, _stopped: bool) -> None:
        pass

    def _out_and_err_logs_aliased(self) -> bool:
        return self.out_log_filepath is not None and \
               self.err_log_filepath is not None and \
               os.path.realpath(self.out_log_filepath) == os.path.realpath(self.err_log_filepath)


class HealthCheck(ABC):
    def __init__(self, interval: float, retries: int):
        self.interval = interval
        self.retries = retries

    @abstractmethod
    async def is_ok(self) -> bool:
        pass

    async def monitor(self) -> None:
        failures = 0
        while failures <= self.retries:
            await asyncio.sleep(self.interval)
            if await self.is_ok():
                failures = 0
            else:
                failures += 1
                LOG.debug(f"Health check failure ({failures}/{self.retries + 1})")


async def _watch_subproc(name: str, subproc: Subprocess, stop_event: asyncio.Event) -> None:
    health_check = subproc.health_check()
    health_check_task = asyncio.create_task(health_check.monitor()) if health_check else None
    interrupts: List[Awaitable] = [stop_event.wait()]
    if health_check_task is not None:
        interrupts.append(health_check_task)
    subproc_task = await either_or_interrupt(subproc.watch(), interrupts)

    if subproc_task is not None:
        if health_check_task is not None and health_check_task.done():
            err = health_check_task.exception()
            if err:
                LOG.error(f"Exception in {name} health check", exc_info=err)
            LOG.info(f"Stopping {name} due to failing health checks")
        subproc.stop()
        await subproc_task


async def _supervise(
        name: str,
        subproc: Subprocess,
        retry_delay: int,
        stop_event: asyncio.Event,
) -> None:
    while True:
        started_at = time.time()
        await _watch_subproc(name, subproc, stop_event)
        LOG.info(f"Supervised process {name} exited")
        elapsed = time.time() - started_at

        if not stop_event.is_set() and elapsed < retry_delay:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=retry_delay - elapsed)
            except asyncio.TimeoutError:
                pass

        if stop_event.is_set():
            break

        try:
            await subproc.start()
            LOG.info(f"Started supervised process {name}")
        except Exception as err:
            LOG.error(f"Error starting supervised process {name}: {err}")


async def start_supervised(
        name: str,
        subproc: Subprocess,
        retry_delay: int,
        stop_event: asyncio.Event,
) -> asyncio.Task:
    await subproc.start()
    LOG.info(f"Started supervised process {name}")
    return asyncio.create_task(_supervise(name, subproc, retry_delay, stop_event), name=name)


async def start_supervised_multi(
        subprocs: List[Tuple[str, Subprocess]],
        retry_delay: int,
        stop_event: asyncio.Event,
) -> List[asyncio.Task]:
    if not subprocs:
        return []

    tasks_done, _ = await asyncio.wait(
        [start_supervised(name, subproc, retry_delay, stop_event) for name, subproc in subprocs],
        return_when=FIRST_EXCEPTION
    )
    return [task.result() for task in tasks_done]
