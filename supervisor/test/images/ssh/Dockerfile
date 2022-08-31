FROM ubuntu:jammy

RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Host should only have one ED25519 SSH key
RUN rm /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub
COPY ssh_host_ed25519_key ssh_host_ed25519_key.pub /etc/ssh/
RUN chmod 0600 /etc/ssh/ssh_host_ed25519_key && \
    echo "HostKey /etc/ssh/ssh_host_ed25519_key" >> /etc/ssh/sshd_config

RUN mkdir /var/run/sshd

# Create unprivileged user
RUN useradd -m somebody

USER somebody
RUN cd /home/somebody && mkdir .ssh supervisor-backups
USER root

COPY --chown=somebody:somebody authorized_keys /home/somebody/.ssh/authorized_keys

EXPOSE 22
CMD /usr/sbin/sshd -D -e
