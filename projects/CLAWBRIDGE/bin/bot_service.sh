#!/bin/bash
BRIDGE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
VENV="$BRIDGE_DIR/venv"

if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
fi

pkill -f "bin/bot_core.py" || true
sleep 1

exec python3 "$BRIDGE_DIR/bin/bot_core.py"
