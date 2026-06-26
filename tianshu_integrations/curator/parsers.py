"""JSON parsing with multi-layer fallback for LLM responses.

M2.1 may return:
1. Valid JSON
2. JSON wrapped in markdown ```json ... ```
3. Free text with JSON-like content
4. Totally garbage text

We try layers in order until one parses.
"""

import json
import re
from typing import Any


def parse_curation_response(raw: str) -> dict[str, Any]:
    """Parse LLM response into a curation dict.

    Layers (in order):
    1. Strict JSON parse
    2. Extract first {...} block
    3. Extract ```json ... ``` block
    4. Single-field fallback (naive tag extraction)

    Always returns a dict with at least `tags` and `rewrites` keys.
    """
    # Layer 1: strict JSON
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return _normalize(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 2: extract first {...} block (greedy match)
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, dict):
                return _normalize(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    # Layer 3: markdown ```json ... ``` block
    m = re.search(r"```json\s*(.+?)\s*```", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return _normalize(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    # Layer 4: naive tag extraction
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
    return result


def _extract_tags_naive(text: str) -> list[str]:
    """Extract #-prefixed tokens as fallback tags."""
    return list(dict.fromkeys(re.findall(r"#(\w+)", text)))[:5]