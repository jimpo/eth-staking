#!/bin/bash

network_flag="--pyrmont"
if [[ "$MAINNET" -eq 1 ]] ; then
    network_flag="--mainnet"
fi

exec beacon-chain --accept-terms-of-use \
     $network_flag \
     --rpc-host 0.0.0.0 \
     --monitoring-host 0.0.0.0 \
     --http-web3provider http://$ETH1_HOST:8545 \
     $@
