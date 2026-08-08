#!/bin/bash
set -euo pipefail
# avoid leaking env output into prompt/logs (handle xtrace shells)
_XTRACE_WAS_ON=0
case "$-" in
  *x*) _XTRACE_WAS_ON=1; set +x ;;
esac
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_BASE="${CONFIG_BASE:-$BASE_DIR}"
LOCK_FILE="$BASE_DIR/email_sort.lock"
MAILBOXES=()
if [ "$#" -gt 0 ]; then
  MAILBOXES=("$@")
fi
LOG_DIR="$BASE_DIR/LOGS"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

if [ "${#MAILBOXES[@]}" -eq 0 ]; then
  echo "Usage: $0 <mailbox-name> [mailbox-name ...]" >&2
  exit 1
fi

if [ -f "$LOCK_FILE" ]; then
  echo "[mail_sync] Lock file exists ($LOCK_FILE). Waiting up to 10 minutes..." | tee -a "$LOG_FILE"
  sleep 600
  if [ -f "$LOCK_FILE" ]; then
    echo "[mail_sync] Lock file still present after waiting. Aborting." | tee -a "$LOG_FILE" >&2
    exit 2
  else
    echo "[mail_sync] Lock cleared. Continuing." | tee -a "$LOG_FILE"
  fi
fi

OFFLINEIMAP_BIN=""
if [ -x "/opt/venv/bin/offlineimap" ]; then
  OFFLINEIMAP_BIN="/opt/venv/bin/offlineimap"
elif [ -x "/opt/venv/bin/offlineimap3" ]; then
  OFFLINEIMAP_BIN="/opt/venv/bin/offlineimap3"
elif command -v offlineimap >/dev/null 2>&1; then
  OFFLINEIMAP_BIN="offlineimap"
elif command -v offlineimap3 >/dev/null 2>&1; then
  OFFLINEIMAP_BIN="offlineimap3"
fi

if [ -z "$OFFLINEIMAP_BIN" ]; then
  echo "[mail_sync] offlineimap binary not found (expected offlineimap or offlineimap3)." >&2
  exit 127
fi

for MAILBOX in "${MAILBOXES[@]}"; do
  LOG_FILE="$LOG_DIR/offlineimap-${MAILBOX}-${TIMESTAMP}.log"
  echo "[mail_sync] $(date) – Starting sync for mailbox '$MAILBOX'" | tee -a "$LOG_FILE"
  if (cd "$BASE_DIR" && "$OFFLINEIMAP_BIN" -c "$CONFIG_BASE/offlineimaprc" -o -a "$MAILBOX"); then
    echo "[mail_sync] $(date) – Sync completed for '$MAILBOX'." | tee -a "$LOG_FILE"
  else
    STATUS=$?
    echo "[mail_sync] $(date) – Sync failed for '$MAILBOX' with status $STATUS." | tee -a "$LOG_FILE" >&2
    exit $STATUS
  fi
done

if [ "$_XTRACE_WAS_ON" -eq 1 ]; then set -x; fi
