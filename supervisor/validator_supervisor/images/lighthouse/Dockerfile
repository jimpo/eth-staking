FROM rust:1.52.1 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cmake && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG PORTABLE
ENV PORTABLE $PORTABLE
ARG COMMIT=3b600acdc5bf9726367c18277a22486573b8b457
RUN git clone https://github.com/sigp/lighthouse /lighthouse && \
    cd /lighthouse && \
    git checkout $COMMIT && \
    make install && \
    make install-lcli

FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/cargo/bin/lighthouse /usr/local/bin/lighthouse
COPY --from=builder /usr/local/cargo/bin/lcli /usr/local/bin/lcli

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
