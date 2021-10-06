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
ARG VERSION=v2.0.0
ARG BINNAME=validator
ARG CHECKSUM=312166c8e6352d6ba8f41d106894b567ec5efa3e9ad5e6f113e7746259b847c0
RUN cd /tmp && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-$ARCH.sig && \
    gpg -u "$PRYLABS_SIGNING_KEY" --verify $BINNAME-$VERSION-linux-$ARCH.sig && \
    [ "$(sha256sum $BINNAME-$VERSION-linux-$ARCH | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    cp $BINNAME-$VERSION-linux-$ARCH /usr/local/bin/$BINNAME && \
    chmod +x /usr/local/bin/$BINNAME && \
    rm $BINNAME-$VERSION-linux-$ARCH $BINNAME-$VERSION-linux-$ARCH.sig

RUN mkdir /app && \
    mkdir /app/canonical && \
    mkdir /app/prysm
WORKDIR /app

ENV CANONICAL_DIR=/app/canonical PRYSM_DIR=/app/prysm
VOLUME /app/canonical
RUN chmod 0777 /app/prysm

COPY run.sh /app/

USER nobody
CMD ["/app/run.sh"]
