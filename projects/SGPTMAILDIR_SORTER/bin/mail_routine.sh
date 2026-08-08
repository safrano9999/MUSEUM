#!/bin/bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_BASE="${CONFIG_BASE:-$BASE_DIR}"
LOCK_FILE="$BASE_DIR/email_sort.lock"
LOG_FILE="$BASE_DIR/LOGS/mail-routine.log"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <mailbox-name> [mailbox-name ...]" >&2
  exit 1
fi
MAILBOXES=("$@")

mkdir -p "$BASE_DIR/LOGS"

log() { echo "[mail_routine] $(date) – $*" | tee -a "$LOG_FILE"; }

if [ -f "$LOCK_FILE" ]; then
  log "lock present, exiting"
  exit 0
fi

log "start"
( cd "$BASE_DIR" && "$BASE_DIR/bin/mail_sync.sh" "${MAILBOXES[@]}" ) 2>&1 | tee -a "$LOG_FILE"
( cd "$BASE_DIR" && "$BASE_DIR/bin/email_sort.sh" --no-offlineimap "${MAILBOXES[@]}" ) 2>&1 | tee -a "$LOG_FILE"
( cd "$BASE_DIR" && "$BASE_DIR/bin/mail_sync.sh" "${MAILBOXES[@]}" ) 2>&1 | tee -a "$LOG_FILE"
log "done"
