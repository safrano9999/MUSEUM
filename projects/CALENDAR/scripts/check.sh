#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

node --check "$PLUGIN_ROOT/index.js"
PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/calendar-pycache" python3 -m py_compile \
  "$PLUGIN_ROOT/calendar_fetch.py" \
  "$PLUGIN_ROOT/CALENDAR_init.sh"
