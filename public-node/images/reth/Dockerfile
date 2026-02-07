FROM ubuntu:noble

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG RETH_SIGNING_KEY="50FB 7CC5 5B2E 8AFA 59FE  03B7 AA5E D56A 7FBF 253E"
COPY reth_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/reth_pgp_release_key.asc && \
    gpg --list-keys "$RETH_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/reth_pgp_release_key.asc

ARG ARCH_TRIPLE=x86_64-unknown-linux-gnu
ARG VERSION=v1.10.2
RUN cd /tmp && \
		curl -sSLO https://github.com/paradigmxyz/reth/releases/download/$VERSION/reth-$VERSION-$ARCH_TRIPLE.tar.gz && \
		curl -sSLO https://github.com/paradigmxyz/reth/releases/download/$VERSION/reth-$VERSION-$ARCH_TRIPLE.tar.gz.asc && \
    gpg --verify reth-$VERSION-$ARCH_TRIPLE.tar.gz.asc 2>&1 | \
        grep "Primary key fingerprint: $RETH_SIGNING_KEY" && \
    tar -zxf reth-$VERSION-$ARCH_TRIPLE.tar.gz && \
    cp reth /usr/local/bin/reth && \
    rm -rf reth reth-$VERSION-$ARCH_TRIPLE.tar.gz reth-$VERSION-$ARCH_TRIPLE.tar.gz.asc

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir -p .local/share/reth
VOLUME /home/somebody/.local/share/reth

RUN mkdir authrpc-secret
VOLUME /home/somebody/authrpc-secret

COPY run.sh .

EXPOSE 6060 8545 8551 30303 30303/udp
ENTRYPOINT ["./run.sh"]
