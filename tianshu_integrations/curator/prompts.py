"""Curator prompt templates for MiniMax M2.1 / M3 (OpenAI protocol).

Both models are reasoning models — they wrap thinking in <think>...</think>.
The prompt instructions below assume the parser has stripped thinking blocks
(see llm.client.extractContent) before attempting JSON parse.
"""

# Phase A: Batch-level tag + merge suggestions (1 M2.1 call for the whole batch)
PHASE_A_PROMPT = """你是知识整理助手。给定以下 recall-sticker 卡片:

{cards_text}

任务:
1. 为每张卡打 1-3 个 tag(英文小写或中文,语义化,不要直接用 text 本身)
2. 如果多张卡主题相同,在 merges 字段中标记(给出应该合并到哪张卡的 cardId)
3. 给 3 个 batch 级 shared tags(本批所有卡都相关)

返回严格 JSON,不要任何额外文字:
{{
  "batch_tags": ["tag1", "tag2", "tag3"],
  "card_tags": {{
    "<cardId>": ["tagA", "tagB"]
  }},
  "merges": [
    {{"source": "<cardId1>", "target": "<cardId2>", "reason": "相同概念"}}
  ]
}}"""

# Phase B: Single-card wiki link suggestions (per-card M2.1 call, reads vault)
PHASE_B_PROMPT = """你是知识整理助手。基于已有 Obsidian vault 笔记列表,建议这张卡的双向链接。

Vault 已有笔记(路径列表):
{existing_notes}

当前卡:
{card_text} | context: {card_context} | source: {card_source}

建议 1-3 个最相关的已有笔记(用 [[path]] 格式)。只返回 JSON:
{{"wikiLinks": ["[[path1]]", "[[path2]]"]}}"""

# Week 1 single-prompt fallback (kept for backwards compat or mock tests)
SINGLE_PROMPT = """你是知识整理助手。给定以下 recall-sticker 卡片:

{cards_text}

对每张卡返回 JSON:
{{
  "tags": ["tag1", "tag2"],
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


def build_phase_a_prompt(cards_text: str) -> str:
    """Build Phase A prompt from cards text."""
    return PHASE_A_PROMPT.format(cards_text=cards_text)


def build_phase_b_prompt(
    card_text: str,
    card_context: str,
    card_source: str,
    existing_notes: list[str],
) -> str:
    """Build Phase B prompt for a single card."""
    notes_str = "\n".join(existing_notes) if existing_notes else "(无已有笔记)"
    return PHASE_B_PROMPT.format(
        existing_notes=notes_str,
        card_text=card_text,
        card_context=card_context or "(无)",
        card_source=card_source or "(无)",
    )


def build_single_prompt(cards_text: str) -> str:
    """Build single-prompt for backwards compat."""
    return SINGLE_PROMPT.format(cards_text=cards_text)