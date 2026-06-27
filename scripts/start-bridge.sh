#!/bin/bash
# tianshu-bridge launcher wrapper
# Sourced by LaunchAgent OR can be run directly from terminal.
# Reads env from ~/.config/tianshu-bridge/env then starts uvicorn.

set -euo pipefail

# --- Config ---
BRIDGE_DIR="$HOME/Developer/tianshu-integrations"
VENV_PYTHON="$BRIDGE_DIR/.venv/bin/python"
CONFIG_FILE="$HOME/.config/tianshu-bridge/env"
PORT="${TIANSHU_BRIDGE_PORT:-7733}"
VAULT="${OBSIDIAN_VAULT:-$HOME/Desktop/知识库/知识库}"

# --- Load config file if exists (overrides defaults) ---
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
fi

# --- Validate ---
if [ ! -f "$VENV_PYTHON" ]; then
  echo "ERROR: Python venv not found at $VENV_PYTHON" >&2
  echo "Run: cd $BRIDGE_DIR && uv venv && uv pip install -e .[dev]" >&2
  exit 1
fi

if [ -z "${MINIMAX_API_KEY:-}" ]; then
  echo "ERROR: MINIMAX_API_KEY not set" >&2
  echo "Add it to $CONFIG_FILE:" >&2
  echo "  MINIMAX_API_KEY=sk-cp-..." >&2
  exit 1
fi

if [ ! -d "$VAULT" ]; then
  echo "ERROR: Vault not found: $VAULT" >&2
  echo "Set OBSIDIAN_VAULT in $CONFIG_FILE:" >&2
  echo "  OBSIDIAN_VAULT=/path/to/vault" >&2
  exit 1
fi

export MINIMAX_API_KEY
export OBSIDIAN_VAULT="$VAULT"

# --- Start bridge ---
exec "$VENV_PYTHON" -m tianshu_integrations.bridge.cli --port "$PORT" --vault "$VAULT"