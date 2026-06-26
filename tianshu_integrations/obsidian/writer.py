"""Obsidian Vault writer.

Writes curated cards to vault/Inbox/YYYY-MM-DD-recall.md with:
- YAML frontmatter (date, tags, source)
- Atomic write (tmp + rename) to prevent partial files
- File lock (fcntl) to prevent concurrent writes from losing data
- Append to existing daily file (don't overwrite)
"""

import os
import re
from datetime import datetime
from pathlib import Path

from tianshu_integrations.bridge.schemas import CuratedCard


SOURCE_URL_TRACKING_RE = re.compile(r"[?&](utm_\w+|ref)=[^&]*")


def sanitize_source_url(url: str) -> str:
    """Strip utm_* and ref tracking params from URL.

    Cleans up the leftover ? / & after stripping to keep the URL tidy.
    URL query parameters are all after the first '?' and separated by '&'.
    Stripping the first param (e.g., ?utm_source=tw) leaves '&id=42' which
    is invalid — replace the first leftover '&' with '?' if no '?' remains.
    """
    cleaned = SOURCE_URL_TRACKING_RE.sub("", url)
    # Collapse multiple '&' that may result from stripping
    cleaned = re.sub(r"&&+", "&", cleaned)
    # If we stripped the first param, the next '&' should be '?' instead
    if "?" not in cleaned and "&" in cleaned:
        cleaned = cleaned.replace("&", "?", 1)
    # Strip trailing ? / &
    cleaned = re.sub(r"[?&]$", "", cleaned)
    return cleaned


def render_card_section(card: CuratedCard) -> str:
    """Render a curated card as Markdown section."""
    md = f"## {card.title}\n\n"
    md += f"{card.body}\n\n"
    if card.wikiLinks:
        md += f"相关: {' '.join(card.wikiLinks)}\n\n"
    if card.sourceUrl:
        # Preserve traceability — user picked this URL when creating the sticker
        md += f"来源: {sanitize_source_url(card.sourceUrl)}\n\n"
    return md


def write_batch(curated: list[CuratedCard], vault_path: str) -> list[str]:
    """Write curated cards to vault/Inbox/YYYY-MM-DD-recall.md.

    Returns list of vault-relative file paths written.

    Uses fcntl file lock to prevent concurrent writes from losing data
    (e.g., two /sync calls in the same day losing one batch).

    Atomic write: writes to .tmp file then renames (avoids partial files
    if process crashes mid-write).
    """
    if not curated:
        return []

    # File lock to prevent race conditions across concurrent /sync calls
    try:
        import fcntl
    except ImportError:
        # Windows: fcntl unavailable. Skip lock (race condition may occur on Windows only)
        fcntl = None

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = Path(vault_path) / "Inbox" / f"{today}-recall.md"

    # Ensure Inbox directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Use lock file for fcntl (since rename is atomic on POSIX, locking the
    # target file path is sufficient — even if it doesn't exist yet, we lock
    # the directory's lock file)
    lock_path = file_path.parent / ".recall-sync.lock"
    lock_fd = open(lock_path, "w")
    if fcntl:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        except (OSError, AttributeError):
            pass  # Some FS don't support flock; skip

    try:
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
    finally:
        if fcntl:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except (OSError, AttributeError):
                pass
        lock_fd.close()

    return [str(file_path.relative_to(vault_path))]