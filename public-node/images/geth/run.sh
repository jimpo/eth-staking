#!/bin/bash

case "$ETH2_NETWORK" in
    mainnet)
        network_flag=""
        ;;

    pyrmont | prater)
        network_flag="--goerli"
        ;;

    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
esac

exec geth \
     --http \
     --http.addr 0.0.0.0 \
     --http.api eth,net \
     --http.vhosts '*' \
     --metrics \
     --pprof \
     --pprof.addr 0.0.0.0 \
     $network_flag \
     $@
