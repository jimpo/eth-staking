FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y python3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY public/ /root/public/

EXPOSE 5052
CMD ["python3", "-m", "http.server", "--directory", "public", "5052"]
