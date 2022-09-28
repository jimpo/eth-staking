FROM ubuntu:jammy

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG GETH_SIGNING_KEY="FDE5 A1A0 44FA 13D2 F7AD  A019 A61A 1356 9BA2 8146"
COPY geth_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/geth_pgp_release_key.asc && \
    gpg --list-keys "$GETH_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/geth_pgp_release_key.asc

ARG ARCH=amd64
ARG VERSION=1.10.25-69568c55
ARG CHECKSUM=017b180a7cdb2a56deb36204b61532e6959f17236bf52eac427c9aa8554e16c2
RUN cd /tmp && \
    curl -sSLO https://gethstore.blob.core.windows.net/builds/geth-linux-$ARCH-$VERSION.tar.gz && \
    curl -sSLO https://gethstore.blob.core.windows.net/builds/geth-linux-$ARCH-$VERSION.tar.gz.asc && \
    gpg --verify geth-linux-$ARCH-$VERSION.tar.gz.asc 2>&1 | \
        grep "Primary key fingerprint: $GETH_SIGNING_KEY" && \
    [ "$(sha256sum geth-linux-$ARCH-$VERSION.tar.gz | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    tar -zxf geth-linux-$ARCH-$VERSION.tar.gz && \
    cp geth-linux-$ARCH-$VERSION/geth /usr/local/bin/geth && \
    rm -rf geth-linux-$ARCH-$VERSION  geth-linux-$ARCH-$VERSION.tar.gz geth-linux-$ARCH-$VERSION.tar.gz.asc

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir .ethereum
VOLUME /home/somebody/.ethereum

RUN mkdir authrpc-secret
VOLUME /home/somebody/authrpc-secret

COPY run.sh .

EXPOSE 6060 8545 8551 30303 30303/udp
ENTRYPOINT ["./run.sh"]
