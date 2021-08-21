#!/bin/bash

set -e

for validator_dir in $CANONICAL_DIR/validators/0x* ; do
    if [[ -d $validator_dir ]] ; then
        lighthouse account validator import \
            --datadir $LIGHTHOUSE_DIR \
            --network "$ETH2_NETWORK" \
            --password-file $validator_dir/password.txt \
            --reuse-password \
            --keystore $validator_dir/keystore.json
    fi
done

if [[ -s $CANONICAL_DIR/slashing-protection.json ]] ; then
    lighthouse account validator slashing-protection import \
        --datadir $LIGHTHOUSE_DIR \
        --network "$ETH2_NETWORK" \
        $CANONICAL_DIR/slashing-protection.json
fi

lighthouse validator \
    --datadir $LIGHTHOUSE_DIR \
    --network "$ETH2_NETWORK" \
    --beacon-nodes "$BEACON_NODES" \
    &

validator_pid=$!

sigint_handler() {
    kill -s SIGINT $validator_pid
}
sigterm_handler() {
    kill -s SIGTERM $validator_pid
}
trap sigint_handler SIGINT
trap sigterm_handler SIGTERM

set +e
wait $validator_pid
retcode=$?

lighthouse account validator slashing-protection export \
    --datadir $LIGHTHOUSE_DIR \
    --network "$ETH2_NETWORK" \
    $CANONICAL_DIR/slashing-protection.json

exit $?
