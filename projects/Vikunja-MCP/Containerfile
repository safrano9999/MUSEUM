# Source of truth: SCRIPTS/githubactions. Generated copies are overwritten.
# syntax=docker/dockerfile:1.7

ARG VIKUNJA_IMAGE=docker.io/vikunja/vikunja:2.6.0@sha256:417ada6f94e81f0267aa2f007d0a811fc82d38dd2aa58351e3ea520ca01c2ea5
ARG NODE_IMAGE=docker.io/library/node:26.12.1-alpine@sha256:40cd011b55415bc894e45b02fdd5a5dfde056921b7d23a64c74f80497af48797

FROM ${VIKUNJA_IMAGE} AS vikunja

FROM ${NODE_IMAGE} AS builder
ARG BETTER_SQLITE3_VERSION=12.10.1
ARG VIKUNJA_MCP_REVISION=a42e1c2a3bd2b694e79a944fba5153970157b19d
ARG SUPERGATEWAY_REVISION=a3ce8ba34c40f7565d1786e1dbd19621aca86093
RUN apk upgrade --no-cache \
    && apk add --no-cache git 'python3>=3.14.8-r0' make g++ 'ca-certificates>=20261020-r0' \
    && test "$(node --version)" = v26.12.1
COPY .github/scripts/patch-vikunja-mcp.py /usr/local/bin/patch-vikunja-mcp.py

WORKDIR /src/vikunja-mcp
RUN git init \
    && git remote add origin https://github.com/democratize-technology/vikunja-mcp.git \
    && git fetch --depth=1 origin "${VIKUNJA_MCP_REVISION}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${VIKUNJA_MCP_REVISION}" \
    && npm install --package-lock-only --ignore-scripts --save-exact "better-sqlite3@${BETTER_SQLITE3_VERSION}" \
    && npm ci \
    && node -e "const Database = require('better-sqlite3'); const db = new Database(':memory:'); if (db.prepare('select 42 as n').get().n !== 42) process.exit(1); db.close()" \
    && python3 /usr/local/bin/patch-vikunja-mcp.py . \
    && npm run build \
    && npm prune --omit=dev

WORKDIR /src/supergateway
RUN git init \
    && git remote add origin https://github.com/supercorp-ai/supergateway.git \
    && git fetch --depth=1 origin "${SUPERGATEWAY_REVISION}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${SUPERGATEWAY_REVISION}"
COPY patches/supergateway-bearer.patch /tmp/supergateway-bearer.patch
COPY patches/verify-supergateway.mjs /tmp/verify-supergateway.mjs
RUN git apply --unidiff-zero --check /tmp/supergateway-bearer.patch \
    && git apply --unidiff-zero /tmp/supergateway-bearer.patch \
    && npm ci \
    && npm run build \
    && node /tmp/verify-supergateway.mjs /src/supergateway VIKUNJA_API_TOKEN \
    && npm prune --omit=dev

FROM ${NODE_IMAGE}
RUN apk upgrade --no-cache \
    && apk add --no-cache 'ca-certificates>=20261020-r0' tini \
    && test "$(node --version)" = v26.12.1 \
    && mkdir -p /app/vikunja/files /opt/vikunja-mcp /opt/supergateway \
    && chown -R 1000:1000 /app/vikunja /opt/vikunja-mcp /opt/supergateway
COPY --from=vikunja --chown=1000:1000 /app/vikunja/vikunja /app/vikunja/vikunja
COPY --from=builder --chown=1000:1000 /src/vikunja-mcp/dist /opt/vikunja-mcp/dist
COPY --from=builder --chown=1000:1000 /src/vikunja-mcp/node_modules /opt/vikunja-mcp/node_modules
COPY --from=builder --chown=1000:1000 /src/vikunja-mcp/package.json /opt/vikunja-mcp/package.json
COPY --from=builder --chown=1000:1000 /src/supergateway/dist /opt/supergateway/dist
COPY --from=builder --chown=1000:1000 /src/supergateway/node_modules /opt/supergateway/node_modules
COPY --from=builder --chown=1000:1000 /src/supergateway/package.json /opt/supergateway/package.json
COPY --chown=1000:1000 --chmod=0755 entrypoint.sh /usr/local/bin/vikunja-mcp-entrypoint

LABEL org.opencontainers.image.title="Vikunja MCP" \
      org.opencontainers.image.description="Vikunja 2.6.0 with a bearer-scoped Streamable HTTP MCP bridge" \
      org.opencontainers.image.source="https://github.com/safrano9999/Vikunja-MCP" \
      org.opencontainers.image.licenses="AGPL-3.0-and-MIT" \
      org.opencontainers.image.base.name="docker.io/vikunja/vikunja:2.6.0" \
      org.opencontainers.image.base.digest="sha256:417ada6f94e81f0267aa2f007d0a811fc82d38dd2aa58351e3ea520ca01c2ea5"

ENV NODE_ENV=production \
    VIKUNJA_SERVICE_ROOTPATH=/app/vikunja/ \
    VIKUNJA_DATABASE_PATH=/tmp/vikunja.db \
    VIKUNJA_PORT=3456 \
    VIKUNJA_MCP_PORT=8000 \
    VIKUNJA_MCP_PATH=/mcp \
    VIKUNJA_API_URL=http://127.0.0.1:3456/api/v1
WORKDIR /app/vikunja
USER 1000
EXPOSE 3456 8000
ENTRYPOINT ["/sbin/tini", "-g", "--", "/usr/local/bin/vikunja-mcp-entrypoint"]
