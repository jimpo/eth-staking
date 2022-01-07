#!/bin/bash

set -e

set_network_flags() {
    network_flags="--$ETH2_NETWORK"
    if [[ -n "$genesis_state_sha256" ]] ; then
        genesis_state_path="${ETH2_NETWORK}_genesis_state.ssz"
        curl -sSL -o $genesis_state_path \
             https://github.com/eth-clients/eth2-networks/blob/master/shared/$ETH2_NETWORK/genesis.ssz\?raw\=true
        echo "$genesis_state_sha256  $genesis_state_path" | sha256sum -c
        network_flags="$network_flags --genesis-state=$genesis_state_path"
    fi
}

case "$ETH2_NETWORK" in
    mainnet)
        # For mainnet, genesis state is built into the binary, so no need to download it
        ;;
    prymont)
        genesis_state_sha256="0f4ab1dec2065c3f545fcd3c6c512ab693aa2057680f41b4906c8179aa0170c6"
        ;;
    prater)
        genesis_state_sha256="23daa70a970034444da4dc04abfab7b7dd08adaadefb1f9764ac56ea58b2086e"
        ;;
    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
        ;;
esac

set_network_flags
exec beacon-chain --accept-terms-of-use \
     $network_flags \
     --rpc-host 0.0.0.0 \
     --grpc-gateway-host 0.0.0.0 \
     --monitoring-host 0.0.0.0 \
     --http-web3provider http://$ETH1_HOST:8545 \
     $@
