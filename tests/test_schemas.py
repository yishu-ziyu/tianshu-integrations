"""Tests for Pydantic schemas."""

from tianshu_integrations.bridge.schemas import (
    CardError,
    CuratedCard,
    RawCard,
    SkippedCard,
    SyncRequest,
    SyncResponse,
)


def test_rawcard_minimal():
    """RawCard accepts minimal payload."""
    c = RawCard.model_validate({"text": "test", "sourceUrl": "https://x.com", "timestamp": 123})
    assert c.text == "test"
    assert c.prefix == ""
    assert c.suffix == ""
    assert c.context == ""
    assert c.tags == []
    assert c.id is None


def test_rawcard_full():
    """RawCard accepts all fields."""
    c = RawCard.model_validate({
        "text": "t",
        "prefix": "p",
        "suffix": "s",
        "context": "ctx",
        "sourceUrl": "u",
        "tags": ["a", "b"],
        "timestamp": 1,
        "id": "card_1",
    })
    assert c.tags == ["a", "b"]
    assert c.id == "card_1"


def test_rawcard_missing_required():
    """RawCard rejects payload missing required fields."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RawCard.model_validate({"text": "t"})  # missing sourceUrl + timestamp


def test_syncrequest_valid():
    """SyncRequest accepts valid payload."""
    req = SyncRequest.model_validate({
        "trigger": "manual",
        "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
        "obsidianVaultPath": "/tmp/vault",
    })
    assert req.trigger == "manual"
    assert len(req.cards) == 1
    assert req.m2xModel == "MiniMax-M3"  # default


def test_syncrequest_invalid_trigger():
    """SyncRequest rejects invalid trigger value."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SyncRequest.model_validate({
            "trigger": "invalid",
            "cards": [],
            "obsidianVaultPath": "/tmp",
        })


def test_curatedcard_minimal():
    """CuratedCard accepts minimal payload."""
    c = CuratedCard(cardId="1", title="t", body="b")
    assert c.tags == []
    assert c.wikiLinks == []
    assert c.mergedWith is None


def test_syncresponse_defaults():
    """SyncResponse has sensible defaults for all optional fields."""
    r = SyncResponse(success=True)
    assert r.curated == []
    assert r.skipped == []
    assert r.errors == []
    assert r.durationMs == 0
    assert r.obsidianFilesWritten == []