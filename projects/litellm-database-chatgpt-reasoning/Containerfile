# Source of truth: SCRIPTS/githubactions. Generated copies are overwritten.
FROM ghcr.io/berriai/litellm-database:v1.104.0@sha256:fbe28229d2d02181c0a7d9df9599de614b491f3d897d2d7da18404f088310218
RUN --mount=type=bind,source=patches,target=/tmp/patches,readonly \
    apk add --no-cache --virtual .patch-deps patch \
    && cd /app/.venv/lib/python3.13/site-packages \
    && sha256sum -c /tmp/patches/base-v1.104.0.sha256 \
    && patch --batch --forward --fuzz=0 -p1 < /tmp/patches/pr31332-runtime.patch \
    && python3 -m py_compile litellm/responses/mcp/mcp_streaming_iterator.py litellm/responses/streaming_iterator.py litellm/router.py \
    && apk del .patch-deps
