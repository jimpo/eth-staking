#!/bin/bash

authrpc_jwtsecret_path="authrpc-secret/jwtsecret"
while [[ ! -f "$authrpc_jwtsecret_path" ]] ; do
		echo "Waiting for execution layer to generate authrpc secret..."
		sleep 10
done

validator_monitor_file=validator-pubkeys.txt
validator_monitor_flag=""
if [[ -s "$validator_monitor_file" ]] ; then
    validator_monitor_flag="--validator-monitor-file $validator_monitor_file"
fi

while [[ ! -f "$authrpc_jwtsecret_path" ]] ; do
		echo "Waiting for execution layer to generate authrpc secret..."
		sleep 10
done

docker_internal_ip=$(getent hosts host.docker.internal | cut -d ' ' -f1)

exec lighthouse beacon_node \
		 --disable-upnp \
		 --http \
		 --http-address "$docker_internal_ip" \
		 --eth1 \
		 --metrics \
		 --metrics-address "$docker_internal_ip" \
		 --execution-endpoint http://$ETH1_HOST:8551 \
		 --execution-jwt "$authrpc_jwtsecret_path" \
		 --checkpoint-sync-url https://sync-mainnet.beaconcha.in \
		 --builder $BUILDER_URL \
     $validator_monitor_flag \
     --network "$ETH2_NETWORK" \
     $@
