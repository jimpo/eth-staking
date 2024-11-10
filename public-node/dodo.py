import base64
from enum import Enum
import functools
import glob
import io
import os
import tarfile
import textwrap
from typing import Generator
import yaml

CONFIG_FILEPATHS = \
    ['install.sh', 'docker-services.service', 'docker-daemon.json'] + glob.glob('images/*/*')
DEPLOYMENT_CONFIG_FILEPATHS = \
    ['network-name', 'authorized_keys', 'validator-pubkeys.txt', 'validator-indices.txt']

class Eth2Network(Enum):
    MAINNET = "mainnet"
    GOERLI  = "goerli"
    PYRMONT = "pyrmont"


def generate_docker_compose_file(deployment: str):
    network = _read_network(deployment)
    with open('docker-compose.yml', 'r') as f:
        spec = yaml.load(f, Loader=yaml.Loader)

    for service in ('reth', 'lighthouse', 'prysm', 'mev-boost'):
        if service not in spec['services']:
            continue
        if 'environment' not in spec['services'][service]:
            spec['services'][service]['environment'] = {}
        spec['services'][service]['environment']['ETH2_NETWORK'] = network.value

    os.makedirs(f"generated/{deployment}", exist_ok=True)
    with open(f"generated/{deployment}/docker-compose.yml", 'w') as f:
        yaml.dump(spec, f)


def generate_install_script(action: str, deployment: str):
    if action not in {'init', 'update'}:
        raise ValueError("action must be one of: init, update")

    outdir = f"generated/{deployment}"
    archive_content = io.BytesIO()
    with tarfile.open(fileobj=archive_content, mode='w:xz') as tar:
        for path in CONFIG_FILEPATHS:
            tar.add(path)
        for path in DEPLOYMENT_CONFIG_FILEPATHS:
            tar.add(os.path.join('deployments', deployment, path), path)
        tar.add(os.path.join(outdir, 'docker-compose.yml'), 'docker-compose.yml')

    archive_content_b64 = base64.b64encode(archive_content.getvalue()).decode('ascii')
    script_path = f"{outdir}/{action}.sh"
    with open(script_path, 'w') as f:
        f.write(textwrap.dedent(f"""\
            #!/bin/sh
            ARCHIVE_CONTENT="{archive_content_b64}"
            tmp_dir=$(mktemp --directory)
            cd $tmp_dir
            echo -n "$ARCHIVE_CONTENT" | base64 -d | tar -Jx
            ./install.sh {action}
            exitcode=$?
            cd /
            rm -rf $tmp_dir
            exit $exitcode
        """))
    os.chmod(script_path, 0o755)


def task_docker_compose_file():
    """Generate deployment-customized docker-compose.yml files."""
    for deployment in _deployments():
        yield {
            'name': deployment,
            'targets': [f"generated/{deployment}/docker-compose.yml"],
            'file_dep': (
                ['docker-compose.yml'] +
                [f"deployments/{deployment}/{path}" for path in DEPLOYMENT_CONFIG_FILEPATHS]
            ),
            'actions': [functools.partial(generate_docker_compose_file, deployment)],
        }


def task_scripts():
    """Generate init scripts."""
    for deployment in _deployments():
        yield {
            'name': deployment,
            'targets': [f"generated/{deployment}/init.sh"],
            'file_dep': (
                CONFIG_FILEPATHS +
                [f"deployments/{deployment}/{path}" for path in DEPLOYMENT_CONFIG_FILEPATHS] +
                [f"generated/{deployment}/docker-compose.yml"]
            ),
            'actions': [functools.partial(generate_install_script, 'init', deployment)],
        }


def task_update_script():
    """Generate update scripts."""
    for deployment in _deployments():
        yield {
            'name': deployment,
            'targets': [f"generated/{deployment}/update.sh"],
            'file_dep': (
                CONFIG_FILEPATHS +
                [f"deployments/{deployment}/{path}" for path in DEPLOYMENT_CONFIG_FILEPATHS] +
                [f"generated/{deployment}/docker-compose.yml"]
            ),
            'actions': [functools.partial(generate_install_script, 'update', deployment)],
        }


def _deployments() -> Generator[None, None, str]:
    for deployment in os.listdir('deployments'):
        deployment_path = os.path.join('deployments', deployment)
        if os.path.isdir(deployment_path):
            yield deployment

def _read_network(deployment: str) -> Eth2Network:
    with open(f"deployments/{deployment}/network-name", 'r') as f:
        network_name = f.read().strip()
    return Eth2Network(network_name)
