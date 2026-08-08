#!/bin/bash
# smoketest.sh — appends a timestamped line to smoketest.log
# Verifies that CLAWBRIDGE inotify dispatch, policy check, and script execution work.

LOG="$(dirname "$(realpath "$0")")/../smoketest.log"
echo "$(date -Iseconds) smoketest OK" >> "$LOG"
echo "Logged to: $LOG"
