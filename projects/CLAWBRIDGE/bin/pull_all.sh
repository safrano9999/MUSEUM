#!/bin/bash
# pull_all.sh — pull every git repo in ~/safrano9999/, log diffs only
# Never fails hard: each repo is attempted regardless of prior errors.
# Exit 0 always.

BASE="$HOME/safrano9999"
LOG_DIR="$(dirname "$(realpath "$0")")/../logs"
LOG_FILE="$LOG_DIR/OPENCLAW.log"

mkdir -p "$LOG_DIR"

log() {
    printf '[%s] [pull_all] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

errors=0

for dir in "$BASE"/*/; do
    [ -d "$dir/.git" ] || continue
    name=$(basename "$dir")

    before=$(git -C "$dir" rev-parse HEAD 2>/dev/null) || { log "[$name] ERROR: could not get HEAD"; errors=$((errors+1)); continue; }

    if git -C "$dir" pull 2>&1 | tail -1 | grep -q "Already up to date"; then
        log "[$name] up to date"
    else
        after=$(git -C "$dir" rev-parse HEAD 2>/dev/null) || after=""
        if [ -n "$after" ] && [ "$before" != "$after" ]; then
            diff=$(git -C "$dir" log --oneline "$before..$after" 2>/dev/null || echo "(diff unavailable)")
            log "[$name] UPDATED: $diff"
        else
            log "[$name] up to date"
        fi
    fi
done

exit 0
