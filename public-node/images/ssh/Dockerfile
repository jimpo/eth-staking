FROM ubuntu:focal

RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Host should only have one ED25519 SSH key
RUN rm /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub && \
    mkdir /etc/ssh/host-keys && \
    ssh-keygen -q -N "" -t ed25519 -f /etc/ssh/host-keys/ssh_host_ed25519_key && \
    echo "HostKey /etc/ssh/host-keys/ssh_host_ed25519_key" >> /etc/ssh/sshd_config

RUN echo "GatewayPorts yes" >> /etc/ssh/sshd_config
RUN mkdir /var/run/sshd

# Create unprivileged user
RUN useradd -m somebody

USER somebody
RUN cd /home/somebody && mkdir .ssh supervisor-backups
USER root

EXPOSE 22
CMD /usr/sbin/sshd -D -e
