#!/bin/bash
set -euo pipefail

ROOTFS_URL="https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64-root.tar.xz"
ROOTFS_FILE="/tmp/ubuntu-noble-rootfs.tar.xz"
BASE_IMAGE="localhost/ubuntu-noble-base:24.04"
FINAL_IMAGE="litellm-ubuntu:latest"

echo "=== Step 1: Ensure Ubuntu 24.04 base image ==="
if podman image exists "$BASE_IMAGE" 2>/dev/null; then
    echo "Base image already exists: $BASE_IMAGE"
else
    if [ ! -f "$ROOTFS_FILE" ]; then
        curl -fSL -o "$ROOTFS_FILE" "$ROOTFS_URL"
        echo "Downloaded: $(du -h "$ROOTFS_FILE" | cut -f1)"
    else
        echo "Already cached: $ROOTFS_FILE"
    fi
    podman import "$ROOTFS_FILE" "$BASE_IMAGE"
    echo "Imported base image: $BASE_IMAGE"
fi

echo ""
echo "=== Step 2: Build LiteLLM image ==="
podman build -t "$FINAL_IMAGE" .

echo ""
echo "=== Step 3: Setup PostgreSQL database ==="
echo "Run on your PostgreSQL host:"
echo "  sudo -u postgres createuser litellm"
echo "  sudo -u postgres createdb -O litellm litellm"
echo "  sudo -u postgres psql -c \"ALTER USER litellm PASSWORD 'litellm_password';\""

echo ""
echo "=== Step 4: Deploy ==="
echo "  cp litellm.container ~/.config/containers/systemd/"
echo "  systemctl --user daemon-reload"
echo "  systemctl --user start litellm"

echo ""
echo "=== Done ==="
podman images | grep -E "litellm-ubuntu|ubuntu-noble"
echo ""
echo "UI: http://localhost:4000/ui"
echo "API: http://localhost:4000"
