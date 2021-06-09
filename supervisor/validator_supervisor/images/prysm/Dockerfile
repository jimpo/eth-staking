FROM ubuntu:focal as builder

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg apg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG PRYLABS_SIGNING_KEY=0AE0051D647BA3C1A917AF4072E33E4DF1A5036E
RUN gpg --list-keys "$PRYLABS_SIGNING_KEY" >/dev/null 2>&1 || curl -sSL https://prysmaticlabs.com/releases/pgp_keys.asc | gpg --import

ARG VERSION=v1.4.2
ARG BINNAME=validator
RUN cd /tmp && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-amd64 && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-amd64.sha256 && \
    curl -sSLO https://github.com/prysmaticlabs/prysm/releases/download/$VERSION/$BINNAME-$VERSION-linux-amd64.sig && \
    gpg -u "$PRYLABS_SIGNING_KEY" --verify $BINNAME-$VERSION-linux-amd64.sig && \
    sha256sum -c $BINNAME-$VERSION-linux-amd64.sha256 && \
    cp $BINNAME-$VERSION-linux-amd64 /usr/local/bin/$BINNAME && \
    chmod +x /usr/local/bin/$BINNAME && \
    rm $BINNAME-$VERSION-linux-amd64 $BINNAME-$VERSION-linux-amd64.sha256 $BINNAME-$VERSION-linux-amd64.sig

RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

ENV CANONICAL_DIR=/home/somebody/canonical
RUN mkdir /home/somebody/canonical
VOLUME /home/somebody/canonical

COPY run.sh /home/somebody/
CMD ["./run.sh"]
