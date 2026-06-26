"""Tests for bridge CLI."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_vault_must_exist(tmp_path):
    """CLI exits 1 if vault path doesn't exist."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tianshu_integrations.bridge.cli",
            "--vault",
            str(tmp_path / "nonexistent"),
            "--port",
            "0",  # any port — but we exit before binding
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "MINIMAX_API_KEY": "sk-test"},
    )
    assert result.returncode == 1
    assert "vault 路径不存在" in result.stderr


def test_cli_vault_must_be_writable(tmp_path):
    """CLI exits 1 if vault path is not writable."""
    vault = tmp_path / "readonly"
    vault.mkdir()
    os.chmod(vault, 0o555)  # read+exec only
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tianshu_integrations.bridge.cli",
                "--vault",
                str(vault),
                "--port",
                "0",
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "MINIMAX_API_KEY": "sk-test"},
        )
        assert result.returncode == 1
        assert "无写权限" in result.stderr
    finally:
        os.chmod(vault, 0o755)


def test_cli_default_vault_is_obsidian(tmp_path, monkeypatch):
    """CLI defaults to ~/Desktop/知识库/知识库 if no env / --vault."""
    from tianshu_integrations.bridge.cli import DEFAULT_VAULT

    assert DEFAULT_VAULT == os.path.expanduser("~/Desktop/知识库/知识库")


def test_cli_warns_when_no_minimax_key(tmp_path, monkeypatch, capsys):
    """CLI prints warning when MINIMAX_API_KEY is missing (but doesn't fail)."""
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    # Skip uvicorn server start
    monkeypatch.setenv("TIANSHU_BRIDGE_SKIP_UVICORN", "1")
    # Reset sys.argv so argparse doesn't pick up pytest args
    monkeypatch.setattr("sys.argv", ["tianshu-bridge"])

    from tianshu_integrations.bridge.cli import main
    main()
    captured = capsys.readouterr()
    assert "MINIMAX_API_KEY 未设置" in captured.err