FROM localhost/ubuntu-noble-base:24.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -r -m -d /app -s /bin/bash litellm

WORKDIR /app

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    'litellm[proxy]' \
    psycopg2-binary

RUN chown -R litellm:litellm /app

USER litellm

EXPOSE 4000

ENTRYPOINT ["litellm", "--config", "/app/config/litellm_config.yaml", "--port", "4000"]
