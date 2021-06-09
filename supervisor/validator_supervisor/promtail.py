"""
Promtail agent subprocess.
"""

import asyncio
from asyncio.subprocess import Process
import logging
import os
import re
from typing import Dict, IO, Optional
import yaml

from .subprocess import SimpleSubprocess

LOG = logging.getLogger(__name__)


class Promtail(SimpleSubprocess):
    """
    Promtail agent (https://grafana.com/docs/loki/latest/clients/promtail/) subprocess which
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
        self.dirpath = os.path.join(base_dir, f"promtail-{self.node_sanitized}")
        os.makedirs(self.dirpath, exist_ok=True)
        out_log_path = os.path.join(self.dirpath, 'out.log')
        err_log_path = os.path.join(self.dirpath, 'err.log')
        super().__init__(out_log_path, err_log_path)

    def _generate_config(self) -> str:
        config_path = os.path.join(self.dirpath, 'promtail.yaml')

        config = {
            'server': {'disable': True},
            'client': {'url': f"http://localhost:{self.local_port}/loki/api/v1/push"},
            'positions': {'filename': '/tmp/positions/positions.yaml'},
            'scrape_configs': [
                {
                    'job_name': 'validator',
                    'static_configs': [
                        {
                            'labels': {
                                'process': process_name,
                                '__path__': f"/var/log/validator-supervisor/{process_name}.log",
                            },
                        }
                        for process_name, path in self.log_paths.items()
                    ],
                }
            ],
        }
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        return config_path

    async def _launch(
            self,
            out_log_file: Optional[IO[str]],
            err_log_file: Optional[IO[str]],
    ) -> Process:
        config_path = self._generate_config()

        positions_volume_name = f"validator-supervisor_promtail_{self.node_sanitized}"
        cmd = [
            'docker', 'run', '--rm',
            '--name', f"validator-supervisor_{os.getpid()}_promtail",
            '--pull', 'always',
            '--net', 'host',
            '--volume', f"{os.path.abspath(config_path)}:/etc/promtail/config.yml",
            '--volume', f"{positions_volume_name}:/tmp/positions",
        ]
        for process_name, path in self.log_paths.items():
            cmd.extend([
                '--volume',
                f"{os.path.abspath(path)}:/var/log/validator-supervisor/{process_name}.log",
            ])
        cmd.append('grafana/promtail')

        return await asyncio.create_subprocess_exec(*cmd, stdout=out_log_file, stderr=err_log_file)
