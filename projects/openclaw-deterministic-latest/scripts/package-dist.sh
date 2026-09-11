#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$repo_root/build.conf"

source_dir=${1:?usage: package-dist.sh /path/to/patched-openclaw [output-dir]}
output_dir=${2:-"$repo_root/artifacts"}
if [[ ! -d "$source_dir/dist" ]]; then
  printf 'missing build output: %s/dist\n' "$source_dir" >&2
  exit 1
fi

mkdir -p "$output_dir"
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
  -cf - -C "$source_dir" dist |
  gzip -n > "$output_dir/$OPENCLAW_DETERMINISTIC_ASSET"
(
  cd "$output_dir"
  sha256sum "$OPENCLAW_DETERMINISTIC_ASSET" \
    > "$OPENCLAW_DETERMINISTIC_ASSET.sha256"
)
