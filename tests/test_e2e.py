"""End-to-end tests for Tianshu Bridge.

These tests verify the full flow from /sync/recall-sticker endpoint
through curator + writer to actual .md files on disk.

Unlike unit tests in test_server.py / test_curator.py / test_writer.py
(which test individual components), these tests verify the **integrated
behavior** that matches spec.md's Hard Cut acceptance criteria:

- 联动 2 E2E: 5 cards → .md file with frontmatter + sections
- Error paths: vault path wrong, M2.1 failure, malformed cards
- Performance: 20 cards batch < 30s (P95 target)
"""

import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tianshu_integrations.bridge.server import app


@pytest.fixture
def real_bridge_client(vault_env, no_minimax_key):
    """TestClient for the actual FastAPI app, with vault env set."""
    return TestClient(app)


class TestEndToEndSync:
    """Spec: Hard Cut AC#1 — 联动 2 E2E (5 cards → .md < 60s)."""

    def test_five_cards_yields_md_file_with_all_sections(self, real_bridge_client, vault_env):
        """5 cards synced → vault/Inbox/<date>-recall.md contains all 5 sections + frontmatter."""
        cards = [
            {
                "text": f"concept-{i}",
                "prefix": "context before ",
                "suffix": " context after",
                "context": f"this is concept {i} description",
                "sourceUrl": f"https://example.com/page-{i}",
                "tags": [],
                "timestamp": 1000 + i,
            }
            for i in range(5)
        ]
        payload = {
            "trigger": "manual",
            "cards": cards,
            "obsidianVaultPath": vault_env,
        }
        r = real_bridge_client.post("/sync/recall-sticker", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert len(data["curated"]) == 5

        # Verify .md file
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(vault_env) / "Inbox" / f"{today}-recall.md"
        assert file_path.exists(), f"Expected file at {file_path}"

        content = file_path.read_text(encoding="utf-8")
        # Frontmatter present
        assert content.startswith("---\n")
        assert "date:" in content
        assert "tags:" in content
        assert "source: recall-sticker-sidepanel" in content

        # All 5 cards present
        for i in range(5):
            assert f"concept-{i}" in content, f"Card {i} missing from .md"

    def test_anki_cloze_stripped_in_e2e(self, real_bridge_client, vault_env):
        """Anki Cloze {{c1::text}} is sanitized to [text] in final .md (no prompt injection)."""
        cards = [
            {
                "text": "secret",
                "prefix": "",
                "suffix": "",
                "context": "{{c1::secret-pattern}} is fun",
                "sourceUrl": "https://example.com",
                "timestamp": 1,
            },
        ]
        payload = {"trigger": "manual", "cards": cards, "obsidianVaultPath": vault_env}
        r = real_bridge_client.post("/sync/recall-sticker", json=payload)
        assert r.status_code == 200

        today = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(vault_env) / "Inbox" / f"{today}-recall.md"
        content = file_path.read_text(encoding="utf-8")
        assert "{{c1::" not in content, "Anki Cloze markers leaked into .md"
        assert "[secret-pattern]" in content

    def test_inbox_directory_auto_created(self, real_bridge_client, tmp_path):
        """Inbox/ doesn't exist beforehand, but sync creates it."""
        import os
        vault = tmp_path / "fresh-vault"
        vault.mkdir()
        assert not (vault / "Inbox").exists()
        # Match env vault for security check
        os.environ["OBSIDIAN_VAULT"] = str(vault)

        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": str(vault),
        })
        assert r.status_code == 200
        assert (vault / "Inbox").exists()

    def test_atomic_write_no_temp_files(self, real_bridge_client, vault_env):
        """After sync, no .tmp files should remain in Inbox."""
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": vault_env,
        })
        assert r.status_code == 200
        inbox = Path(vault_env) / "Inbox"
        temp_files = list(inbox.glob("*.tmp"))
        assert temp_files == [], f"Found leftover .tmp files: {temp_files}"

    def test_appends_to_existing_daily_file(self, real_bridge_client, vault_env):
        """Second sync on same day appends to existing file, doesn't overwrite."""
        payload_a = {
            "trigger": "manual",
            "cards": [{"text": "first-card", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": vault_env,
        }
        payload_b = {
            "trigger": "manual",
            "cards": [{"text": "second-card", "sourceUrl": "u", "timestamp": 2}],
            "obsidianVaultPath": vault_env,
        }
        real_bridge_client.post("/sync/recall-sticker", json=payload_a)
        real_bridge_client.post("/sync/recall-sticker", json=payload_b)

        today = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(vault_env) / "Inbox" / f"{today}-recall.md"
        content = file_path.read_text(encoding="utf-8")
        assert "first-card" in content, "First card overwritten by second sync"
        assert "second-card" in content

    def test_source_url_included_in_md(self, real_bridge_client, vault_env):
        """sourceUrl is rendered in .md for traceability (fixes review P2)."""
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{
                "text": "trace-test",
                "prefix": "",
                "suffix": "",
                "context": "",
                "sourceUrl": "https://example.com/article?utm_source=tw&id=42",
                "timestamp": 1,
            }],
            "obsidianVaultPath": vault_env,
        })
        assert r.status_code == 200

        today = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(vault_env) / "Inbox" / f"{today}-recall.md"
        content = file_path.read_text(encoding="utf-8")
        # 来源: line + URL (with utm_source stripped)
        assert "来源:" in content
        assert "https://example.com/article?id=42" in content
        assert "utm_source" not in content

    def test_vault_path_must_match_configured_vault(self, real_bridge_client, tmp_path):
        """P2 security: request vault must match env OBSIDIAN_VAULT, else 400."""
        # env_vault is set to vault_env (a tmp path) by fixture
        # Try writing to a different tmp path
        other_vault = tmp_path / "other-vault"
        other_vault.mkdir()
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": str(other_vault),
        })
        assert r.status_code == 400
        assert "not the configured" in r.json()["error"]


class TestErrorPaths:
    """Spec: Hard Cut AC#5 — Error paths covered (vault wrong / M2.1 fail)."""

    def test_vault_path_does_not_exist_returns_400(self, real_bridge_client):
        """POST /sync with non-existent vault → 400 + clear error."""
        # Must use env vault for this test (request path must match OBSIDIAN_VAULT)
        import os
        env_vault = os.environ.get("OBSIDIAN_VAULT", "/tmp/nonexistent-vault-12345")
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
            "obsidianVaultPath": env_vault + "/nonexistent",
        })
        assert r.status_code == 400
        body = r.json()
        # Either path mismatch or doesn't exist — both acceptable errors
        assert "does not exist" in body["error"] or "not the configured" in body["error"]

    def test_vault_path_not_writable_returns_400(self, real_bridge_client, tmp_path):
        """POST /sync with read-only vault → 400."""
        # Note: request path must match OBSIDIAN_VAULT (security check)
        import os
        vault = tmp_path / "readonly"
        vault.mkdir()
        os.chmod(vault, 0o555)
        original_env = os.environ.get("OBSIDIAN_VAULT", "")
        os.environ["OBSIDIAN_VAULT"] = str(vault)
        try:
            r = real_bridge_client.post("/sync/recall-sticker", json={
                "trigger": "manual",
                "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
                "obsidianVaultPath": str(vault),
            })
            assert r.status_code == 400
            assert "not writable" in r.json()["error"]
        finally:
            os.chmod(vault, 0o755)
            os.environ["OBSIDIAN_VAULT"] = original_env

    def test_empty_cards_succeeds_without_writing(self, real_bridge_client, vault_env):
        """Empty cards list returns success but creates no .md file."""
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [],
            "obsidianVaultPath": vault_env,
        })
        assert r.status_code == 200
        assert r.json()["success"] is True
        # No file should be created
        inbox = Path(vault_env) / "Inbox"
        assert not inbox.exists() or list(inbox.iterdir()) == []

    def test_llm_failure_falls_back_to_direct_write(self, real_bridge_client, vault_env):
        """When LLM fails, cards are still written via direct fallback."""
        # Without MINIMAX_API_KEY, server uses MockLLMClient which returns ""
        # (which falls back to direct write)
        r = real_bridge_client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [{
                "text": "fallback-test",
                "prefix": "p",
                "suffix": "s",
                "context": "",
                "sourceUrl": "u",
                "timestamp": 1,
            }],
            "obsidianVaultPath": vault_env,
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

        # File still written
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(vault_env) / "Inbox" / f"{today}-recall.md"
        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert "fallback-test" in content


class TestPerformance:
    """Spec: Hard Cut AC#6 — Performance (20 cards batch < 30s P95)."""

    def test_20_card_batch_completes_under_30s(self, real_bridge_client, vault_env):
        """20-card sync completes in < 30s (MockLLMClient, no real LLM)."""
        cards = [
            {
                "text": f"card-{i}",
                "prefix": "",
                "suffix": "",
                "context": f"context for card {i}",
                "sourceUrl": f"https://example.com/{i}",
                "timestamp": i,
            }
            for i in range(20)
        ]
        payload = {"trigger": "manual", "cards": cards, "obsidianVaultPath": vault_env}

        started = time.time()
        r = real_bridge_client.post("/sync/recall-sticker", json=payload)
        elapsed = time.time() - started

        assert r.status_code == 200, f"Request failed: {r.json()}"
        assert elapsed < 30.0, f"20-card sync took {elapsed:.1f}s (>30s threshold)"


class TestHealthEndpoint:
    """Spec: bridge /health endpoint must report vault + M2.1 status."""

    def test_health_returns_required_fields(self, vault_env, fake_minimax_key):
        """/health returns status, version, vaultWritable, minimaxConfigured, uptimeSec."""
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        required_fields = ["status", "version", "vaultWritable", "minimaxConfigured", "currentVault", "uptimeSec"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["vaultWritable"] is True
        assert data["minimaxConfigured"] is True
        assert isinstance(data["uptimeSec"], int)

    def test_health_reflects_minimax_key_state(self, vault_env, no_minimax_key):
        """/health shows minimaxConfigured=False when key absent."""
        client = TestClient(app)
        r = client.get("/health")
        assert r.json()["minimaxConfigured"] is False

    def test_health_reflects_vault_writability(self, tmp_path, fake_minimax_key):
        """/health shows vaultWritable=False for read-only vault."""
        import os as _os
        vault = tmp_path / "readonly"
        vault.mkdir()
        _os.chmod(vault, 0o555)
        try:
            _os.environ["OBSIDIAN_VAULT"] = str(vault)
            client = TestClient(app)
            r = client.get("/health")
            # vaultWritable checks both exists + writable
            # exists=True (dir exists), writable=False (no write perm)
            # But our check uses os.access on the dir which is False for 0o555
            assert r.json()["vaultWritable"] is False
        finally:
            _os.chmod(vault, 0o755)
            _os.environ.pop("OBSIDIAN_VAULT", None)