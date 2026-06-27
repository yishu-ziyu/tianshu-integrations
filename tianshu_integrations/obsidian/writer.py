"""Obsidian Vault writer.

Writes curated cards to vault/Inbox/YYYY-MM-DD-recall.md with:
- YAML frontmatter (date, tags, source) — tags MERGED on append (Week 2 fix)
- Atomic write (tmp + rename) to prevent partial files
- File lock (fcntl) to prevent concurrent writes from losing data
- Append to existing daily file (don't overwrite)
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tianshu_integrations.bridge.schemas import CuratedCard


SOURCE_URL_TRACKING_RE = re.compile(r"[?&](utm_\w+|ref)=[^&]*")
FRONTMATTER_DELIM = "---"


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
        # Obsidian wikilink format: [[path]] with space separator
        links_str = " ".join(card.wikiLinks)
        md += f"相关: {links_str}\n\n"
    if card.sourceUrl:
        # Preserve traceability — user picked this URL when creating the sticker
        md += f"来源: {sanitize_source_url(card.sourceUrl)}\n\n"
    return md


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, body_text). If no frontmatter, returns ({}, text).
    Simple YAML parser — handles `key: value` lines and `key: [a, b, c]` lists.
    """
    if not text.startswith(f"{FRONTMATTER_DELIM}\n"):
        return {}, text
    # Find the closing ---
    end_marker = f"\n{FRONTMATTER_DELIM}\n"
    end_idx = text.find(end_marker, 4)
    if end_idx < 0:
        return {}, text
    fm_text = text[4:end_idx]
    body = text[end_idx + len(end_marker):]

    fm: dict[str, Any] = {}
    for line in fm_text.strip().split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            # List: [a, b, c]
            items = [x.strip() for x in value[1:-1].split(",") if x.strip()]
            fm[key] = items
        else:
            fm[key] = value
    return fm, body


def merge_frontmatter_tags(existing_fm: dict[str, Any], new_tags: list[str]) -> dict[str, Any]:
    """Merge new_tags into existing_fm['tags']. Dedup, preserve order.

    Returns updated frontmatter dict.
    """
    existing_tags = existing_fm.get("tags", [])
    if isinstance(existing_tags, str):
        # Handle legacy "tags: a, b, c" format
        existing_tags = [t.strip() for t in existing_tags.split(",") if t.strip()]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    # Dedup preserving order: existing tags first, then new ones
    seen = set(existing_tags)
    merged = list(existing_tags)
    for tag in new_tags:
        if tag and tag not in seen:
            merged.append(tag)
            seen.add(tag)
    return {**existing_fm, "tags": merged}


def render_frontmatter(fm: dict[str, Any]) -> str:
    """Render frontmatter dict to YAML string."""
    lines = [FRONTMATTER_DELIM]
    for key, value in fm.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append(FRONTMATTER_DELIM)
    return "\n".join(lines) + "\n\n"


def write_batch(curated: list[CuratedCard], vault_path: str) -> list[str]:
    """Write curated cards to vault/Inbox/YYYY-MM-DD-recall.md.

    Returns list of vault-relative file paths written.

    Uses fcntl file lock to prevent concurrent writes from losing data
    (e.g., two /sync calls in the same day losing one batch).

    Atomic write: writes to .tmp file then renames (avoids partial files
    if process crashes mid-write).

    Week 2: if file exists, MERGE frontmatter tags (not replace).
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
            existing_text = file_path.read_text(encoding="utf-8")
            existing_fm, body = parse_frontmatter(existing_text)
            # Week 2 fix: MERGE frontmatter tags (not replace)
            all_new_tags = sorted({t for c in curated for t in c.tags} | {"recall-sticker"})
            merged_fm = merge_frontmatter_tags(existing_fm, all_new_tags)
            fm_str = render_frontmatter(merged_fm)
            # Keep existing body as-is, append new sections
            base = fm_str + body
        else:
            # First write — generate from curated tags
            all_tags = sorted({t for c in curated for t in c.tags} | {"recall-sticker"})
            fm = {
                "date": today,
                "tags": all_tags,
                "source": "recall-sticker-sidepanel",
            }
            base = (
                render_frontmatter(fm)
                + f"# Recall Sticker · {today}\n\n"
            )

        # Append new sections
        appended = base + "\n---\n\n".join(render_card_section(c) for c in curated) + "\n"

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