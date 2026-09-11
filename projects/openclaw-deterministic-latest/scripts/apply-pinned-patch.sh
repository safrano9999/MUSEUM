#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$repo_root/build.conf"

source_dir=${1:?usage: apply-pinned-patch.sh /path/to/openclaw}
actual_sha=$(git -C "$source_dir" rev-parse HEAD)
if [[ "$actual_sha" != "$OPENCLAW_UPSTREAM_SHA" ]]; then
  printf 'upstream SHA mismatch: expected %s, got %s\n' \
    "$OPENCLAW_UPSTREAM_SHA" "$actual_sha" >&2
  exit 1
fi

actual_patch_sha=$(sha256sum "$repo_root/$OPENCLAW_PATCH_FILE" | cut -d' ' -f1)
if [[ "$actual_patch_sha" != "$OPENCLAW_PATCH_SHA256" ]]; then
  printf 'patch SHA256 mismatch: expected %s, got %s\n' \
    "$OPENCLAW_PATCH_SHA256" "$actual_patch_sha" >&2
  exit 1
fi

git -C "$source_dir" apply --check "$repo_root/$OPENCLAW_PATCH_FILE"
git -C "$source_dir" apply "$repo_root/$OPENCLAW_PATCH_FILE"
