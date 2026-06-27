#!/bin/bash
# Uninstall LaunchAgent for tianshu-bridge.
# Stops the bridge process and removes the plist.
# Config file (~/.config/tianshu-bridge/env) is kept for re-install.

set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.yishu.tianshu-bridge.plist"

echo "=== Uninstalling Tianshu Bridge LaunchAgent ==="

if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "[ok] LaunchAgent removed. Bridge will not auto-start on next login."
else
    echo "[skip] No LaunchAgent found at $PLIST"
fi

# Kill any running bridge process
PIDS=$(pgrep -f "tianshu_integrations.bridge.cli" 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo "[ok] Stopping running bridge process (PID: $PIDS)"
    echo "$PIDS" | xargs kill 2>/dev/null || true
    sleep 1
    # Force kill if still running
    PIDS=$(pgrep -f "tianshu_integrations.bridge.cli" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
    fi
    echo "[ok] Bridge stopped."
else
    echo "[skip] No running bridge process found."
fi

echo ""
echo "Config file kept at ~/.config/tianshu-bridge/env"
echo "To re-install: bash ~/Developer/tianshu-integrations/scripts/install-launchagent.sh"