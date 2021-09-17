"""Ethereum 2.0 validator implementation runners."""

from typing import List

from .base import BeaconNodePortMap, ValidatorRelease, ValidatorRunner, ValidatorReleaseSchema
from .lighthouse import LighthouseValidator
from .prysm import PrysmValidator
from ..exceptions import BadValidatorRelease, DockerBuildException


_VALIDATOR_CLASSES = {
    'lighthouse': LighthouseValidator,
    'prysm': PrysmValidator,
}


async def create_validator_for_release(
        release: ValidatorRelease,
        eth2_network: str,
        datadir: str,
        out_log_filepath: str,
        err_log_filepath: str,
        beacon_node_ports: List[BeaconNodePortMap],
) -> ValidatorRunner:
    """
    Factory for creating a ValidatorRunner based on the release.

    :param release: the validator release spec
    :param eth2_network: the Ethereum 2.0 network name
    :param datadir:
    :param out_log_filepath:
    :param err_log_filepath:
    :param beacon_node_ports: list of port maps for remote public beacon nodes
    :return: a validator
    :raise BadValidatorRelease: if validator could not be created from release
    """
    try:
        cls = _VALIDATOR_CLASSES[release.impl_name]
    except KeyError:
        raise BadValidatorRelease(f"invalid implementation name: {release.impl_name}")

    validator = cls(
        eth2_network,
        datadir,
        out_log_filepath,
        err_log_filepath,
        beacon_node_ports,
        release,
    )
    try:
        await validator.build_docker_image()
    except DockerBuildException as err:
        raise BadValidatorRelease("build failure") from err
    return validator
