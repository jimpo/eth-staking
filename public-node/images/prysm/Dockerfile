FROM ubuntu:jammy

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg apg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# PGP key hosted at https://prysmaticlabs.com/releases/pgp_keys.asc
ARG PRYLABS_SIGNING_KEY="0AE0 051D 647B A3C1 A917  AF40 72E3 3E4D F1A5 036E"
COPY prylabs_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/prylabs_pgp_release_key.asc && \
    gpg --list-keys "$PRYLABS_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/prylabs_pgp_release_key.asc

ARG ARCH=amd64
ARG VERSION=v3.1.1
ARG CHECKSUM=917c37f41506182da7061aa2e9a15bdecc5d30eaafdc2688c9b0fba7073a7d05
ARG BINNAME=beacon-chain
RUN cd /tmp && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH.sig && \
    gpg --verify $BINNAME-$VERSION-linux-$ARCH.sig 2>&1 | \
        grep "Primary key fingerprint: $PRYLABS_SIGNING_KEY" && \
    [ "$(sha256sum $BINNAME-$VERSION-linux-$ARCH | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    cp $BINNAME-$VERSION-linux-$ARCH /usr/local/bin/$BINNAME && \
    chmod +x /usr/local/bin/$BINNAME && \
    rm $BINNAME-$VERSION-linux-$ARCH $BINNAME-$VERSION-linux-$ARCH.sig

RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir .eth2
VOLUME /home/somebody/.eth2

RUN mkdir authrpc-secret
VOLUME /home/somebody/authrpc-secret

COPY run.sh .

EXPOSE 3500 4000 8080
ENTRYPOINT ["./run.sh"]
