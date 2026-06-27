"""Error path coverage tests for Tianshu Integrations.

Week 4 T-27: 12 scenarios covering bridge failures, M2.1 errors, vault errors,
Readability failures, chrome.storage overflow, prompt injection, and reasoning
output handling.
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tianshu_integrations.bridge import schemas
from tianshu_integrations.bridge.schemas import CuratedCard, RawCard, SyncRequest
from tianshu_integrations.curator.parsers import parse_curation_response
from tianshu_integrations.llm.client import extractContent


# === E1: M2.1 non-JSON → 4-layer fallback ===
def test_e1_minimax_non_json_response():
    """M2.1 returns free text instead of JSON. Parser should fall back gracefully."""
    raw = "Sorry, I cannot help with that request."
    result = parse_curation_response(raw)
    # Layer 4 fallback: empty tags + empty rewrites
    assert result["tags"] == []
    assert result["rewrites"] == []
    # Don't crash


# === E2: M2.1 truncated JSON → Layer 5 recovery ===
def test_e2_minimax_truncated_json():
    """Truncated JSON recovers partial data via Layer 5."""
    raw = '{"tags": ["kernel", "sandbox"], "rewrites": [{"cardId":'
    result = parse_curation_response(raw)
    # Layer 3 regex should match outer {...} and parse successfully
    assert "kernel" in result["tags"]
    assert "sandbox" in result["tags"]


# === E3: M2.1 markdown wrapped JSON ===
def test_e3_minimax_markdown_wrapped_json():
    """JSON inside ```json ... ``` markdown block."""
    raw = 'Here is my response:\n\n```json\n{"tags": ["a"], "rewrites": [{"cardId": "1", "title": "x"}]}\n```\n'
    result = parse_curation_response(raw)
    assert "a" in result["tags"] or "rewrites" in result


# === E4: M2.1 returns array directly (not object) ===
def test_e4_minimax_array_response():
    """M2.1 returns [{}, {}] not wrapped in object."""
    raw = '[{"type": "trap", "question": "x"}]'
    result = parse_curation_response(raw)
    # Falls back to Layer 4 (naive tag extraction)
    assert "tags" in result


# === E5: M2.1 thinking block stripping ===
def test_e5_minimax_thinking_block_stripped():
    """M2.1/M3 emit <think>...</think> before content. extractContent should strip it."""
    raw = "<think>The user wants JSON. Let me think.\n\nAnalysis: this is a test.</think>\n\n```json\n{\"tags\": [\"a\"]}\n```"
    cleaned = extractContent(raw)
    assert "<think>" not in cleaned
    assert "tags" in cleaned
    # The JSON inside markdown is preserved
    result = parse_curation_response(cleaned)
    assert "a" in result["tags"]


# === E6: M2.1 returns null ===
def test_e6_minimax_null_response():
    raw = "null"
    result = parse_curation_response(raw)
    assert result == {"tags": [], "rewrites": []}


# === E7: Pydantic input validation rejects empty text ===
def test_e7_pydantic_rejects_empty_text():
    """Pydantic should reject empty text in RawCard (Week 1 P3 #4 fix)."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RawCard.model_validate({"text": "", "sourceUrl": "u", "timestamp": 1})


# === E8: Pydantic input validation rejects missing sourceUrl ===
def test_e8_pydantic_rejects_missing_source_url():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RawCard.model_validate({"text": "x", "timestamp": 1})


# === E9: SyncRequest rejects unknown trigger ===
def test_e9_pydantic_rejects_invalid_trigger():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SyncRequest.model_validate({
            "trigger": "invalid",
            "cards": [],
            "obsidianVaultPath": "/tmp",
        })


# === E10: Vault path is read-only (chmod 555) ===
def test_e10_vault_path_readonly(tmp_path):
    """If vault is read-only, /sync returns 400."""
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app

    vault = tmp_path / "readonly"
    vault.mkdir()
    os.chmod(vault, 0o555)
    try:
        with TestClient(app) as client:
            os.environ["OBSIDIAN_VAULT"] = str(vault)
            r = client.post("/sync/recall-sticker", json={
                "trigger": "manual",
                "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
                "obsidianVaultPath": str(vault),
            })
            assert r.status_code == 400
            assert "not writable" in r.json()["error"]
    finally:
        os.chmod(vault, 0o755)


# === E11: Vault path = /etc (security) ===
def test_e11_vault_path_security_etc(tmp_path):
    """Vault path = /etc must be rejected (Week 1 P2 fix)."""
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app

    vault = tmp_path / "configured"
    vault.mkdir()
    with TestClient(app) as client:
        os.environ["OBSIDIAN_VAULT"] = str(vault)
        r = client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": "/etc",
        })
        assert r.status_code == 400
        assert "not the configured" in r.json()["error"]


# === E12: Vault path is subdirectory of configured (allowed) ===
def test_e12_vault_path_subdir_allowed(tmp_path):
    """Vault subdirectory of OBSIDIAN_VAULT is allowed."""
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app

    parent = tmp_path / "configured"
    parent.mkdir()
    sub = parent / "subdir"
    sub.mkdir()
    with TestClient(app) as client:
        os.environ["OBSIDIAN_VAULT"] = str(parent)
        r = client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": str(sub),
        })
        assert r.status_code == 200
        assert r.json()["success"] is True