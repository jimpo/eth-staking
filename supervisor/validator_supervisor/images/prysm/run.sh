#!/bin/bash

set -e

export HOME=/app/prysm
cd $HOME

wallet_dir="$HOME/.eth2validators/prysm-wallet-v2"
datadir="$HOME/.eth2"
wallet_password_file="$HOME/wallet-password.txt"

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

# Workaround https://github.com/prysmaticlabs/prysm/issues/9739 by temporarily making non-default
# location for datadir
alt_datadir="$HOME/eth2data"
mv $datadir $alt_datadir

validator \
    --"$ETH2_NETWORK" \
    --datadir=$alt_datadir \
    --wallet-dir=$wallet_dir \
    --wallet-password-file=$wallet_password_file \
    --beacon-rpc-gateway-provider="$BEACON_HTTP_ENDPOINT" \
    --beacon-rpc-provider="$BEACON_GRPC_ENDPOINT" \
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
set -e

# Restore datadir
mv $alt_datadir $datadir

slashing_protection_export_dir="$HOME/slashing-protection-export"
validator slashing-protection export \
    --datadir=$datadir \
    --slashing-protection-export-dir=$slashing_protection_export_dir
mv $slashing_protection_export_dir/slashing_protection.json $CANONICAL_DIR/slashing-protection.json

exit $retcode
