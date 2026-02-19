# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ethereum 2.0 validator staking infrastructure with three main components:
- **Public nodes** (`public-node/`): Redundant remote servers running consensus/execution clients (Lighthouse/Reth) with monitoring (Prometheus/Grafana/Loki). Act as SSH bastions.
- **Validator supervisor** (`supervisor/`): Python daemon running on isolated physical hardware that manages validator lifecycle, SSH tunnels, encrypted backups, and an RPC control interface.
- **Remote control client**: Shell interface connecting through SSH tunnels to the supervisor RPC.

## Build & Development Commands

### Supervisor (Python, in `supervisor/`)

```bash
# Install dependencies (uses uv, not pip/pipenv)
uv sync

# Run all tests (unit + integration)
uv run python -m unittest discover -s src

# Run a single test file
uv run python -m unittest src/validator_supervisor/test_backup_archive.py

# Run a single test case
uv run python -m unittest src.validator_supervisor.test_backup_archive.BackupArchiveTest.test_create_and_read

# Type checking
uv run mypy

# Start test dependency services (needed for integration tests)
docker compose -f docker-compose.test-deps.yml up

# Build package
uv build
```

### Public Node (in `public-node/`)

```bash
# Generate deployment scripts (uses doit build system)
doit

# Output goes to generated/{deployment_name}/{init,update}.sh
```

## Architecture

### Supervisor Core (`supervisor/src/validator_supervisor/`)

- **`supervisor.py`** — `ValidatorSupervisor`: Central orchestrator. Manages SSH tunnels to public nodes, supervises validator Docker container, handles encrypted backups, runs RPC server, and manages Promtail log shipping. Allocates ports dynamically from a configured range.
- **`config.py`** — Configuration schema using marshmallow for validation/deserialization of YAML config files.
- **`cli.py`** / **`__main__.py`** — CLI entry points: `daemon`, `control`, `setup` subcommands.
- **`subprocess.py`** — Supervised process execution with automatic restarts, health checks, and graceful shutdown via signal handling.

### Cryptography & Key Management

- **`key_ops.py`** — Root key derivation (Argon2id), key checksum (Blake2b), backup key derivation. Root key is 16 bytes, kept in RAM.
- **`backup_archive.py`** — Encrypted tar.xz archives using libsodium SecretBox (XChaCha20-Poly1305). Contains slashing protection DB (EIP-3076), keystores (EIP-2335), and passwords.
- **`eip2335.py`** — EIP-2335 keystore encrypt/decrypt support.

### Validator Implementations (`validators/`)

Pluggable validator runners with a common base class (`ValidatorRunner`). Implementations for Lighthouse and Prysm. All run in Docker containers.

### RPC (`rpc/`)

Custom JSON-RPC 2.0 over Unix socket or SSH tunnel. Challenge-response authentication using NaCl public key crypto. Operations: validate, pause, exit, get status, etc.

### SSH (`ssh.py`)

Custom `SSHClient` managing connections with port forwarding, reverse tunnels, Unix socket support, and pinned host keys.

## Key Design Constraints

- **Slashing prevention is paramount**: Validator state (slashing protection DB) must be carefully managed during backup/restore. Never run two validators with the same keys simultaneously.
- **Validator keys never leave the isolated host**: Public nodes have no access to signing keys.
- **SSH tunnels for all communication**: Beacon node RPC reaches the validator host through SSH tunnels; control RPC reaches the supervisor through reverse SSH tunnels.

## Tech Stack

- **Python 3.10+** with asyncio (async/await throughout)
- **uv** for dependency management and builds
- **Docker** for all service containers
- **doit** for public node deployment script generation
- **Libraries**: aiohttp (async HTTP), marshmallow (schemas), PyNaCl/libsodium (crypto), PyYAML, python-prctl
