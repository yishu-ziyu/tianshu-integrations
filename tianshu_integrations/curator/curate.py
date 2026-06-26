"""Curator: organize Recall Sticker cards via M2.1.

Two-phase approach (Phase 1):
- Phase A (curate): sanitize context + call M2.1 + parse response
- Phase B (per-card fallback): if M2.1 fails or returns no rewrites,
  write each card with its own context (no LLM transformation).

Per-card isolation: one card's failure does not block the batch.
"""

import re

from tianshu_integrations.bridge.schemas import CardError, CuratedCard, RawCard
from tianshu_integrations.curator.parsers import parse_curation_response


CLOZE_PATTERN = re.compile(r"\{\{c\d+::(.*?)\}\}")
PROMPT_TEMPLATE = """你是知识整理助手。给定以下 recall-sticker 卡片:

{cards_text}

对每张卡返回 JSON:
{{
  "tags": ["tag1", "tag2"],       // 本批所有 unique tag
  "rewrites": [
    {{
      "cardId": "id1",
      "title": "简短标题",
      "body": "改写后的 Markdown 内容",
      "wikiLinks": []
    }}
  ]
}}

要求:
- tag 语义化(英文小写或中文),1-3 个
- title ≤15 字,body ≤100 字
- 如果多张卡主题相同,合并到同一组 tags
"""


def sanitize_context(card: RawCard) -> RawCard:
    """Strip Anki Cloze markers {{c1::text}} → [text] to avoid prompt injection."""
    if card.context:
        # Use model_copy to stay immutable
        cleaned = CLOZE_PATTERN.sub(r"[\1]", card.context)
        card = card.model_copy(update={"context": cleaned})
    return card


def generate_card_id(card: RawCard) -> str:
    """Generate stable card id from timestamp + text prefix."""
    text_prefix = re.sub(r"\W+", "_", card.text)[:10].strip("_") or "card"
    return f"{card.timestamp}_{text_prefix}"


async def curate(
    cards: list[RawCard],
    llm_client,
) -> tuple[list[CuratedCard], list[CardError]]:
    """Curate a batch of cards. Returns (curated, errors).

    Per-card isolation: if M2.1 fails entirely, all cards fall back to
    direct write. If M2.1 returns partial rewrites, missing cards
    also fall back.
    """
    if not cards:
        return [], []

    # Sanitize context for all cards (avoid Anki Cloze → M2.1 confusion)
    sanitized = [sanitize_context(c) for c in cards]

    # Generate ids if missing
    for card in sanitized:
        if not card.id:
            card.id = generate_card_id(card)

    # Build prompt
    cards_text = "\n".join(
        f"[{c.id}] text={c.text!r} ctx={c.context!r} src={c.sourceUrl}"
        for c in sanitized
    )
    prompt = PROMPT_TEMPLATE.format(cards_text=cards_text)

    # Call LLM
    curated: list[CuratedCard] = []
    errors: list[CardError] = []

    try:
        raw = await llm_client.chat(prompt)
    except Exception as e:
        # Whole batch failed — return errors for all cards
        for c in sanitized:
            errors.append(CardError(cardId=c.id or "", message=f"LLM call failed: {e}"))
        return _fallback_direct_write(sanitized, errors=[]), errors

    # Parse LLM response (multi-layer fallback)
    parsed = parse_curation_response(raw)
    rewrites_by_id = {r.get("cardId"): r for r in parsed.get("rewrites", []) if r.get("cardId")}
    global_tags = parsed.get("tags", [])[:3]

    # Build curated cards
    for card in sanitized:
        rewrite = rewrites_by_id.get(card.id)
        if rewrite:
            curated.append(
                CuratedCard(
                    cardId=card.id,
                    title=str(rewrite.get("title", card.text))[:30],
                    body=str(rewrite.get("body", card.context or f"{card.prefix} {card.text} {card.suffix}")),
                    tags=_merge_tags(card.tags, global_tags),
                    wikiLinks=rewrite.get("wikiLinks", []),
                )
            )
        else:
            # No rewrite for this card — direct write fallback
            body = card.context or f"{card.prefix} **{card.text}** {card.suffix}"
            curated.append(
                CuratedCard(
                    cardId=card.id,
                    title=card.text,
                    body=body,
                    tags=card.tags,
                    wikiLinks=[],
                )
            )

    return curated, errors


def _fallback_direct_write(
    cards: list[RawCard], errors: list[CardError]
) -> list[CuratedCard]:
    """When LLM fails entirely, write cards directly without curation."""
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
            )
        )
    return result


def _merge_tags(existing: list[str], new: list[str]) -> list[str]:
    """Merge two tag lists, dedup, cap at 3."""
    seen = set()
    result = []
    for tag in list(existing) + list(new):
        if tag and tag not in seen:
            result.append(tag)
            seen.add(tag)
            if len(result) >= 3:
                break
    return result