FROM alpine:3.19

RUN apk add --no-cache \
    bash \
    python3 \
    py3-pip \
    py3-virtualenv \
    jq \
    git \
    ca-certificates

# sgpt CLI + reportlab for PDF + offlineimap3 (inside venv)
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir shell-gpt reportlab \
 && /opt/venv/bin/pip install --upgrade litellm \
 && /opt/venv/bin/pip install --no-cache-dir git+https://github.com/OfflineIMAP/offlineimap3.git \
 && ln -s /opt/venv/bin/offlineimap3 /usr/local/bin/offlineimap

ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# copy scripts + static files (configs are bind-mounted at runtime)
COPY bin/ ./bin/
COPY rules/ ./rules/
COPY mirror_dir_gmail.json_example ./
COPY offlineimaprc_example ./
COPY goodie_openclaw_low_llm_advises.txt ./
COPY README.md ./

ENV PATH="/app/bin:${PATH}"

# default command (override in docker-compose or docker run)
CMD ["/bin/bash"]
