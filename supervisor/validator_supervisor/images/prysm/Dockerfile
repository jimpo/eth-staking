FROM ubuntu:jammy

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
ARG VERSION=v3.0.0
ARG BINNAME=validator
ARG CHECKSUM=9fc69b8c940c30195a3e02b80c1a0e3e08781644945affce79d3afbe9213c7c3
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
