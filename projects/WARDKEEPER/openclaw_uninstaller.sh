#!/usr/bin/env bash
# openclaw_uninstaller.sh — WARDKEEPER Vikunja Uninstallation
# Deregisters agents, optionally removes Vikunja data.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS=(steward inspirator critic operator belief_agent)

echo "🧭 WARDKEEPER Vikunja Uninstaller"
echo "────────────────────────────────────────────────"

# 1. Deregister agents
echo "── Deregistering agents..."
for agent in "${AGENTS[@]}"; do
    if openclaw agents remove "$agent" 2>/dev/null; then
        echo "  ✓ $agent removed"
    else
        echo "  ⚠ $agent not found or already removed"
    fi
done

# 2. Ask about Vikunja data
echo ""
read -rp "Also delete all WARDKEEPER data from Vikunja? (y/N): " delete_vikunja
if [[ "$delete_vikunja" =~ ^[yY]$ ]]; then
    if [ -f "$SCRIPT_DIR/wardkeeper.cfg" ]; then
        echo "── Deleting Vikunja root project and all subprojects..."
        root_id=$(python3 -c "
import configparser
cfg = configparser.ConfigParser()
cfg.read('$SCRIPT_DIR/wardkeeper.cfg')
print(cfg['vikunja'].get('root_id', '0'))
")
        if [ "$root_id" != "0" ]; then
            python3 "$SCRIPT_DIR/wardkeeper.py" delete "$root_id" 2>/dev/null || echo "  ⚠ Could not delete root project"
        fi
    else
        echo "  ⚠ wardkeeper.cfg not found — cannot delete Vikunja data"
    fi
fi

# 3. Clean up config
echo ""
read -rp "Delete wardkeeper.cfg? (y/N): " delete_cfg
if [[ "$delete_cfg" =~ ^[yY]$ ]]; then
    rm -f "$SCRIPT_DIR/wardkeeper.cfg"
    echo "  ✓ wardkeeper.cfg deleted"
fi

# 4. Remove BOOTSTRAP.md artifacts
for agent in "${AGENTS[@]}"; do
    rm -f "$SCRIPT_DIR/workspace/$agent/BOOTSTRAP.md"
done

# 5. Restart gateway
echo ""
echo "── Restarting gateway..."
openclaw gateway restart 2>/dev/null || echo "  ⚠ Gateway restart failed"

echo ""
echo "────────────────────────────────────────────────"
echo "✅ WARDKEEPER Vikunja uninstalled."
echo ""
