"""Shared fixtures for tianshu-bridge tests."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def vault_path(tmp_path: Path) -> str:
    """Return a temporary vault path for tests."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    return str(vault)


@pytest.fixture
def no_minimax_key(monkeypatch):
    """Ensure MINIMAX_API_KEY is unset for tests that use mock client."""
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)


@pytest.fixture
def fake_minimax_key(monkeypatch):
    """Set a fake MINIMAX_API_KEY for tests that need it present."""
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test-fake-key")


@pytest.fixture
def vault_env(monkeypatch, vault_path):
    """Set OBSIDIAN_VAULT env to a temp vault."""
    monkeypatch.setenv("OBSIDIAN_VAULT", vault_path)
    return vault_path


@pytest.fixture(autouse=True)
def clear_app_state():
    """Reset FastAPI app state between tests."""
    from tianshu_integrations.bridge import server

    # Reset START_TIME so uptime is small per test
    server.START_TIME = 9999999999.0  # far future → uptime will be negative-ish but ok
    yield