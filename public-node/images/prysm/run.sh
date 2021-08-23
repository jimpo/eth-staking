#!/bin/bash

case "$ETH2_NETWORK" in
    mainnet | pyrmont | prater)
        network_flag="--$ETH2_NETWORK"
        ;;

    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
        ;;
esac

exec beacon-chain --accept-terms-of-use \
     $network_flag \
     --rpc-host 0.0.0.0 \
     --monitoring-host 0.0.0.0 \
     --http-web3provider http://$ETH1_HOST:8545 \
     $@
