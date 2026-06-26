"""Obsidian Vault writer.

Writes curated cards to vault/Inbox/YYYY-MM-DD-recall.md with:
- YAML frontmatter (date, tags, source)
- Atomic write (tmp + rename) to prevent partial files
- Append to existing daily file (don't overwrite)
"""

import re
from datetime import datetime
from pathlib import Path

from tianshu_integrations.bridge.schemas import CuratedCard


SOURCE_URL_TRACKING_RE = re.compile(r"[?&](utm_\w+|ref)=[^&]*")


def sanitize_source_url(url: str) -> str:
    """Strip utm_* and ref tracking params from URL."""
    return SOURCE_URL_TRACKING_RE.sub("", url)


def render_card_section(card: CuratedCard) -> str:
    """Render a curated card as Markdown section."""
    md = f"## {card.title}\n\n"
    md += f"{card.body}\n\n"
    if card.wikiLinks:
        md += f"相关: {' '.join(card.wikiLinks)}\n\n"
    return md


def write_batch(curated: list[CuratedCard], vault_path: str) -> list[str]:
    """Write curated cards to vault/Inbox/YYYY-MM-DD-recall.md.

    Returns list of vault-relative file paths written.

    Atomic write: writes to .tmp file then renames (avoids partial files
    if process crashes mid-write).
    """
    if not curated:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = Path(vault_path) / "Inbox" / f"{today}-recall.md"

    # Ensure Inbox directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Build frontmatter + existing content
    if file_path.exists():
        existing = file_path.read_text(encoding="utf-8")
    else:
        # Collect all unique tags for frontmatter
        all_tags = sorted({t for c in curated for t in c.tags} | {"recall-sticker"})
        existing = (
            "---\n"
            f"date: {today}\n"
            f"tags: [{', '.join(all_tags)}]\n"
            "source: recall-sticker-sidepanel\n"
            "---\n\n"
            f"# Recall Sticker · {today}\n\n"
        )

    # Append new sections
    appended = existing + "\n---\n\n".join(render_card_section(c) for c in curated) + "\n"

    # Atomic write: tmp + rename
    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    tmp_path.write_text(appended, encoding="utf-8")
    tmp_path.rename(file_path)

    return [str(file_path.relative_to(vault_path))]