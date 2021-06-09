"""
Command line interface specification.
"""

import argparse
from enum import Enum

from .config import DEFAULT_BASTION_SSH_USER


class Subcommand(Enum):
    SETUP = 'setup'
    DAEMON = 'daemon'
    CONTROL = 'control'


def parse_cli_args():
    parser = argparse.ArgumentParser(description='Manage Eth 2.0 validator')
    subparsers = parser.add_subparsers(
        dest='subcommand_name',
        required=True,
    )
    setup_parser = subparsers.add_parser(
        Subcommand.SETUP.value,
        help='perform initial supervisor setup',
    )
    daemon_parser = subparsers.add_parser(
        Subcommand.DAEMON.value,
        help='run supervisor locally on the validator host',
    )
    control_parser = subparsers.add_parser(
        Subcommand.CONTROL.value,
        help='remote controller communicating with validator supervisor',
    )

    for subparser in (setup_parser, daemon_parser):
        subparser.add_argument('--config-path', required=True,
                               help='Path to the YAML configuration file')

    daemon_parser.add_argument('--logging-config-path', required=True,
                               help='Path to the YAML logging configuration file')
    daemon_parser.add_argument('--disable-promtail', action='store_true',
                               help='Disable upload of local logs to remote Loki server with Promtail')

    control_parser.add_argument('--rpc-socket-path',
                                help='Path to local UNIX domain socket for the daemon')
    control_parser.add_argument('--auth-user', help="User name for control authentication")
    control_parser.add_argument('--auth-key', help="User key for control authentication")
    control_parser.add_argument('--bastion-host',
                                help='Host address for remote bastion to validator')
    control_parser.add_argument('--bastion-port', type=int, default=2222,
                                help='SSH port for bastion')
    control_parser.add_argument('--bastion-user', default=DEFAULT_BASTION_SSH_USER,
                                help='SSH user for bastion')
    control_parser.add_argument('--bastion-ssh-identity-file',
                                help='Path to SSH identity file for bastion')
    control_parser.add_argument('--ssl-cert',
                                help='Path to SSL certificate for validator RPC auth')

    return parser.parse_args()
