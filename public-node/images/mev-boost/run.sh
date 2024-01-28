#!/bin/sh

case "$ETH2_NETWORK" in
    mainnet)
				FLAGS="-mainnet -relays https://0xac6e77dfe25ecd6110b8e780608cce0dab71fdd5ebea22a16c0205200f2f8e2e3ad3b71d3499c54ad14d6c21b41a37ae@boost-relay.flashbots.net"
        ;;

    goerli)
				FLAGS="-goerli -relays https://0xafa4c6985aa049fb79dd37010438cfebeb0f2bd42b115b89dd678dab0670c1de38da0c4e9138c9290a398ecd9a0b3110@builder-relay-goerli.flashbots.net"
        ;;

    *)
        echo "unknown network $ETH2_NETWORK" >&2
        exit 1
esac

exec /app/mev-boost -addr "0.0.0.0:18550" -relay-check $FLAGS
