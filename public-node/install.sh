#!/bin/bash

set -e

if [[ "$1" == "init" ]] ; then
    is_update=0
elif [[ "$1" == "update" ]] ; then
    is_update=1
else
    echo "usage: $0 {init|update}" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get upgrade -y \
    -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

if [[ $is_update -ne 1 ]] ; then
    # Install Docker
    # See https://docs.docker.com/engine/install/ubuntu/
    apt-get -y install \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    docker_gpg_fingerprint=9DC858229FC7DD38854AE2D88D81803C0EBFCD88
    docker_gpg_keyring_file=/usr/share/keyrings/docker-archive-keyring.gpg
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --import
    gpg --export $docker_gpg_fingerprint > $docker_gpg_keyring_file
    echo \
    "deb [arch=amd64 signed-by=$docker_gpg_keyring_file] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
fi

# Install Docker Compose
docker_compose_sha256=f3f10cf3dbb8107e9ba2ea5f23c1d2159ff7321d16f0a23051d68d8e2547b323
docker_compose_path=/usr/local/bin/docker-compose
if [[ $is_update -eq 1 && \
      -x $docker_compose_path && \
      $(sha256sum $docker_compose_path | cut -d ' ' -f 1) == $docker_compose_sha256 ]] ; then
    echo "docker-compose is already latest version"
else
    echo "$docker_compose_sha256 docker-compose" > docker-compose.sha256
    curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o docker-compose
    sha256sum -c docker-compose.sha256
    chmod +x docker-compose
    mv docker-compose /usr/local/bin
    rm docker-compose.sha256
fi

# Install or update docker-services systemd unit
if [[ $is_update -eq 1 ]] ; then
    systemctl stop docker-services.service

    # If docker-services.service, restart systemctl
    set +e
    diff docker-services.service /etc/systemd/system/docker-services.service --brief >/dev/null 2>&1
    diff_retcode=$?
    set -e
    if [[ $diff_retcode -ne 0 ]] ; then
        echo "Updating docker-services.service..."
        cp docker-services.service /etc/systemd/system/
        systemctl daemon-reload
    fi
else
    cp docker-services.service /etc/systemd/system/
fi

rm -rf /services
mkdir /services

# Initialize Docker services
cp -r docker-compose.yml images authorized_keys validator-pubkeys.txt /services
docker-compose --project-directory /services build --pull

# Configure Docker daemon
# If docker-daemon.json changed, restart Docker service
set +e
diff docker-daemon.json /etc/docker/daemon.json --brief >/dev/null 2>&1
diff_retcode=$?
set -e
if [[ $diff_retcode -ne 0 ]] ; then
    echo "Updating /etc/docker/daemon.json..."
    cp docker-daemon.json /etc/docker/daemon.json
    systemctl restart docker.service
fi

systemctl enable docker-services.service
systemctl start docker-services.service
