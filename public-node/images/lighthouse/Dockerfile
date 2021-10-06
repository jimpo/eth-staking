FROM rust:1 AS builder

RUN apt-get update && \
    apt-get install -y \
        cmake gpg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG MAINTAINER_GPG_KEYSERVER=keyserver.ubuntu.com
ARG MAINTAINER_GPG_FINGERPRINT=0xCAA9A2685516A030F66A0AD877B1309D2E54E914
RUN gpg --keyserver $MAINTAINER_GPG_KEYSERVER --recv-keys $MAINTAINER_GPG_FINGERPRINT

ARG PORTABLE=0
ENV PORTABLE $PORTABLE
ARG TAG_REF=9b3b83dbfd759efc60b7f6e80dcd577902b2cadb
RUN git clone https://github.com/sigp/lighthouse /lighthouse && \
    cd /lighthouse && \
    git checkout $TAG_REF && \
    git verify-tag $TAG_REF && \
    make install && \
    make install-lcli

FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/cargo/bin/lighthouse /usr/local/bin/lighthouse
COPY --from=builder /usr/local/cargo/bin/lcli /usr/local/bin/lcli

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir /home/somebody/.lighthouse
VOLUME /home/somebody/.lighthouse

COPY run.sh /home/somebody/

EXPOSE 5052 5054 9000 9000/udp
ENTRYPOINT ["./run.sh"]
