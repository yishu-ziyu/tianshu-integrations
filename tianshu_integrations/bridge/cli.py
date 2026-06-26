"""CLI entry point for tianshu-bridge.

Usage:
    tianshu-bridge --port 7733 --vault /path/to/vault

Required:
- OBSIDIAN_VAULT env or --vault arg (must exist + be writable)
Optional:
- MINIMAX_API_KEY env (warns if missing; runs in mock mode for testing)
"""

import argparse
import os
import sys


DEFAULT_VAULT = os.path.expanduser("~/Desktop/知识库/知识库")
DEFAULT_PORT = 7733


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for tianshu-bridge.

    Returns parsed args with vault (str path), port (int), host (str).
    """
    parser = argparse.ArgumentParser(
        prog="tianshu-bridge",
        description="Tianshu Integrations Bridge — connect Recall Sticker / Deep Reader with Obsidian Vault",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--vault",
        type=os.path.abspath,
        default=None,
        help=f"path to Obsidian Vault (default: $OBSIDIAN_VAULT or {DEFAULT_VAULT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="host to bind (default: 127.0.0.1 — do not expose publicly)",
    )
    return parser.parse_args()


def validate_vault(vault: str) -> None:
    """Validate vault path exists and is writable. Exits on failure."""
    from pathlib import Path

    if not Path(vault).is_dir():
        print(f"ERROR: vault 路径不存在: {vault}", file=sys.stderr)
        sys.exit(1)
    if not os.access(vault, os.W_OK):
        print(f"ERROR: vault 路径无写权限: {vault}", file=sys.stderr)
        sys.exit(1)


def check_minimax_key() -> None:
    """Warn if MINIMAX_API_KEY is not set."""
    if not os.environ.get("MINIMAX_API_KEY"):
        print(
            "WARN: MINIMAX_API_KEY 未设置,bridge 将在 mock 模式下运行",
            file=sys.stderr,
        )


def main() -> None:
    args = parse_args()

    # Resolve vault: CLI > env > default
    vault = args.vault or os.environ.get("OBSIDIAN_VAULT") or DEFAULT_VAULT

    # Validate vault BEFORE setting env / starting server
    validate_vault(vault)

    # Set env so server.py can read it
    os.environ["OBSIDIAN_VAULT"] = vault

    # Warn about missing M2.1 key
    check_minimax_key()

    # Start uvicorn (only if not in test mode)
    if os.environ.get("TIANSHU_BRIDGE_SKIP_UVICORN"):
        print(f"Vault validated: {vault}")
        print("TIANSHU_BRIDGE_SKIP_UVICORN set — not starting server")
        return

    import uvicorn

    print(f"Starting tianshu-bridge on {args.host}:{args.port}")
    print(f"  Vault: {vault}")
    print(f"  M2.1:  {'configured' if os.environ.get('MINIMAX_API_KEY') else 'MOCK mode'}")

    uvicorn.run(
        "tianshu_integrations.bridge.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()