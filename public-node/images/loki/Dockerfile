FROM grafana/loki:latest

USER root
RUN mkdir /var/lib/loki && \
    chown -R loki:loki /var/lib/loki
VOLUME /var/lib/loki
USER loki

COPY config.yaml /etc/loki/config.yaml

