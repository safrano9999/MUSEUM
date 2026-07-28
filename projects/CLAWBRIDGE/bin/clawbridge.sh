#!/bin/bash
# clawbridge.sh — unified entry point
# Starts dispatcher.sh + bot_core.py as background jobs.
# If either dies, the whole process exits → systemd (Restart=on-failure) restarts both.

set -euo pipefail

BRIDGE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
VENV="$BRIDGE_DIR/venv"

echo "[clawbridge] starting (PID $$)"
echo "[clawbridge] BRIDGE_DIR=$BRIDGE_DIR"

# Kill any leftover instances
pkill -f "bin/dispatcher.sh" || true
pkill -f "bin/bot_core.py"   || true
sleep 1

# Activate venv if present
if [ -f "$VENV/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
fi

"$BRIDGE_DIR/bin/dispatcher.sh" &
PID_BRIDGE=$!
echo "[clawbridge] dispatcher.sh started (PID $PID_BRIDGE)"

python3 "$BRIDGE_DIR/bin/bot_core.py" &
PID_BOT=$!
echo "[clawbridge] bot_core.py started (PID $PID_BOT)"

# wait -n exits as soon as any child exits (bash 4.3+)
# This ensures systemd restarts the whole unit if either daemon dies
wait -n
echo "[clawbridge] a child process exited — shutting down"
kill "$PID_BRIDGE" "$PID_BOT" || true
wait
