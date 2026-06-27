#!/bin/bash
# Install LaunchAgent for tianshu-bridge (auto-start on login).
#
# Usage:
#   bash scripts/install-launchagent.sh
#
# After install: bridge starts automatically on next login.
# To start immediately without re-login: launchctl start com.yishu.tianshu-bridge
# To stop: bash scripts/uninstall-launchagent.sh
# To check status: launchctl list | grep tianshu

set -euo pipefail

BRIDGE_DIR="$HOME/Developer/tianshu-integrations"
PLIST_TEMPLATE="$BRIDGE_DIR/scripts/com.yishu.tianshu-bridge.plist.template"
PLIST_DEST="$HOME/Library/LaunchAgents/com.yishu.tianshu-bridge.plist"
CONFIG_DIR="$HOME/.config/tianshu-bridge"
CONFIG_FILE="$CONFIG_DIR/env"

echo "=== Tianshu Bridge LaunchAgent Installer ==="
echo ""

# --- Step 1: Create config file ---
echo "[1/4] Creating config file at $CONFIG_FILE"
mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_FILE" ]; then
    echo "  [skip] Config already exists. Edit manually if needed:"
    echo "    nano $CONFIG_FILE"
else
    # Try to get API key from current env or .zshrc
    API_KEY="${MINIMAX_API_KEY:-}"
    if [ -z "$API_KEY" ]; then
        # Try extracting from .zshrc
        API_KEY=$(grep 'MINIMAX_API_KEY' "$HOME/.zshrc" 2>/dev/null | head -1 | sed 's/.*=//' | tr -d '"' || true)
    fi

    if [ -z "$API_KEY" ]; then
        echo "  [warn] MINIMAX_API_KEY not found in env or .zshrc"
        echo "  Please enter your MiniMax API key (sk-cp-...):"
        read -r API_KEY
    fi

    cat > "$CONFIG_FILE" << EOF
# Tianshu Bridge configuration
# Edit this file to change API key or vault path.
MINIMAX_API_KEY=$API_KEY
OBSIDIAN_VAULT=$HOME/Desktop/知识库/知识库
TIANSHU_BRIDGE_PORT=7733
EOF
    chmod 600 "$CONFIG_FILE"  # user-only read (contains API key)
    echo "  [ok] Config created with API key + default vault path"
fi

# --- Step 2: Generate plist from template ---
echo ""
echo "[2/4] Generating LaunchAgent plist"
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "  [error] Plist template not found: $PLIST_TEMPLATE" >&2
    exit 1
fi

PLIST_CONTENT=$(cat "$PLIST_TEMPLATE")
PLIST_CONTENT="${PLIST_CONTENT//__BRIDGE_DIR__/$BRIDGE_DIR}"
PLIST_CONTENT="${PLIST_CONTENT//__HOME__/$HOME}"

mkdir -p "$(dirname "$PLIST_DEST")"
echo "$PLIST_CONTENT" > "$PLIST_DEST"
echo "  [ok] Plist written to $PLIST_DEST"

# --- Step 3: Unload old version if running ---
echo ""
echo "[3/4] Loading LaunchAgent"
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "  [ok] LaunchAgent loaded"

# --- Step 4: Verify ---
echo ""
echo "[4/4] Verifying"
sleep 2
if launchctl list | grep -q "tianshu"; then
    echo "  [ok] Bridge is running (LaunchAgent managed)"
else
    echo "  [warn] Bridge not yet visible in launchctl list"
    echo "  It may take a few seconds to start. Check logs:"
    echo "    tail -f /tmp/tianshu-bridge.log"
fi

# Try health check
HEALTH=$(curl -sf --max-time 5 http://127.0.0.1:7733/health 2>/dev/null || echo "")
if [ -n "$HEALTH" ]; then
    echo ""
    echo "  ✅ Bridge is healthy!"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo ""
    echo "  ⏳ Bridge still starting up. Check in 5 seconds:"
    echo "    curl http://127.0.0.1:7733/health"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Bridge will auto-start on every login from now on."
echo ""
echo "Commands:"
echo "  Status:  launchctl list | grep tianshu"
echo "  Stop:    bash $BRIDGE_DIR/scripts/uninstall-launchagent.sh"
echo "  Restart: launchctl stop com.yishu.tianshu-bridge && launchctl start com.yishu.tianshu-bridge"
echo "  Logs:    tail -f /tmp/tianshu-bridge.log"
echo "  Config:  nano $CONFIG_FILE"