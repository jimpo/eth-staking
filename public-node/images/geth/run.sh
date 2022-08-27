#!/bin/bash

authrpc_jwtsecret_path="authrpc-secret/jwtsecret"

case "$ETH2_NETWORK" in
    mainnet)
        network_flag=""
        ;;

    goerli)
        network_flag="--goerli"
        ;;

    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
esac

if [[ ! -f "$authrpc_jwtsecret_path" ]] ; then
		openssl rand -hex 32 > "$authrpc_jwtsecret_path"
fi

exec geth \
     --http \
     --http.addr 0.0.0.0 \
     --http.api eth,net \
     --http.vhosts '*' \
		 --authrpc.addr 0.0.0.0 \
		 --authrpc.vhosts '*' \
		 --authrpc.jwtsecret "$authrpc_jwtsecret_path" \
     --metrics \
     --pprof \
     --pprof.addr 0.0.0.0 \
     $network_flag \
     $@
