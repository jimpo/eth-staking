#!/bin/bash

set -e

cd ~/local_testnet_scripts

./ganache_test_node.sh >../ganache.log &
tail -f ../ganache.log | grep -m1 'Listening on 127.0.0.1:8545'

./bootnode.sh >../bootnode.log 2>&1 &
tail -f ../bootnode.log | grep -m1 'Starting bootnode'

source ./vars.env

# Such a hack, but jam another flag in after the http port arg
./beacon_node.sh $DATADIR/node_1 9000 "5052 --http-address 0.0.0.0" >../beacon_node_1.log 2>&1 &
tail -f ../beacon_node_1.log | grep -m1 'HTTP API started'

./beacon_node.sh $DATADIR/node_2 9001 5053 >../beacon_node_2.log 2>&1 &
tail -f ../beacon_node_2.log | grep -m1 'HTTP API started'

tail -n +0 -f ../beacon_node_1.log
