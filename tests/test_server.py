"""Tests for bridge HTTP endpoints.

TDD: written before implementation.
"""

from fastapi.testclient import TestClient

from tianshu_integrations.bridge.server import app


def test_health_ok(vault_env, fake_minimax_key):
    """GET /health returns 200 with vault writable + M2.1 configured."""
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["vaultWritable"] is True
    assert data["minimaxConfigured"] is True
    assert "uptimeSec" in data
    assert "version" in data


def test_health_no_minimax_key(vault_env, no_minimax_key):
    """GET /health returns minimaxConfigured=False when key missing."""
    client = TestClient(app)
    r = client.get("/health")
    data = r.json()
    assert data["minimaxConfigured"] is False


def test_sync_writes_markdown_direct_no_llm(vault_env, no_minimax_key):
    """POST /sync/recall-sticker without M2.1 key uses mock and writes .md."""
    client = TestClient(app)
    payload = {
        "trigger": "manual",
        "cards": [
            {
                "text": "eBPF",
                "prefix": "类似 ",
                "suffix": " 的机制",
                "context": "类似 eBPF 的机制",
                "sourceUrl": "https://example.com/article",
                "timestamp": 1,
            },
            {
                "text": "service mesh",
                "prefix": "",
                "suffix": "",
                "context": "{{c1::service mesh}} 是微服务通信层",
                "sourceUrl": "https://example.com/article2",
                "timestamp": 2,
            },
        ],
        "obsidianVaultPath": vault_env,
    }
    r = client.post("/sync/recall-sticker", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["curated"]) == 2

    # File should be created
    from datetime import datetime
    import pathlib

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = pathlib.Path(vault_env) / "Inbox" / f"{today}-recall.md"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "eBPF" in content
    assert "service mesh" in content
    # Anki Cloze should be stripped to brackets
    assert "{{c1::" not in content


def test_sync_rejects_nonexistent_vault(no_minimax_key):
    """POST /sync/recall-sticker returns 400 when vault doesn't exist."""
    client = TestClient(app)
    payload = {
        "trigger": "manual",
        "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
        "obsidianVaultPath": "/nonexistent/path/12345",
    }
    r = client.post("/sync/recall-sticker", json=payload)
    assert r.status_code == 400
    assert "vault path does not exist" in r.json()["error"]


def test_sync_empty_cards_returns_empty(vault_env, no_minimax_key):
    """POST /sync/recall-sticker with empty cards list returns success but no write."""
    client = TestClient(app)
    payload = {
        "trigger": "manual",
        "cards": [],
        "obsidianVaultPath": vault_env,
    }
    r = client.post("/sync/recall-sticker", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["curated"] == []


def test_sync_appends_to_existing_file(vault_env, no_minimax_key):
    """Multiple sync calls to same day append, don't overwrite."""
    client = TestClient(app)
    payload1 = {
        "trigger": "manual",
        "cards": [{"text": "first", "sourceUrl": "u", "timestamp": 1}],
        "obsidianVaultPath": vault_env,
    }
    payload2 = {
        "trigger": "manual",
        "cards": [{"text": "second", "sourceUrl": "u", "timestamp": 2}],
        "obsidianVaultPath": vault_env,
    }
    client.post("/sync/recall-sticker", json=payload1)
    client.post("/sync/recall-sticker", json=payload2)

    from datetime import datetime
    import pathlib

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = pathlib.Path(vault_env) / "Inbox" / f"{today}-recall.md"
    content = file_path.read_text(encoding="utf-8")
    assert "first" in content
    assert "second" in content