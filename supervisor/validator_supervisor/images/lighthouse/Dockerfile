FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y \
        ca-certificates curl gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# PGP key hosted at https://keybase.io/sigp/pgp_keys.asc?fingerprint=15e66d941f697e28f49381f426416dc3f30674b0
ARG SIGP_SIGNING_KEY=15E66D941F697E28F49381F426416DC3F30674B0
COPY sigp_pgp_release_key.asc /tmp/
RUN gpg --import /tmp/sigp_pgp_release_key.asc && \
    gpg --list-keys "$SIGP_SIGNING_KEY" >/dev/null 2>&1 && \
    rm /tmp/sigp_pgp_release_key.asc

ARG ARCH=x86_64
ARG VERSION=v1.5.2
# Double check checksum in addition to PGP sig out of extreme paranoia
ARG CHECKSUM=924a5441c3fb6f01da75273290324af85aae2f66e84fdce1899e8b265176c782
RUN cd /tmp && \
    curl -sSLO https://github.com/sigp/lighthouse/releases/download/$VERSION/lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz && \
    curl -sSLO https://github.com/sigp/lighthouse/releases/download/$VERSION/lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc && \
    gpg -u "$SIGP_SIGNING_KEY" --verify lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc && \
    [ "$(sha256sum lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz | cut -d ' ' -f 1)" = "$CHECKSUM" ] && \
    tar -zxf lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz && \
    cp lighthouse /usr/local/bin/lighthouse && \
    rm lighthouse lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz lighthouse-$VERSION-$ARCH-unknown-linux-gnu.tar.gz.asc

RUN mkdir /app && \
    mkdir /app/canonical && \
    mkdir /app/lighthouse
WORKDIR /app

ENV CANONICAL_DIR=/app/canonical LIGHTHOUSE_DIR=/app/lighthouse
VOLUME /app/canonical
RUN chmod 0777 /app/lighthouse

COPY run.sh /app/

USER nobody
CMD ["/app/run.sh"]
