"""Tests for JSON parsing with multi-layer fallback."""

from tianshu_integrations.curator.parsers import parse_curation_response


def test_parse_strict_json():
    """Layer 1: valid JSON parses correctly."""
    raw = '{"tags": ["k8s"], "rewrites": [{"cardId": "1", "title": "t"}]}'
    result = parse_curation_response(raw)
    assert result["tags"] == ["k8s"]
    assert result["rewrites"] == [{"cardId": "1", "title": "t"}]


def test_parse_extract_json_block():
    """Layer 2: extract first {...} block from surrounding text."""
    raw = (
        "Here is my analysis:\n\n"
        '{"tags": ["networking"], "rewrites": [{"cardId": "x"}]}\n\n'
        "Hope this helps!"
    )
    result = parse_curation_response(raw)
    assert result["tags"] == ["networking"]


def test_parse_markdown_json_block():
    """Layer 3: ```json ... ``` block."""
    raw = (
        "Sure!\n\n"
        "```json\n"
        '{"tags": ["linux"], "rewrites": []}\n'
        "```\n\n"
        "Done."
    )
    result = parse_curation_response(raw)
    assert result["tags"] == ["linux"]


def test_parse_naive_tag_extraction():
    """Layer 4: extract #hashtags from free text."""
    raw = "This card is about #kubernetes #networking and #service-mesh"
    result = parse_curation_response(raw)
    assert "kubernetes" in result["tags"]
    assert "networking" in result["tags"]
    assert result["rewrites"] == []


def test_parse_total_garbage_returns_safe_defaults():
    """Layer 4 fallback always returns dict with tags + rewrites keys."""
    raw = "totally not json at all, just text"
    result = parse_curation_response(raw)
    assert isinstance(result, dict)
    assert "tags" in result
    assert "rewrites" in result


def test_parse_normalizes_missing_keys():
    """Result always has tags + rewrites keys even if JSON has other keys."""
    raw = '{"foo": "bar"}'
    result = parse_curation_response(raw)
    assert result["tags"] == []
    assert result["rewrites"] == []


def test_parse_handles_unicode_and_emoji():
    """Parser handles unicode + emoji correctly."""
    raw = '{"tags": ["中文", "🚀rocket"], "rewrites": []}'
    result = parse_curation_response(raw)
    assert "中文" in result["tags"]
    assert "🚀rocket" in result["tags"]


def test_parse_handles_null():
    """Parser handles JSON null."""
    raw = "null"
    result = parse_curation_response(raw)
    assert result["tags"] == []
    assert result["rewrites"] == []