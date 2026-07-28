#!/bin/bash
set -euo pipefail

ROOTFS_URL="https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64-root.tar.xz"
ROOTFS_FILE="/tmp/ubuntu-noble-rootfs.tar.xz"
BASE_IMAGE="localhost/ubuntu-noble-base:24.04"
FINAL_IMAGE="mattermost-deb:latest"

echo "=== Step 1: Download Ubuntu 24.04 rootfs from Canonical ==="
if [ ! -f "$ROOTFS_FILE" ]; then
    curl -fSL -o "$ROOTFS_FILE" "$ROOTFS_URL"
    echo "Downloaded: $(du -h "$ROOTFS_FILE" | cut -f1)"
else
    echo "Already cached: $ROOTFS_FILE"
fi

echo ""
echo "=== Step 2: Import as Podman base image ==="
podman rmi "$BASE_IMAGE" 2>/dev/null || true
podman import "$ROOTFS_FILE" "$BASE_IMAGE"
echo "Base image: $BASE_IMAGE"

echo ""
echo "=== Step 3: Build Mattermost image ==="
podman build -t "$FINAL_IMAGE" .

echo ""
echo "=== Done ==="
podman images | grep -E "mattermost-deb|ubuntu-noble"
