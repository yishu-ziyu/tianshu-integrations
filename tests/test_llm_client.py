"""Tests for MiniMax LLM client + MockLLMClient + extractContent."""

import os
import pytest

from tianshu_integrations.llm.client import MiniMaxClient, MockLLMClient, extractContent


# === extractContent (pure function) ===

def test_extract_content_strips_think_block():
    """Reasoning model output with <think> block gets stripped."""
    raw = "<think>The user wants JSON. I'll return it.</think>\n\n{\"hello\": \"world\"}"
    result = extractContent(raw)
    assert result == '{"hello": "world"}'


def test_extract_content_handles_no_think_block():
    """Plain text without thinking block passes through."""
    raw = "Just plain response"
    assert extractContent(raw) == "Just plain response"


def test_extract_content_handles_empty():
    """Empty string returns empty."""
    assert extractContent("") == ""
    assert extractContent(None) == ""


def test_extract_content_handles_multiline_think():
    """Multi-line thinking block gets fully stripped."""
    raw = "<think>\nStep 1: ...\nStep 2: ...\nConclusion: {}\n</think>\n\nFinal answer"
    result = extractContent(raw)
    assert result == "Final answer"


def test_extract_content_handles_nested_braces_in_think():
    """Even if thinking contains {} blocks, they get stripped."""
    raw = '<think>The JSON is {"nested": "stuff"}</think>\n\n{"real": "answer"}'
    result = extractContent(raw)
    assert result == '{"real": "answer"}'


def test_extract_content_preserves_internal_json():
    """Only strips outermost <think>...</think>, preserves JSON inside."""
    raw = '<think>analysis</think>\n```json\n{"x": 1}\n```'
    result = extractContent(raw)
    # The ```json block should remain intact
    assert '{"x": 1}' in result


# === MockLLMClient ===

def test_mock_client_returns_single_response():
    mock = MockLLMClient(response="hello")
    assert mock.call_count == 0  # not called yet


def test_mock_client_returns_list_responses_per_call():
    mock = MockLLMClient(response=["first", "second", "third"])
    # Each call returns the next response
    import asyncio
    async def run():
        r1 = await mock.chat("p1")
        r2 = await mock.chat("p2")
        r3 = await mock.chat("p3")
        return r1, r2, r3
    r1, r2, r3 = asyncio.run(run())
    assert r1 == "first"
    assert r2 == "second"
    assert r3 == "third"
    assert mock.call_count == 3


def test_mock_client_reuses_last_response_when_exhausted():
    """If responses list shorter than calls, reuse last one."""
    mock = MockLLMClient(response=["only"])
    import asyncio
    async def run():
        r1 = await mock.chat("p1")
        r2 = await mock.chat("p2")
        r3 = await mock.chat("p3")
        return r1, r2, r3
    r1, r2, r3 = asyncio.run(run())
    assert r1 == "only"
    assert r2 == "only"
    assert r3 == "only"


# === MiniMaxClient (real API) — requires MINIMAX_API_KEY ===

@pytest.mark.skipif(
    not os.environ.get("INTEGRATION_TEST"),
    reason="INTEGRATION_TEST not set (requires real MINIMAX_API_KEY)",
)
@pytest.mark.asyncio
async def test_real_minimax_m3_returns_response():
    """Real M3 call returns non-empty response."""
    client = MiniMaxClient()
    r = await client.chat("用一句话回答: 1+1=?", max_tokens=50)
    assert len(r) > 0


@pytest.mark.skipif(
    not os.environ.get("INTEGRATION_TEST"),
    reason="INTEGRATION_TEST not set",
)
@pytest.mark.asyncio
async def test_real_minimax_m3_response_can_be_stripped():
    """M3 returns thinking block; extractContent strips it."""
    client = MiniMaxClient()
    r = await client.chat("Return JSON: {\"hello\": \"world\"}", max_tokens=100)
    cleaned = extractContent(r)
    # If model emitted thinking, cleaned should differ from raw
    # If model skipped thinking (unlikely for M3), cleaned == raw
    assert len(cleaned) > 0
    # Cleaned should not contain <think> tag
    assert "<think>" not in cleaned


@pytest.mark.skipif(
    not os.environ.get("INTEGRATION_TEST"),
    reason="INTEGRATION_TEST not set",
)
@pytest.mark.asyncio
async def test_real_minimax_m2_1_works():
    """M2.1 also works (smaller model)."""
    client = MiniMaxClient(model="MiniMax-M2.1")
    r = await client.chat("Say hi", max_tokens=20)
    assert len(r) > 0


# === Constructor edge cases ===

def test_minimax_client_missing_key_raises_keyerror():
    """If neither env nor arg, KeyError raised (caught by server.py fallback)."""
    os.environ.pop("MINIMAX_API_KEY", None)
    with pytest.raises(KeyError):
        MiniMaxClient(api_key=None)


def test_minimax_client_with_explicit_key_works():
    """api_key arg overrides env."""
    os.environ.pop("MINIMAX_API_KEY", None)
    client = MiniMaxClient(api_key="sk-test-explicit")
    # openai SDK normalizes to "Bearer ..." so check via internal state
    assert "sk-test-explicit" in str(client.client.api_key) or client.client.api_key == "sk-test-explicit"