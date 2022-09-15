#!/bin/bash

set -e

authrpc_jwtsecret_path="authrpc-secret/jwtsecret"
while [[ ! -f "$authrpc_jwtsecret_path" ]] ; do
		echo "Waiting for execution layer to generate authrpc secret..."
		sleep 10
done

set_network_flags() {
    network_flags="--$ETH2_NETWORK"
    if [[ -n "$genesis_state_sha256" ]] ; then
        genesis_state_path="${ETH2_NETWORK}_genesis_state.ssz"
        curl -sSL -o $genesis_state_path \
             https://github.com/eth2-clients/eth2-networks/blob/master/shared/$genesis_state_name/genesis.ssz\?raw\=true
        echo "$genesis_state_sha256  $genesis_state_path" | sha256sum -c
        network_flags="$network_flags --genesis-state=$genesis_state_path"
    fi
}

case "$ETH2_NETWORK" in
    mainnet)
        # For mainnet, genesis state is built into the binary, so no need to download it
        ;;
    goerli)
        genesis_state_sha256="23daa70a970034444da4dc04abfab7b7dd08adaadefb1f9764ac56ea58b2086e"
				genesis_state_name="prater"
        ;;
    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
        ;;
esac

validator_monitor_file=validator-indices.txt
validator_monitor_flag=""
if [[ -f "$validator_monitor_file" ]] ; then
		for index in $(cat $validator_monitor_file) ; do
				validator_monitor_flag="$validator_monitor_flag --monitor-indices $index"
		done
fi

set_network_flags
exec beacon-chain --accept-terms-of-use \
     $network_flags \
     --rpc-host host.docker.internal \
     --grpc-gateway-host host.docker.internal \
     --monitoring-host host.docker.internal \
     --execution-endpoint http://$ETH1_HOST:8551 \
		 --jwt-secret "$authrpc_jwtsecret_path" \
		 $validator_monitor_flag \
     $@
