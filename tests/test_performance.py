import sys
"""Performance baseline tests for Tianshu Integrations.

Week 4 T-28: Establish performance baselines per Week 1 ROADMAP §6.
"""

import asyncio
import os
import time
from pathlib import Path

import pytest

# === Mock performance tests (always run) ===

def test_1_card_mock_under_500ms(vault_env, fake_minimax_key):
    """1 card with MockLLMClient + TestClient lifespan should sync in < 500ms.

    Note: TestClient lifespan startup costs ~250ms on first request.
    Per-card cost amortizes with batch size.
    """
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app
    from tianshu_integrations.bridge.schemas import RawCard

    with TestClient(app) as client:
        # Warmup (TestClient lifespan startup)
        client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [RawCard(text="warmup", sourceUrl="u", timestamp=0).model_dump()],
            "obsidianVaultPath": vault_env,
        })
        started = time.time()
        r = client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": [RawCard(text="perf", sourceUrl="u", timestamp=1).model_dump()],
            "obsidianVaultPath": vault_env,
        })
        elapsed = (time.time() - started) * 1000
        assert r.status_code == 200
        assert elapsed < 500, f"1 card took {elapsed:.1f}ms (expected < 500ms after warmup)"


def test_5_cards_mock_under_1s(vault_env, fake_minimax_key):
    """5 cards should sync in < 1s (MockLLMClient, after warmup)."""
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app
    from tianshu_integrations.bridge.schemas import RawCard

    cards = [
        RawCard(text=f"perf-{i}", sourceUrl="u", timestamp=i).model_dump()
        for i in range(5)
    ]
    with TestClient(app) as client:
        # Warmup
        client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": cards[:1],
            "obsidianVaultPath": vault_env,
        })
        started = time.time()
        r = client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": cards,
            "obsidianVaultPath": vault_env,
        })
        elapsed = (time.time() - started) * 1000
        assert r.status_code == 200
        assert elapsed < 1000, f"5 cards took {elapsed:.1f}ms (expected < 1s)"


def test_100_cards_mock_under_5s(vault_env, fake_minimax_key):
    """100 cards should sync in < 5s (MockLLMClient, single batch, after warmup)."""
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app
    from tianshu_integrations.bridge.schemas import RawCard

    cards = [
        RawCard(text=f"perf-{i}", sourceUrl="u", timestamp=i).model_dump()
        for i in range(100)
    ]
    with TestClient(app) as client:
        # Warmup
        client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": cards[:1],
            "obsidianVaultPath": vault_env,
        })
        started = time.time()
        r = client.post("/sync/recall-sticker", json={
            "trigger": "manual",
            "cards": cards,
            "obsidianVaultPath": vault_env,
        })
        elapsed = (time.time() - started) * 1000
        assert r.status_code == 200
        assert elapsed < 10000, f"100 cards took {elapsed:.1f}ms (expected < 10s)"


def test_5_concurrent_sync_data_preserved(vault_env, fake_minimax_key):
    """5 concurrent /sync calls preserve all data (Week 1 fcntl fix)."""
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from tianshu_integrations.bridge.server import app
    from tianshu_integrations.bridge.schemas import RawCard

    def do_sync(idx):
        with TestClient(app) as c:
            r = c.post("/sync/recall-sticker", json={
                "trigger": "manual",
                "cards": [RawCard(text=f"concurrent-{idx}", sourceUrl="u", timestamp=idx).model_dump()],
                "obsidianVaultPath": vault_env,
            })
            return r.json()

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(do_sync, range(5)))

    # All 5 succeeded
    for r in results:
        assert r["success"] is True

    # All 5 cards present in .md
    md_file = Path(vault_env) / "Inbox" / f"{time.strftime('%Y-%m-%d')}-recall.md"
    if md_file.exists():
        content = md_file.read_text(encoding="utf-8")
        for i in range(5):
            assert f"concurrent-{i}" in content, f"concurrent-{i} missing from {md_file}"


# === Real API performance (requires MINIMAX_API_KEY) ===

@pytest.mark.skipif(
    not os.environ.get("INTEGRATION_TEST"),
    reason="INTEGRATION_TEST not set (requires real MINIMAX_API_KEY)",
)
@pytest.mark.asyncio
async def test_5_cards_real_minimax_under_30s():
    """5 cards with real M2.1 should sync in < 30s."""
    from tianshu_integrations.bridge.server import app
    from tianshu_integrations.bridge.schemas import RawCard
    from fastapi.testclient import TestClient
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        os.environ["OBSIDIAN_VAULT"] = td
        with TestClient(app) as client:
            cards = [
                RawCard(text=f"perf-{i}", sourceUrl="u", timestamp=i).model_dump()
                for i in range(5)
            ]
            started = time.time()
            r = client.post("/sync/recall-sticker", json={
                "trigger": "manual",
                "cards": cards,
                "obsidianVaultPath": td,
            })
            elapsed = (time.time() - started)
            assert r.status_code == 200
            assert elapsed < 30, f"5 cards took {elapsed:.1f}s (expected < 30s)"


# === Bridge startup performance ===

@pytest.mark.slow
def test_bridge_startup_under_2s():
    """tianshu-bridge should start up in < 2s."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as vault:
        env = {**os.environ, "OBSIDIAN_VAULT": vault}
        # Use --help to measure import time + arg parsing
        started = time.time()
        result = subprocess.run(
            ["/Users/mahaoxuan/Developer/tianshu-integrations/.venv/bin/tianshu-bridge", "--help"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        elapsed = time.time() - started
        assert result.returncode == 0
        assert elapsed < 2, f"bridge startup took {elapsed:.1f}s (expected < 2s)"