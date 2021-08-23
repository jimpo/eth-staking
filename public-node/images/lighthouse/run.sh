#!/bin/bash

validator_monitor_file=validator-pubkeys.txt
validator_monitor_flag=""
if [[ -s validator-pubkeys.txt ]] ; then
    validator_monitor_flag="--validator-monitor-file $validator_monitor_file"
fi

exec lighthouse beacon_node \
     --disable-upnp \
     --http \
     --http-address 0.0.0.0 \
     --eth1 \
     --eth1-endpoints http://$ETH1_HOST:8545 \
     --metrics \
     --metrics-address 0.0.0.0 \
     $validator_monitor_flag \
     --network "$ETH2_NETWORK" \
     $@
