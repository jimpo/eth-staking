#!/bin/bash

network_flag="--goerli"
if [[ "$MAINNET" -eq 1 ]] ; then
    network_flag=""
fi

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
