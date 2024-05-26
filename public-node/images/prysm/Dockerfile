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
ARG VERSION=v4.0.7
ARG CHECKSUM=a606f3e95f5504ef67a9ed4871a5dfc710f0b932f5917b64af235ecbfd56eb8d
ARG BINNAME=beacon-chain
RUN cd /tmp && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-modern-linux-$ARCH && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-modern-linux-$ARCH.sig && \
    gpg --verify $BINNAME-$VERSION-modern-linux-$ARCH.sig 2>&1 | \
        grep "Primary key fingerprint: $PRYLABS_SIGNING_KEY" && \
    [ "$(sha256sum $BINNAME-$VERSION-modern-linux-$ARCH | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    cp $BINNAME-$VERSION-modern-linux-$ARCH /usr/local/bin/$BINNAME && \
    chmod +x /usr/local/bin/$BINNAME && \
    rm $BINNAME-$VERSION-modern-linux-$ARCH $BINNAME-$VERSION-modern-linux-$ARCH.sig

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
