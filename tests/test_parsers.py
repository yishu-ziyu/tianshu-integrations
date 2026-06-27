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


# === Week 2 robustness tests ===

def test_parse_trailing_comma_lenient():
    """Layer 2: lenient JSON parse allows trailing comma."""
    raw = '{"tags": ["a", "b",], "rewrites": [],}'
    result = parse_curation_response(raw)
    assert "a" in result["tags"]
    assert "b" in result["tags"]


def test_parse_truncated_json_recovers():
    """Layer 5: truncated JSON recovers tags from valid prefix."""
    raw = '{"tags": ["a", "b"], "rewrites": [{"cardId":'  # truncated mid-value
    result = parse_curation_response(raw)
    # Layer 3 should match the outer {...} and parse successfully
    assert "a" in result["tags"]
    assert "b" in result["tags"]


def test_parse_normalizes_week2_schema():
    """Phase A/B schema fields are normalized even if missing."""
    raw = '{"batch_tags": ["k8s"], "card_tags": {"1": ["linux"]}, "merges": []}'
    result = parse_curation_response(raw)
    assert result["batch_tags"] == ["k8s"]
    assert result["card_tags"] == {"1": ["linux"]}
    assert result["merges"] == []


def test_parse_backfills_batch_tags_from_tags():
    """If only top-level 'tags' present (old schema), backfill batch_tags."""
    raw = '{"tags": ["a", "b", "c"]}'
    result = parse_curation_response(raw)
    assert result["tags"] == ["a", "b", "c"]
    assert result["batch_tags"] == ["a", "b", "c"][:3]


def test_parse_empty_string():
    raw = ""
    result = parse_curation_response(raw)
    assert result == {"tags": [], "rewrites": []}


def test_parse_handles_wikilinks_field():
    raw = '{"tags": ["k8s"], "wikiLinks": ["[[Projects/tianshu]]", "[[Concepts/Kubernetes]]"]}'
    result = parse_curation_response(raw)
    assert "[[Projects/tianshu]]" in result["wikiLinks"]


def test_parse_handles_complex_merges():
    """MergeProposal structure preserved through normalize."""
    raw = '''{
        "batch_tags": ["k8s"],
        "card_tags": {"1_eBPF": ["linux"]},
        "merges": [
            {"source": "1_eBPF", "target": "2_sidecar", "reason": "kernel concepts"}
        ]
    }'''
    result = parse_curation_response(raw)
    assert len(result["merges"]) == 1
    assert result["merges"][0]["source"] == "1_eBPF"
    assert result["merges"][0]["reason"] == "kernel concepts"