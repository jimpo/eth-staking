#!/bin/bash

authrpc_jwtsecret_path="authrpc-secret/jwtsecret"

if [[ ! -f "$authrpc_jwtsecret_path" ]] ; then
		openssl rand -hex 32 > "$authrpc_jwtsecret_path"
fi

exec reth node \
		 --full \
     --http \
     --http.addr 0.0.0.0 \
     --http.api eth,net \
     --http.corsdomain '*' \
		 --authrpc.addr 0.0.0.0 \
		 --authrpc.jwtsecret "$authrpc_jwtsecret_path" \
     --metrics 0.0.0.0:6060 \
     --chain "$ETH2_NETWORK" \
     $@
