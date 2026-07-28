#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-localhost/citadelprivate:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-citadelprivate}"
IMAGE_NAME_LOWER="${IMAGE_NAME,,}"
CREDS_SRC="${CREDS_SRC:-/srv/shared/openclaw/.PV}"
CREDS_DST="${CREDS_DST:-/run/secrets/pv_creds}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="${STACK_DIR:-${SCRIPT_DIR}/stack}"

load_defaults_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0

  while IFS= read -r raw || [[ -n "$raw" ]]; do
    local line key value
    line="${raw%$'\r'}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    [[ "$value" == \"*\" && "$value" == *\" ]] && value="${value:1:${#value}-2}"
    [[ "$value" == \'*\' && "$value" == *\' ]] && value="${value:1:${#value}-2}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    [[ -n "${!key+x}" ]] && continue
    export "$key=$value"
  done < "$file"
}

load_defaults_file "${STACK_DIR}/common.env"
load_defaults_file "${STACK_DIR}/ports.env"
load_defaults_file "${STACK_DIR}/services.env"

OPENAI_API_BASE="${OPENAI_API_BASE:-http://127.0.0.1:4000/v1}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DEFAULT_MODEL="${DEFAULT_MODEL:-openai/gpt-5.4}"

PV_DACH_PORT="${PV_DACH_PORT:-8080}"
CODEANALYST_PORT="${CODEANALYST_PORT:-820}"
JUGO_PORT="${JUGO_PORT:-840}"
NAPOLEON_PORT="${NAPOLEON_PORT:-7700}"
HTTPS_PORT="${HTTPS_PORT:-9443}"
ENABLE_PV_DACH="${ENABLE_PV_DACH:-1}"
ENABLE_CODEANALYST="${ENABLE_CODEANALYST:-1}"
ENABLE_JUGO="${ENABLE_JUGO:-1}"
ENABLE_NAPOLEON="${ENABLE_NAPOLEON:-1}"

echo "[run] container: ${CONTAINER_NAME}"
if [[ "${IMAGE_NAME}" != "${IMAGE_NAME_LOWER}" ]]; then
  echo "[run] note: image name normalized to lowercase: ${IMAGE_NAME_LOWER}"
fi
echo "[run] image: ${IMAGE_NAME_LOWER}"
echo "[run] creds: ${CREDS_SRC} -> ${CREDS_DST}"
echo "[run] OPENAI_API_BASE: ${OPENAI_API_BASE}"
echo "[run] DB_HOST: ${DB_HOST}"
echo "[run] DEFAULT_MODEL: ${DEFAULT_MODEL}"
echo "[run] HTTPS_PORT: ${HTTPS_PORT}"
echo "[run] ENABLE_PV_DACH: ${ENABLE_PV_DACH}"
echo "[run] ENABLE_CODEANALYST: ${ENABLE_CODEANALYST}"
echo "[run] ENABLE_JUGO: ${ENABLE_JUGO}"
echo "[run] ENABLE_NAPOLEON: ${ENABLE_NAPOLEON}"

if [[ ! -f "${CREDS_SRC}" ]]; then
  echo "[run] warning: creds file not found: ${CREDS_SRC}"
fi

podman rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

exec podman run -d \
  --name "${CONTAINER_NAME}" \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  --device /dev/net/tun \
  -v "${CREDS_SRC}:${CREDS_DST}:ro,Z" \
  -e PV_CREDS_FILE="${CREDS_DST}" \
  -e OPENAI_API_BASE="${OPENAI_API_BASE}" \
  -e DB_HOST="${DB_HOST}" \
  -e DEFAULT_MODEL="${DEFAULT_MODEL}" \
  -e PV_DACH_PORT="${PV_DACH_PORT}" \
  -e CODEANALYST_PORT="${CODEANALYST_PORT}" \
  -e JUGO_PORT="${JUGO_PORT}" \
  -e NAPOLEON_PORT="${NAPOLEON_PORT}" \
  -e HTTPS_PORT="${HTTPS_PORT}" \
  -e ENABLE_PV_DACH="${ENABLE_PV_DACH}" \
  -e ENABLE_CODEANALYST="${ENABLE_CODEANALYST}" \
  -e ENABLE_JUGO="${ENABLE_JUGO}" \
  -e ENABLE_NAPOLEON="${ENABLE_NAPOLEON}" \
  "${IMAGE_NAME_LOWER}"
