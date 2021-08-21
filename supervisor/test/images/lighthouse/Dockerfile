# https://github.com/sigp/lighthouse/issues/2420
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

FROM node:16

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g npm
RUN npm install -g ganache-cli

COPY --from=builder /usr/local/cargo/bin/lighthouse /usr/local/bin/lighthouse
COPY --from=builder /usr/local/cargo/bin/lcli /usr/local/bin/lcli

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

COPY --from=builder /lighthouse/scripts/local_testnet /home/somebody/local_testnet_scripts
COPY vars.env /home/somebody/local_testnet_scripts/vars.env

COPY run.sh /home/somebody/

EXPOSE 5052
CMD ["./run.sh"]