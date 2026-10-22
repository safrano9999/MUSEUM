#!/bin/sh
set -eu

export VIKUNJA_SERVICE_INTERFACE=":${VIKUNJA_PORT:-3456}"
export VIKUNJA_URL="${VIKUNJA_API_URL:-http://127.0.0.1:3456/api/v1}"
unset VIKUNJA_API_TOKEN

/app/vikunja/vikunja web &
vikunja_pid=$!
node /opt/supergateway/dist/index.js \
  --stdio "node /opt/vikunja-mcp/dist/index.js" \
  --outputTransport streamableHttp \
  --stateful \
  --port "${VIKUNJA_MCP_PORT:-8000}" \
  --streamableHttpPath "${VIKUNJA_MCP_PATH:-/mcp}" \
  --healthEndpoint /healthz \
  --sessionTimeout "${VIKUNJA_MCP_SESSION_TIMEOUT:-3600000}" \
  --logLevel "${VIKUNJA_MCP_LOG_LEVEL:-info}" &
mcp_pid=$!

stop() {
  kill "$vikunja_pid" "$mcp_pid" 2>/dev/null || true
  wait "$vikunja_pid" "$mcp_pid" 2>/dev/null || true
}
trap 'stop; exit 143' TERM
trap 'stop; exit 130' INT
while kill -0 "$vikunja_pid" 2>/dev/null && kill -0 "$mcp_pid" 2>/dev/null; do sleep 1; done
set +e
if ! kill -0 "$vikunja_pid" 2>/dev/null; then wait "$vikunja_pid"; else wait "$mcp_pid"; fi
status=$?
set -e
stop
exit "$status"
