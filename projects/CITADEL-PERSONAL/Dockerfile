FROM quay.io/fedora/fedora:latest

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN dnf install -y \
    caddy \
    php-fpm \
    php-json \
    python3 \
    python3-pip \
    python3-virtualenv \
    iproute \
    procps-ng \
    curl \
    openssl \
    iptables-nft \
    tmux \
    findutils \
    git \
    nodejs \
    npm \
    && dnf clean all

# Process supervisor for multi-service runtime
RUN python3 -m pip install --no-cache-dir supervisor

# Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

# PHP-FPM: listen on TCP, run as nobody
RUN mkdir -p /run/php-fpm && \
    sed -i 's|^listen = .*|listen = 127.0.0.1:9000|' /etc/php-fpm.d/www.conf && \
    sed -i 's|^user = .*|user = nobody|' /etc/php-fpm.d/www.conf && \
    sed -i 's|^group = .*|group = nobody|' /etc/php-fpm.d/www.conf

# Build context must be: /home/openclaw/safrano9999
COPY CITADEL /opt/citadel
COPY PV_D-A-CH /opt/apps/PV_D-A-CH
COPY JUGO /opt/apps/JUGO
COPY CODEANALYST /opt/apps/CODEANALYST
COPY NAPOLEON_HILLS_AI_MASTERMIND_CLASSES /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES

RUN chmod +x /opt/citadel/scan.sh

# Remove copied host virtualenvs to avoid broken interpreter paths in container.
RUN rm -rf \
    /opt/apps/PV_D-A-CH/venv \
    /opt/apps/JUGO/venv \
    /opt/apps/CODEANALYST/venv \
    /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/venv

# App virtualenvs
RUN python3 -m venv /opt/citadel/hello_world/venv && \
    /opt/citadel/hello_world/venv/bin/pip install -r /opt/citadel/hello_world/requirements.txt

RUN python3 -m venv /opt/apps/PV_D-A-CH/venv && \
    /opt/apps/PV_D-A-CH/venv/bin/pip install -r /opt/apps/PV_D-A-CH/requirements.txt

RUN python3 -m venv /opt/apps/JUGO/venv && \
    /opt/apps/JUGO/venv/bin/pip install -r /opt/apps/JUGO/requirements.txt

RUN python3 -m venv /opt/apps/CODEANALYST/venv && \
    /opt/apps/CODEANALYST/venv/bin/pip install -r /opt/apps/CODEANALYST/requirements.txt

RUN python3 -m venv /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/venv && \
    /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/apps/NAPOLEON_HILLS_AI_MASTERMIND_CLASSES/venv/bin/pip install flask python-dotenv requests

# Node CLIs are installed at container start (if missing) to avoid
# rootless Podman layer-commit stalls on huge npm trees during build.

# Hermes Agent CLI (installed from upstream repo, no login/config)
RUN git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /opt/tools/hermes-agent && \
    python3 -m venv /opt/tools/hermes-agent/venv && \
    /opt/tools/hermes-agent/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/tools/hermes-agent/venv/bin/pip install -r /opt/tools/hermes-agent/requirements.txt && \
    /opt/tools/hermes-agent/venv/bin/pip install -e /opt/tools/hermes-agent && \
    ln -sf /opt/tools/hermes-agent/venv/bin/hermes /usr/local/bin/hermes && \
    ln -sf /opt/tools/hermes-agent/venv/bin/hermes-agent /usr/local/bin/hermes-agent

# Caddyfile + private entrypoint
COPY CITADEL/deploy/Caddyfile /etc/caddy/Caddyfile
COPY CITADEL/PERSONAL/entrypoint.private.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
