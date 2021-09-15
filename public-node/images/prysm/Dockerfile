FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg apg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# PGP key hosted at https://prysmaticlabs.com/releases/pgp_keys.asc
ARG PRYLABS_SIGNING_KEY=0AE0051D647BA3C1A917AF4072E33E4DF1A5036E
COPY prylabs_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/prylabs_pgp_release_key.asc && \
    gpg --list-keys "$PRYLABS_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/prylabs_pgp_release_key.asc

ARG ARCH=amd64
ARG VERSION=v1.4.4
ARG BINNAME=beacon-chain
RUN cd /tmp && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH.sha256 && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH.sig && \
    gpg -u "$PRYLABS_SIGNING_KEY" --verify $BINNAME-$VERSION-linux-$ARCH.sig && \
    sha256sum -c $BINNAME-$VERSION-linux-$ARCH.sha256 && \
    cp $BINNAME-$VERSION-linux-$ARCH /usr/local/bin/$BINNAME && \
    chmod +x /usr/local/bin/$BINNAME && \
    rm $BINNAME-$VERSION-linux-$ARCH $BINNAME-$VERSION-linux-$ARCH.sha256 $BINNAME-$VERSION-linux-$ARCH.sig

RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

COPY run.sh /home/somebody/

RUN mkdir /home/somebody/.eth2

EXPOSE 3501 4000 8080
ENTRYPOINT ["./run.sh"]
