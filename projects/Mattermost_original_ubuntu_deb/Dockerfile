FROM localhost/ubuntu-noble-base:24.04

# Mattermost GPG key fingerprint: A1B31D46F0F3A10B02CF2D44F8F2C31744774B28
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg && \
    curl -fsSL https://deb.packages.mattermost.com/pubkey.gpg | \
        gpg --dearmor -o /usr/share/keyrings/mattermost-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/mattermost-archive-keyring.gpg] https://deb.packages.mattermost.com noble main" \
        > /etc/apt/sources.list.d/mattermost.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mattermost && \
    apt-get purge -y gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN chown -R mattermost:mattermost /opt/mattermost

USER mattermost

EXPOSE 8065

VOLUME ["/opt/mattermost/config", "/opt/mattermost/data", "/opt/mattermost/logs", "/opt/mattermost/plugins"]

WORKDIR /opt/mattermost

ENTRYPOINT ["bin/mattermost"]
