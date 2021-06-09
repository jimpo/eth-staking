# The validator supervisor

The validator supervisor runs on the validator host machine and manages and

- opens SSH tunnels to the public bastion nodes, restarting the connections if they exit
- runs and supervises the validator process, restarting it if it exits unexpectedly
- runs an RPC service, accessible through a Unix domain socket or SSH reverse tunnel from bastion
- uploads local logs to the Loki log servers on the public nodes
- generates encrypted backups of validator state with latest slashing protection information and uploads to the public nodes

See Python module documentation for the `validator_supervisor.supervisor` module for more information.

The package also includes an executable subcommand for remotely controlling the running validator
supervisor through its RPC interface. The control command opens a shell interface.

## Running and deployment

How you decide to get this running on your validator hardware is up to you, but here are some ideas and suggestions.

To build the Python package, run

```bash
pip install build
pipenv run python -m build
```

To install the Python packages directly, run

```bash
pip install .
```

To generate or update a configuration file, use the `setup` subcommand.

```bash
python -m validator_supervisor setup [...options...]
```

On an Ubuntu host, I put the configuration files in `/usr/local/share/validator-supervisor`, set the data and log directories in the config to `/var/lib/validator-supervisor` and `/var/log/validator-supervisor` respectively.

You should not have swap on, as this uses a tmpfs for sensitive files that we want to keep only in RAM. Also, you should probably have disk encryption enabled with `dm-crypt` or at least something for filesystem integrity like `dm-integrity`.

Use `openssl` to generate a self-signed SSL certificate. For example,

```bash
openssl req -x509 -newkey ed25519 -nodes -keyout ssl_key.em -out ssl_cert.pem
```

And who watches the watcher? You may want to make a systemd service for the validator supervisor that restarts it if it ever crashes.

To run the supervisor on the validator host, use the `daemon` subcommand.

```bash
python -m validator_supervisor setup [...options...]
```

And to run the remote control shell, use the `control` subcommand.

```bash
python -m validator_supervisor control [...options...]
```

## Development

The project uses [Pipenv](https://pipenv.pypa.io/en/latest/) for development,

```bash
pip install pipenv
pipenv install
```

[mypy](http://mypy-lang.org/) for static type checking,

```bash
pipenv run mypy
```

and [unittest](https://docs.python.org/3/library/unittest.html) for testing.

```bash
pipenv run python -m unittest
```

Before running certain tests, you should run the test service dependencies with `docker-compose`.

```bash
docker-compose -f docker-compose.test-deps.yml up
```

## Design choices

#### Why Python?

This feels like a devops project, and devops code feels like it should be in Python. And fuck Go.
