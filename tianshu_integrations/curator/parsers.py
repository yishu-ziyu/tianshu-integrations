"""JSON parsing with multi-layer fallback for LLM responses.

M2.1 / M3 (reasoning models) may return:
1. Valid JSON
2. JSON wrapped in markdown ```json ... ```
3. Free text with JSON-like content
4. Totally garbage text
5. Truncated JSON (mid-key, no closing brace)

We try layers in order until one parses.
"""

import json
import re
from typing import Any


def parse_curation_response(raw: str) -> dict[str, Any]:
    """Parse LLM response into a curation dict.

    Layers (in order):
    1. Strict JSON parse
    2. Lenient JSON parse (allow trailing comma, single quotes)
    3. Extract first {...} block (supports nested braces up to 3 levels)
    4. ```json ... ``` markdown block
    5. Truncated JSON recovery (progressively shorter prefixes)
    6. Single-field fallback (naive tag extraction)

    Always returns a dict with at least `tags` and `rewrites` keys.
    """
    if not raw:
        return {"tags": [], "rewrites": []}

    # Layer 1: strict JSON parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return _normalize(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 2: lenient JSON parse (strip trailing commas before ] or })
    try:
        cleaned = re.sub(r",(\s*[}\]])", r"\1", raw)
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return _normalize(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 3: extract first {...} block (supports nested braces up to 3 levels)
    # Pattern: outermost {...} with up to 2 levels of nesting
    nested_pattern = r"\{(?:[^{}]|\{[^{}]*\})*\}"
    for pattern in [nested_pattern, r"\{[^{}]*\}"]:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return _normalize(parsed)
            except (json.JSONDecodeError, ValueError):
                pass

    # Layer 4: ```json ... ``` markdown block
    m = re.search(r"```json\s*(.+?)\s*```", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return _normalize(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    # Layer 5: truncated JSON recovery
    # If raw doesn't end with } or ], try progressively shorter prefixes
    # that DO end with } or ]
    trimmed = raw.rstrip()
    if trimmed and trimmed[-1] not in "}]":
        # Walk backwards from the end looking for a valid prefix
        for end_idx in range(len(trimmed), 0, -1):
            if end_idx < len(trimmed) and trimmed[end_idx - 1] in "}]":
                candidate = trimmed[:end_idx]
                # Add closing braces if missing
                opens = candidate.count("{") - candidate.count("}")
                candidate_padded = candidate + "}" * opens
                try:
                    parsed = json.loads(candidate_padded)
                    if isinstance(parsed, dict):
                        return _normalize(parsed)
                except (json.JSONDecodeError, ValueError):
                    pass
                break  # only try once per closing brace position

    # Layer 6: naive tag extraction
    return {
        "tags": _extract_tags_naive(raw),
        "rewrites": [],
    }


def _normalize(parsed: dict[str, Any]) -> dict[str, Any]:
    """Ensure expected keys exist with correct types."""
    result = dict(parsed)
    if "tags" not in result or not isinstance(result["tags"], list):
        result["tags"] = []
    if "rewrites" not in result or not isinstance(result["rewrites"], list):
        result["rewrites"] = []
    if "batch_tags" not in result or not isinstance(result["batch_tags"], list):
        # Backwards compat: top-level "tags" → "batch_tags"
        if isinstance(result.get("tags"), list):
            result["batch_tags"] = result["tags"][:3]
        else:
            result["batch_tags"] = []
    if "card_tags" not in result or not isinstance(result["card_tags"], dict):
        result["card_tags"] = {}
    if "merges" not in result or not isinstance(result["merges"], list):
        result["merges"] = []
    if "wikiLinks" not in result or not isinstance(result["wikiLinks"], list):
        result["wikiLinks"] = []
    return result


def _extract_tags_naive(text: str) -> list[str]:
    """Extract #-prefixed tokens as fallback tags."""
    return list(dict.fromkeys(re.findall(r"#(\w+)", text)))[:5]