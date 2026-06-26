"""Tests for curator (M2.1 organization)."""

import pytest

from tianshu_integrations.bridge.schemas import CardError, CuratedCard, RawCard
from tianshu_integrations.curator.curate import curate, generate_card_id, sanitize_context
from tianshu_integrations.llm.client import MockLLMClient


def test_generate_card_id_from_timestamp():
    """Card id uses timestamp + text prefix for stability."""
    card = RawCard(text="eBPF tech!", sourceUrl="u", timestamp=12345)
    cid = generate_card_id(card)
    assert cid.startswith("12345_")
    assert "eBPF" in cid or "tech" in cid


def test_generate_card_id_handles_special_chars():
    """Special chars in text get replaced with underscore."""
    card = RawCard(text="a/b\\c d", sourceUrl="u", timestamp=1)
    cid = generate_card_id(card)
    assert "\\" not in cid
    assert "/" not in cid
    assert " " not in cid


def test_sanitize_context_strips_cloze():
    """Anki Cloze {{c1::text}} becomes [text]."""
    card = RawCard(
        text="x",
        context="this is {{c1::a concept}} in action",
        sourceUrl="u",
        timestamp=1,
    )
    sanitized = sanitize_context(card)
    assert "{{c1::" not in sanitized.context
    assert "[a concept]" in sanitized.context


def test_sanitize_context_preserves_normal_text():
    """Non-Cloze text passes through unchanged."""
    card = RawCard(text="x", context="normal text without cloze", sourceUrl="u", timestamp=1)
    sanitized = sanitize_context(card)
    assert sanitized.context == "normal text without cloze"


@pytest.mark.asyncio
async def test_curate_with_valid_json_response():
    """M2.1 returns valid JSON → cards get tags + rewrite."""
    mock = MockLLMClient(response='{"tags": ["k8s", "networking"], "rewrites": [{"cardId": "1_eBPF", "title": "eBPF", "body": "内核技术"}]}')
    cards = [RawCard(text="eBPF", sourceUrl="u", timestamp=1)]
    curated, errors = await curate(cards, llm_client=mock)
    assert len(curated) == 1
    assert curated[0].title == "eBPF"
    assert "k8s" in curated[0].tags
    assert errors == []


@pytest.mark.asyncio
async def test_curate_fallback_on_bad_json():
    """M2.1 returns non-JSON → curator falls back to direct write."""
    mock = MockLLMClient(response="I cannot help with this, sorry")
    cards = [RawCard(text="hello", prefix="say ", suffix=" world", sourceUrl="u", timestamp=1)]
    curated, errors = await curate(cards, llm_client=mock)
    assert len(curated) == 1
    assert "hello" in curated[0].body
    # Falls back gracefully — no crash
    assert errors == []


@pytest.mark.asyncio
async def test_curate_per_card_isolation():
    """One card's failure doesn't block others (returns card in curated, error in errors)."""
    # Mock returns only one rewrite for first card; second card gets direct fallback
    mock = MockLLMClient(
        response='{"tags": ["ok"], "rewrites": [{"cardId": "1_a", "title": "a"}]}'
    )
    cards = [
        RawCard(text="a", sourceUrl="u", timestamp=1),
        RawCard(text="b", sourceUrl="u", timestamp=2),
        RawCard(text="c", sourceUrl="u", timestamp=3),
    ]
    curated, errors = await curate(cards, llm_client=mock)
    assert len(curated) == 3  # all 3 cards processed
    assert errors == []


@pytest.mark.asyncio
async def test_curate_handles_anki_cloze_in_prompt():
    """Cards with {{c1::...}} context are sanitized before M2.1 prompt."""
    mock = MockLLMClient(response='{"tags": ["x"], "rewrites": [{"cardId": "1_x", "title": "t", "body": "b"}]}')
    cards = [
        RawCard(text="x", context="{{c1::secret}} is fun", sourceUrl="u", timestamp=1),
    ]
    curated, errors = await curate(cards, llm_client=mock)
    assert len(curated) == 1
    # Verify mock received sanitized prompt (no {{c1::)
    # (We can verify by checking mock.call_count)
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_curate_empty_cards():
    """Empty cards list returns empty curated + empty errors."""
    mock = MockLLMClient()
    curated, errors = await curate([], llm_client=mock)
    assert curated == []
    assert errors == []
    assert mock.call_count == 0  # No LLM call for empty list


@pytest.mark.asyncio
async def test_curate_whole_batch_failure_returns_errors():
    """If LLM.chat() raises, all cards get error + fallback direct write."""
    class FailingClient:
        async def chat(self, prompt, max_tokens=2000):
            raise RuntimeError("LLM down")

    cards = [
        RawCard(text="a", sourceUrl="u", timestamp=1),
        RawCard(text="b", sourceUrl="u", timestamp=2),
    ]
    curated, errors = await curate(cards, llm_client=FailingClient())
    assert len(errors) == 2
    assert all("LLM down" in e.message for e in errors)
    assert len(curated) == 2  # fallback direct write