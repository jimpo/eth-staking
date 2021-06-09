FROM golang:1 as builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG COMMIT=576681f29b895dd39e559b7ba17fcd89b42e4833
RUN git clone https://github.com/ethereum/go-ethereum /go-ethereum && \
    cd /go-ethereum && \
    git checkout $COMMIT && \
    make geth

FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /go-ethereum/build/bin/geth /usr/local/bin/

# Create unprivileged user
RUN useradd -m somebody
USER somebody
WORKDIR /home/somebody

RUN mkdir /home/somebody/.ethereum
VOLUME /home/somebody/.ethereum

COPY run.sh /home/somebody/

EXPOSE 6060 8545 30303 30303/udp
ENTRYPOINT ["./run.sh"]
