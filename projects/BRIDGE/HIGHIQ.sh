#!/usr/bin/env bash
# HIGHIQ.sh — Claude Code wrapper for OpenClaw agents
# Usage: HIGHIQ.sh 'your prompt here'
set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: HIGHIQ.sh 'prompt'" >&2
  exit 1
fi

mkdir -p ~/log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> ~/log/HIGHIQ.log

exec claude --print --permission-mode bypassPermissions --model claude-opus-4-6 "$*"
