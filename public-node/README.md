# The public node

These servers are meant to be run redundantly on multiple different cloud infrastructure providers, chosen so that I think at least one will be operational at all times. The node runs the following services

- [go-ethereum](https://github.com/ethereum/go-ethereum), an Ethereum 1.0 network node
- [Lighthouse](https://github.com/sigp/lighthouse), an Ethereum 2.0 beacon chain node
- [Prysm](https://github.com/prysmaticlabs/prysm), an Ethereum 2.0 beacon chain node
- [Prometheus](https://prometheus.io/), a metrics collection and monitoring system
- [Loki](https://grafana.com/oss/loki/), a log aggregation system
- [Grafana](https://grafana.com/grafana/), for visualizing, exploring, and alerting on metrics and logs
- [mev-boost](https://github.com/flashbots/mev-boost), a service for outsourcing block building to the Flashbots marketplace
- An SSH bastion server for securely accessing private services like the Ethereum RPC interfaces and Grafana

These services are all run in [Docker](https://www.docker.com/products/container-runtime) containers on an [Ubuntu](https://ubuntu.com/) host OS.

## Configuration

Private configuration for different deployments are put in the deployments directory by name. For example, I have directories `mainnet` and `testnet` in my `deployments` directory. Each deployment directory should contain the following files:

- `network-name`: a file containing the Ethereum 2.0 network name, currently either `mainnet` or `pyrmont`
- `authorized_keys`: the SSH `authorized_keys` file for the bastion service
- `validator-pubkeys.txt`: a list of your validators' public keys, one per line

### FIDO/U2F-enabled MFA

For FIDO/U2F-enabled MFA, generate an `ed25519-sk` or `ecdsa-sk` type SSH keypair, which is [natively supported](https://www.openssh.com/txt/release-8.2) by OpenSSH >= 8.2 and is so, so dope.

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

## Grafana setup

The Grafana setup is left as a mostly manual process for now. The Grafana server is not published on a host port, so it must be accessed through an SSH tunnel to the bastion

```bash
ssh -p 2222 -L 3000:grafana:3000 somebody@<HOSTNAME>
```

### Set up datasources

On the left side bar, Configuration > Data Sources. Click "Add data source" button. Add Loki with URL `http://loki:3100`. Repeat and add Prometheus with URL `http://prometheus:9090`.

### Set up dashboards

For the Lighthouse node, see the official Lighthouse metrics repo: https://github.com/sigp/lighthouse-metrics/tree/master/dashboards.

For the Prysm node, see https://docs.prylabs.network/docs/prysm-usage/monitoring/grafana-dashboard/#creating-and-importing-dashboards.

### Set up alerting

See https://grafana.com/docs/grafana/latest/alerting/.
