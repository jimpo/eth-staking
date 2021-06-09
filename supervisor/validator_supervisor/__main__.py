import asyncio
import functools
import logging
import logging.config
import os
import signal
import sys
from typing import Union
import yaml

from .cli import Subcommand, parse_cli_args
from .config import Config, SSHConnInfo, read_config, read_root_key, write_root_key
from .control_shell import ControlShell
from .exceptions import UnlockRequired
from .setup import perform_setup
from .ssh import UnixSocket
from .supervisor import ValidatorSupervisor

LOG = logging.getLogger(__name__)

ROOT_KEY_FILENAME = 'supervisor-key.hex'


async def run_daemon(config: Config, args):
    exit_event = asyncio.Event()

    root_key = None
    root_key_path = os.path.join(config.data_dir, ROOT_KEY_FILENAME)
    try:
        root_key = read_root_key(config.key_desc, root_key_path)
    except UnlockRequired:
        LOG.info("Waiting for supervisor unlock...")

    supervisor = ValidatorSupervisor(
        config=config,
        root_key=root_key,
        enable_promtail=not args.disable_promtail,
        exit_event=exit_event,
    )

    def exit_handler(signame: str):
        LOG.debug(f"Handling signal {signame}")
        exit_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, functools.partial(exit_handler, 'SIGINT'))
    loop.add_signal_handler(signal.SIGTERM, functools.partial(exit_handler, 'SIGTERM'))

    await supervisor.run()

    # If supervisor was dynamically unlocked, write the root key for next time.
    if root_key is None and supervisor.root_key is not None:
        write_root_key(supervisor.root_key, root_key_path)


def run_control(args) -> None:
    logging.basicConfig(stream=sys.stdout)

    endpoint: Union[UnixSocket, SSHConnInfo]
    if args.rpc_socket_path:
        endpoint = UnixSocket(args.rpc_socket_path)
    elif args.bastion_host:
        endpoint = SSHConnInfo(
            host=args.bastion_host,
            port=args.bastion_port,
            user=args.bastion_user,
            identity_file=args.bastion_ssh_identity_file,
            pubkey=None,
        )
    else:
        sys.stderr.write("Must provide either --rpc-socket-path or --bastion-host")
        sys.exit(1)

    controller = ControlShell(endpoint, args.ssl_cert, args.auth_user, args.auth_key)
    controller.cmdloop()


def configure_logging(logging_config_path: str) -> None:
    with open(logging_config_path, 'r') as f:
        logging_config = yaml.load(f, Loader=yaml.Loader)
    logging.config.dictConfig(logging_config)


def main() -> None:
    args = parse_cli_args()

    if args.subcommand_name == Subcommand.SETUP.value:
        perform_setup(args.config_path)

    if args.subcommand_name == Subcommand.DAEMON.value:
        configure_logging(args.logging_config_path)
        config = read_config(args.config_path)
        logging.root.addHandler(logging.FileHandler(config.supervisor_log_path))
        asyncio.run(run_daemon(config, args))

    if args.subcommand_name == Subcommand.CONTROL.value:
        run_control(args)


if __name__ == '__main__':
    main()
