#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-localhost/citadelprivate:latest}"
BUILD_CONTEXT="${BUILD_CONTEXT:-/home/openclaw/safrano9999}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-/home/openclaw/safrano9999/CITADEL/PERSONAL/Dockerfile}"
IMAGE_NAME_LOWER="${IMAGE_NAME,,}"

if [[ "${IMAGE_NAME}" != "${IMAGE_NAME_LOWER}" ]]; then
  echo "[build] note: image name normalized to lowercase: ${IMAGE_NAME_LOWER}"
fi

echo "[build] image: ${IMAGE_NAME_LOWER}"
echo "[build] dockerfile: ${DOCKERFILE_PATH}"
echo "[build] context: ${BUILD_CONTEXT}"

exec podman build \
  -f "${DOCKERFILE_PATH}" \
  -t "${IMAGE_NAME_LOWER}" \
  "${BUILD_CONTEXT}"
