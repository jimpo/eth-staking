"""
Grafana Alloy agent subprocess.
"""

import asyncio
from asyncio.subprocess import Process
import logging
import os
import re
from typing import Dict, IO, Optional

from .subprocess import SimpleSubprocess
from .util import set_sighup_on_parent_exit

LOG = logging.getLogger(__name__)


def _generate_alloy_config(log_paths: Dict[str, str], local_port: int) -> str:
    targets = []
    for process_name in log_paths:
        targets.append(
            f'    {{__path__ = "/var/log/validator-supervisor/{process_name}.log",'
            f' process = "{process_name}"}}'
        )
    targets_str = ",\n".join(targets)

    return f"""\
loki.source.file "logs" {{
  targets = [
{targets_str},
  ]
  forward_to = [loki.write.default.receiver]
}}

loki.write "default" {{
  endpoint {{
    url = "http://localhost:{local_port}/loki/api/v1/push"
  }}
}}
"""


class Alloy(SimpleSubprocess):
    """
    Grafana Alloy agent (https://grafana.com/docs/alloy/) subprocess which
    uploads local logs to the remote nodes' Loki servers.

    Implements the Subprocess interface. Runs in a Docker container.

    Currently only uploads the validator supervisor process log and the validator subprocess log.
    Maybe we'll want to upload more eventually.
    """
    def __init__(
            self,
            node: str,
            local_port: int,
            base_dir: str,
            log_paths: Dict[str, str],
    ):
        self.node = node
        self.node_sanitized = re.sub(r"[^a-zA-Z0-9_\-]", '_', node)
        self.local_port = local_port
        self.log_paths = log_paths
        self.dirpath = os.path.join(base_dir, f"alloy-{self.node_sanitized}")
        os.makedirs(self.dirpath, exist_ok=True)
        out_log_path = os.path.join(self.dirpath, 'out.log')
        err_log_path = os.path.join(self.dirpath, 'err.log')
        super().__init__(out_log_path, err_log_path)

    def _generate_config(self) -> str:
        config_path = os.path.join(self.dirpath, 'config.alloy')
        with open(config_path, 'w') as f:
            f.write(_generate_alloy_config(self.log_paths, self.local_port))
        return config_path

    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Process:
        config_path = self._generate_config()

        volume_name = f"validator-supervisor_alloy_{self.node_sanitized}"
        cmd = [
            'docker', 'run', '--rm',
            '--name', f"validator-supervisor_{os.getpid()}_alloy_{self.node_sanitized}",
            '--pull', 'always',
            '--net', 'host',
            '--volume', f"{os.path.abspath(config_path)}:/etc/alloy/config.alloy",
            '--volume', f"{volume_name}:/tmp/alloy-data",
        ]
        for process_name, path in self.log_paths.items():
            # Ensure file exists as a regular file or else Docker will create a directory at that
            # path and fuck things up
            if not os.path.exists(path):
                with open(path, 'a') as _:
                    pass
            cmd.extend([
                '--volume',
                f"{os.path.abspath(path)}:/var/log/validator-supervisor/{process_name}.log",
            ])
        cmd.extend([
            'grafana/alloy:latest',
            'run',
            '--storage.path=/tmp/alloy-data',
            '/etc/alloy/config.alloy',
        ])

        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=out_log_file,
            stderr=err_log_file,
            preexec_fn=set_sighup_on_parent_exit,
        )
