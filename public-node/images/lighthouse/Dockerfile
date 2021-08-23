# https://github.com/sigp/lighthouse/issues/2420
FROM rust:1.52.1 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cmake && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG PORTABLE
ENV PORTABLE $PORTABLE
ARG COMMIT=90d5ab15660e62e16390731d92c74b640a70bed9
RUN git clone https://github.com/sigp/lighthouse /lighthouse && \
    cd /lighthouse && \
    git checkout $COMMIT && \
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
