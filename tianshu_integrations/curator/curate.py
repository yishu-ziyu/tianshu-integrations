"""Curator: organize Recall Sticker cards via M2.1.

Two-phase approach (Week 2):
- Phase A (curate_phase_a): batch-level tag + merge suggestions (1 M2.1 call)
- Phase B (curate_phase_b): single-card wiki link suggestions from vault (per-card M2.1 call)
- orchestrate(curate): runs A, builds CuratedCard, then per-card runs B

Reasoning model handling:
- Both M2.1 and M3 emit <think>...</think> blocks
- We strip them via extractContent() BEFORE passing to JSON parser

Per-card isolation: one card's failure does not block the batch.
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field

from tianshu_integrations.bridge.schemas import CardError, CuratedCard, RawCard
from tianshu_integrations.curator.parsers import parse_curation_response
from tianshu_integrations.curator.prompts import (
    build_phase_a_prompt,
    build_phase_b_prompt,
)
from tianshu_integrations.llm.client import extractContent


CLOZE_PATTERN = re.compile(r"\{\{c\d+::(.*?)\}\}")


class MergeProposal(BaseModel):
    """Phase A merge suggestion: source cardId should be merged into target cardId."""
    source: str
    target: str
    reason: str = ""


class PhaseAResult(BaseModel):
    """Output of Phase A: batch-level organization."""
    batch_tags: list[str] = Field(default_factory=list)
    card_tags: dict[str, list[str]] = Field(default_factory=dict)
    merges: list[MergeProposal] = Field(default_factory=list)


def sanitize_context(card: RawCard) -> RawCard:
    """Strip Anki Cloze markers {{c1::text}} → [text] to avoid prompt injection."""
    if card.context:
        cleaned = CLOZE_PATTERN.sub(r"[\1]", card.context)
        card = card.model_copy(update={"context": cleaned})
    return card


def generate_card_id(card: RawCard) -> str:
    """Generate stable card id from timestamp + text prefix."""
    text_prefix = re.sub(r"\W+", "_", card.text)[:10].strip("_") or "card"
    return f"{card.timestamp}_{text_prefix}"


async def curate_phase_a(
    cards: list[RawCard],
    llm_client,
) -> PhaseAResult:
    """Phase A: batch-level tag + merge suggestions (1 M2.1 call).

    Returns empty PhaseAResult on LLM failure (caller falls back to direct write).
    """
    if not cards:
        return PhaseAResult()

    sanitized = [sanitize_context(c) for c in cards]
    for card in sanitized:
        if not card.id:
            card.id = generate_card_id(card)

    cards_text = "\n".join(
        f"[{c.id}] text={c.text!r} ctx={c.context!r} src={c.sourceUrl}"
        for c in sanitized
    )
    prompt = build_phase_a_prompt(cards_text)

    try:
        raw = await llm_client.chat(prompt)
        # Strip <think>...</think> blocks (M2.1 / M3 reasoning)
        cleaned = extractContent(raw)
        parsed = parse_curation_response(cleaned)
    except Exception:
        # Caller will fall back; return empty PhaseAResult
        return PhaseAResult()

    # parse_curation_response may return "tags" + "rewrites" (legacy single schema)
    # or be missing our Phase A fields. Normalize:
    batch_tags = parsed.get("batch_tags", [])
    if not batch_tags and "tags" in parsed:
        # Old single-prompt schema — fall back to using top-level tags as batch_tags
        batch_tags = parsed.get("tags", [])[:3]
    card_tags = parsed.get("card_tags", {})

    merges = []
    for m in parsed.get("merges", []):
        if isinstance(m, dict) and "source" in m and "target" in m:
            merges.append(MergeProposal(
                source=m["source"],
                target=m["target"],
                reason=m.get("reason", ""),
            ))

    return PhaseAResult(
        batch_tags=batch_tags,
        card_tags=card_tags,
        merges=merges,
    )


async def curate_phase_b(
    card: CuratedCard,
    vault_existing_notes: list[str],
    llm_client,
) -> list[str]:
    """Phase B: single-card wiki link suggestions (per-card M2.1 call).

    Returns [] on failure (curator never crashes on wiki link issues).
    """
    prompt = build_phase_b_prompt(
        card_text=card.title,
        card_context=card.body,
        card_source=card.sourceUrl or "",
        existing_notes=vault_existing_notes,
    )
    try:
        raw = await llm_client.chat(prompt)
        cleaned = extractContent(raw)
        parsed = parse_curation_response(cleaned)
    except Exception:
        return []

    links = parsed.get("wikiLinks", [])
    # Normalize: accept both "[[path]]" and "path" forms
    normalized = []
    for link in links:
        if isinstance(link, str):
            if link.startswith("[[") and link.endswith("]]"):
                normalized.append(link)
            else:
                normalized.append(f"[[{link}]]")
    return normalized


def scan_vault_existing_notes(vault_path: str) -> list[str]:
    """Scan vault for existing .md files. Return path-style names (without .md).

    Used by Phase B to suggest wiki links.
    """
    vault = Path(vault_path)
    if not vault.is_dir():
        return []
    notes = []
    for md_file in vault.rglob("*.md"):
        # Skip our own output
        if ".recall-sync.lock" in md_file.name:
            continue
        rel = md_file.relative_to(vault)
        # Strip .md extension
        notes.append(str(rel.with_suffix("")))
    return sorted(notes)


async def curate(
    cards: list[RawCard],
    llm_client,
    vault_path: str | None = None,
) -> tuple[list[CuratedCard], list[CardError]]:
    """Orchestrate Phase A + Phase B + write.

    Returns (curated, errors). Per-card isolation throughout.

    If vault_path is provided, Phase B uses it to suggest wiki links.
    Otherwise Phase B is skipped (empty wikiLinks).
    """
    if not cards:
        return [], []

    sanitized = [sanitize_context(c) for c in cards]
    for card in sanitized:
        if not card.id:
            card.id = generate_card_id(card)

    # Phase A: batch-level organization
    phase_a = await curate_phase_a(sanitized, llm_client)

    # Build CuratedCard for each input card
    curated: list[CuratedCard] = []
    for card in sanitized:
        # Apply Phase A results
        card_tags = phase_a.card_tags.get(card.id, [])
        all_tags = _merge_tags(card.tags, card_tags, phase_a.batch_tags)

        body = card.context or f"{card.prefix} **{card.text}** {card.suffix}"
        title = card.text  # Phase A could refine this later

        # Track merged sources (cards pointing to this one)
        merged_sources = []
        for merge in phase_a.merges:
            if merge.target == card.id:
                merged_sources.append(merge.source)

        c = CuratedCard(
            cardId=card.id,
            title=title,
            body=body,
            tags=all_tags,
            wikiLinks=[],  # Phase B fills this
            mergedWith=merged_sources[0] if merged_sources else None,
            sourceUrl=card.sourceUrl,
        )
        curated.append(c)

    # Phase B: per-card wiki link suggestions (only if vault_path given)
    if vault_path:
        try:
            existing_notes = scan_vault_existing_notes(vault_path)
        except Exception:
            existing_notes = []
        for c in curated:
            c.wikiLinks = await curate_phase_b(c, existing_notes, llm_client)

    return curated, []


def _fallback_direct_write(
    cards: list[RawCard], errors: list[CardError]
) -> list[CuratedCard]:
    """When LLM fails entirely, write cards directly without curation.

    Kept for backwards compatibility with server.py direct-write fallback path.
    """
    result = []
    for card in cards:
        body = card.context or f"{card.prefix} **{card.text}** {card.suffix}"
        result.append(
            CuratedCard(
                cardId=card.id or generate_card_id(card),
                title=card.text,
                body=body,
                tags=card.tags,
                wikiLinks=[],
                sourceUrl=card.sourceUrl,
            )
        )
    return result


def _merge_tags(*tag_lists: list[str]) -> list[str]:
    """Merge multiple tag lists, dedup, cap at 3."""
    seen = set()
    result = []
    for tag_list in tag_lists:
        for tag in tag_list:
            if tag and tag not in seen:
                result.append(tag)
                seen.add(tag)
                if len(result) >= 3:
                    return result
    return result