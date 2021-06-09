# The public node

These servers are meant to be run redundantly on multiple different cloud infrastructure providers, chosen so that I think at least one will be operational at all times. The node runs the following services

- [go-ethereum](https://github.com/ethereum/go-ethereum), an Ethereum 1.0 network node
- [Lighthouse](https://github.com/sigp/lighthouse), an Ethereum 2.0 beacon chain node
- [Prysm](https://github.com/prysmaticlabs/prysm), an Ethereum 2.0 beacon chain node
- [Prometheus](https://prometheus.io/), a metrics collection and monitoring system
- [Loki](https://grafana.com/oss/loki/), a log aggregation system
- [Grafana](https://grafana.com/grafana/), for visualizing, exploring, and alerting on metrics and logs
- An SSH bastion server for securely accessing private services like the Ethereum RPC interfaces and Grafana

These services are all run in [Docker](https://www.docker.com/products/container-runtime) containers on an [Ubuntu](https://ubuntu.com/) host OS.

## Configuration

Private configuration for different deployments are put in the deployments directory by name. For example, I have directories `mainnet` and `testnet` in my `deployments` directory. Each deployment directory should contain the following files:

- `network-name`: a file containing the Ethereum 2.0 network name, currently either `mainnet` or `pyrmont`
- `authorized_keys`: the SSH `authorized_keys` file for the bastion service
- `validator-pubkeys.txt`: a list of your validators' public keys, one per line

## Deployment

To keep deployment simple and generalized, this targets an Ubuntu host OS and server initialization and updates are done with a single shell script, which is run with root privileges. These scripts are self-decompressing and themselves contain an archive of all data files. Some Docker images are built on the host, not pulled down from a remote registry.

### Build deploy scripts

For each deployment, running the build generates two scripts called `init.sh` and `update.sh` in the directory `generated/{deployment_name}/`. The script `init.sh` is only to be run once on a new Ubuntu 20.04 server and the script `update.sh` is run each time afterward to update the system and in case any of the local images or configuration changes. These must be executed with root privileges on the remote node.

The scripts are built with [doit](https://pydoit.org/). To install, run

```bash
python3 -m pip install doit
```

and to build, run

```bash
python3 -m doit
```
