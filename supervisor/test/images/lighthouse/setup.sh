#!/bin/bash

set -e

cd ~/local_testnet_scripts

ganache_log="../ganache.log"
./ganache_test_node.sh >"$ganache_log" &
ganache_pid=$!
tail -f "$ganache_log" | grep -m1 -q 'Listening on 127.0.0.1:8545'

./setup.sh

echo "Stopping ganache..."
kill $ganache_pid
wait $ganache_pid
rm "$ganache_log"
