FROM ubuntu:noble

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG SIGP_SIGNING_KEY="15E6 6D94 1F69 7E28 F493  81F4 2641 6DC3 F306 74B0"
COPY sigp_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/sigp_pgp_release_key.asc && \
    gpg --list-keys "$SIGP_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/sigp_pgp_release_key.asc

ARG ARCH=x86_64
ARG VERSION=v8.1.0
# Double check checksum in addition to PGP sig out of extreme paranoia
ARG CHECKSUM=6a8c31866045f3d623af08d1498902253fa1b0c009856b33d15d091941af28db
RUN cd /tmp && \
    curl -sSLO https://github.com/sigp/lighthouse/releases/download/$VERSION/lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz && \
    curl -sSLO https://github.com/sigp/lighthouse/releases/download/$VERSION/lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc && \
    gpg --verify lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc 2>&1 | \
	      grep "Primary key fingerprint: $SIGP_SIGNING_KEY" && \
    [ "$(sha256sum lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    tar -zxf lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz && \
    cp lighthouse /usr/local/bin/lighthouse && \
    rm lighthouse lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir .lighthouse
VOLUME /home/somebody/.lighthouse

RUN mkdir authrpc-secret
VOLUME /home/somebody/authrpc-secret

COPY run.sh .

EXPOSE 5052 5054 9000 9000/udp
ENTRYPOINT ["./run.sh"]
