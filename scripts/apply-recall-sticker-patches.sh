#!/usr/bin/env bash
# Apply Recall Sticker patches for tianshu-integrations.
#
# Required because we don't directly modify the Recall-Sticker git repo.
# Run from the tianshu-integrations project root.

set -euo pipefail

RECALL_STICKER_DIR="${RECALL_STICKER_DIR:-$HOME/Documents/trae_projects/recall-sticker/Recall-Sticker}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$RECALL_STICKER_DIR" ]; then
    echo "ERROR: Recall Sticker dir not found: $RECALL_STICKER_DIR" >&2
    echo "Set RECALL_STICKER_DIR env var to override." >&2
    exit 1
fi

cd "$RECALL_STICKER_DIR"

echo "Applying Recall Sticker patches..."
echo "  Target dir: $RECALL_STICKER_DIR"

# Patch 1: manifest.json (add host_permissions + downloads)
if grep -q "host_permissions" manifest.json; then
    echo "  [skip] manifest.json already patched"
else
    patch manifest.json -i "$SCRIPT_DIR/../patches/recall-sticker-manifest.patch" < /dev/null
    echo "  [ok]   manifest.json patched (host_permissions + downloads)"
fi

# Patch 2: sidepanel.js (STORAGE_KEY_BLACKLIST)
if grep -q "STORAGE_KEY_BLACKLIST" sidepanel.js; then
    echo "  [skip] sidepanel.js already patched"
else
    patch sidepanel.js -i "$SCRIPT_DIR/../patches/recall-sticker-sidepanel-blacklist.patch" < /dev/null
    echo "  [ok]   sidepanel.js patched (STORAGE_KEY_BLACKLIST)"
fi

echo ""
echo "Done! Reload Recall Sticker extension in chrome://extensions."