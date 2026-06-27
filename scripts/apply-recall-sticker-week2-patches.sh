#!/usr/bin/env bash
# Apply Recall Sticker Week 2 patches.
#
# Week 2 adds:
#   - 3 new lib/ files: bridge-client.js, obsidian-exporter.js, storage-collector.js
#   - sidepanel.html + sidepanel.js modifications (sync button + status)
#
# Run from the tianshu-integrations project root.

set -euo pipefail

RECALL_STICKER_DIR="${RECALL_STICKER_DIR:-$HOME/Documents/trae_projects/recall-sticker/Recall-Sticker}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="$SCRIPT_DIR/../patches"

if [ ! -d "$RECALL_STICKER_DIR" ]; then
    echo "ERROR: Recall Sticker dir not found: $RECALL_STICKER_DIR" >&2
    exit 1
fi

cd "$RECALL_STICKER_DIR"

echo "Applying Recall Sticker Week 2 patches..."
echo "  Target dir: $RECALL_STICKER_DIR"

# Patch 3: sidepanel v2 (modifies existing files)
if grep -q "id=\"sync-to-bridge-btn\"" sidepanel.html; then
    echo "  [skip] sidepanel.html already patched (sync button exists)"
else
    patch sidepanel.html -i "$PATCHES_DIR/recall-sticker-sidepanel-v2.patch" < /dev/null
    echo "  [ok]   sidepanel.html + sidepanel.js patched (sync button + status)"
fi

# New lib/ files
mkdir -p lib
for f in bridge-client.js obsidian-exporter.js storage-collector.js; do
    if [ -f "lib/$f" ]; then
        echo "  [skip] lib/$f already exists"
    else
        cp "$PATCHES_DIR/lib-files/$f" "lib/$f"
        echo "  [ok]   lib/$f created"
    fi
done

echo ""
echo "Week 2 patches applied. Reload Recall Sticker in chrome://extensions."