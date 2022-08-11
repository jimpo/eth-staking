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
ARG VERSION=v2.1.4
ARG CHECKSUM=80246ccdee12823c0dafec6456524c10e5a689a8a36c6a458a581c92f9cb856d
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

COPY run.sh /home/somebody/

RUN mkdir /home/somebody/.eth2

EXPOSE 3500 4000 8080
ENTRYPOINT ["./run.sh"]
