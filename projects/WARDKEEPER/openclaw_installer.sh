#!/usr/bin/env bash
# openclaw_installer.sh — WARDKEEPER Vikunja Installation
# Registers all 5 agents with workspaces inside the repo, initializes Vikunja.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_BASE="$SCRIPT_DIR/workspace"
AGENTS=(steward inspirator critic operator belief_agent)

echo "🧭 WARDKEEPER Vikunja Installation"
echo "────────────────────────────────────────────────"

# 0. Check wardkeeper.cfg
if [ ! -f "$SCRIPT_DIR/wardkeeper.cfg" ]; then
    echo "❌ wardkeeper.cfg not found."
    echo "   Create it with your Vikunja API token:"
    echo ""
    echo "   [vikunja]"
    echo "   url     = https://127.0.0.1:460"
    echo "   token   = YOUR_TOKEN_HERE"
    echo "   root_id = 0"
    exit 1
fi

# 1. Register agents with workspaces inside the repo
echo "── Registering agents..."
for agent in "${AGENTS[@]}"; do
    if openclaw agents add "$agent" --workspace "$WORKSPACE_BASE/$agent"; then
        echo "  ✓ $agent registered (workspace: $WORKSPACE_BASE/$agent)"
    else
        echo "  ⚠ $agent could not be registered (already exists?)"
    fi
done

# 2. Remove BOOTSTRAP.md — forces OpenClaw to use SOUL.md
echo ""
echo "── Removing BOOTSTRAP.md from all workspaces..."
for agent in "${AGENTS[@]}"; do
    rm -f "$WORKSPACE_BASE/$agent/BOOTSTRAP.md"
    echo "  ✓ $agent/BOOTSTRAP.md removed"
done

# 3. Initialize Vikunja (create root project + 5 subprojects)
echo ""
echo "── Initializing Vikunja..."
python3 "$SCRIPT_DIR/wardkeeper.py" init

# 4. Create first project
echo ""
read -rp "Name of your first project: " project_name
if [[ -n "$project_name" ]]; then
    echo "── Creating project..."
    python3 "$SCRIPT_DIR/wardkeeper.py" add project --name "$project_name"
else
    echo "  ⚠ No project name given — add later with: python3 wardkeeper.py add project --name <name>"
fi

# 5. Restart gateway
echo ""
echo "── Restarting gateway..."
openclaw gateway restart
echo "  ✓ Gateway restarted"

# Remove BOOTSTRAP.md again — OpenClaw may regenerate them on restart
echo ""
echo "── Removing BOOTSTRAP.md again (post-restart)..."
for agent in "${AGENTS[@]}"; do
    rm -f "$WORKSPACE_BASE/$agent/BOOTSTRAP.md"
    echo "  ✓ $agent/BOOTSTRAP.md removed"
done

echo ""
echo "────────────────────────────────────────────────"
echo "✅ WARDKEEPER Vikunja installed."
echo ""
echo "Start a session:"
echo "  openclaw tui --session agent:steward:main"
echo ""
