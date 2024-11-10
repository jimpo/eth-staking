#!/bin/bash

authrpc_jwtsecret_path="authrpc-secret/jwtsecret"

case "$ETH2_NETWORK" in
    mainnet)
        network_flag="--chain mainnet"
        ;;

    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
esac

if [[ ! -f "$authrpc_jwtsecret_path" ]] ; then
		openssl rand -hex 32 > "$authrpc_jwtsecret_path"
fi

exec reth node \
		 --full \
     --http \
     --http.addr 172.17.0.1 \
     --http.api eth,net \
     --http.corsdomain '*' \
		 --authrpc.addr 172.17.0.1 \
		 --authrpc.jwtsecret "$authrpc_jwtsecret_path" \
     --metrics 172.17.0.1:6060 \
     $network_flag \
     $@
