#!/bin/bash

set -e

wallet_dir="$HOME/.eth2validators/prysm-wallet-v2"
datadir="$HOME/.eth2"
wallet_password_file=wallet-password.txt

# Generate secure random wallet password
apg -m 20 -x 20 -a 1 -M SNCL -n 1 -c /dev/urandom > $wallet_password_file

validator wallet create \
    --"$ETH2_NETWORK" \
    --accept-terms-of-use \
    --wallet-dir=$wallet_dir \
    --wallet-password-file=$wallet_password_file \
    --keymanager-kind=direct

for validator_dir in $CANONICAL_DIR/validators/0x* ; do
    if [[ -d $validator_dir ]] ; then
        validator accounts import \
            --"$ETH2_NETWORK" \
            --wallet-dir=$wallet_dir \
            --wallet-password-file=$wallet_password_file \
            --account-password-file=$validator_dir/password.txt \
            --keys-dir=$validator_dir
    fi
done

if [[ -s $CANONICAL_DIR/slashing-protection.json ]] ; then
    validator slashing-protection import \
        --"$ETH2_NETWORK" \
        --datadir=$datadir \
        --slashing-protection-json-file=$CANONICAL_DIR/slashing-protection.json
fi

# validator \
#     --"$ETH2_NETWORK" \
#     --datadir=$datadir \
#     --wallet-dir=$wallet_dir \
#     --wallet-password-file=$wallet_password_file \
#     &

# echo "blah" &

# validator_pid=$!

# sigint_handler() {
#     kill -s SIGINT $validator_pid
# }
# sigterm_handler() {
#     kill -s SIGTERM $validator_pid
# }
# trap sigint_handler SIGINT
# trap sigterm_handler SIGTERM

# set +e
# wait $validator_pid
# retcode=$?

# validator slashing-protection export \
#     --network "$ETH2_NETWORK" \
#     $CANONICAL_DIR/slashing-protection.json

# exit $?
