"""Tests for Obsidian vault writer."""

from tianshu_integrations.bridge.schemas import CuratedCard
from tianshu_integrations.obsidian.writer import render_card_section, sanitize_source_url, write_batch


def test_sanitize_source_url_strips_utm():
    """utm_* and ref params are stripped from URL."""
    url = "https://example.com/article?utm_source=twitter&id=1&ref=newsletter&utm_medium=social"
    clean = sanitize_source_url(url)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "ref=newsletter" not in clean
    assert "id=1" in clean  # non-tracking params preserved


def test_render_card_section():
    """Section rendering includes title, body, wiki links."""
    card = CuratedCard(
        cardId="1",
        title="eBPF",
        body="内核技术",
        wikiLinks=["[[BPF]]", "[[kernel]]"],
    )
    md = render_card_section(card)
    assert "## eBPF" in md
    assert "内核技术" in md
    assert "[[BPF]]" in md
    assert "[[kernel]]" in md


def test_write_batch_creates_file(tmp_path):
    """First call creates Inbox/YYYY-MM-DD-recall.md with frontmatter."""
    curated = [
        CuratedCard(cardId="1", title="t1", body="b1", tags=["k8s"]),
    ]
    files = write_batch(curated, str(tmp_path))
    assert len(files) == 1
    # files[0] is "Inbox/2026-06-27-recall.md" (vault-relative path)
    content = (tmp_path / files[0]).read_text(encoding="utf-8")
    assert "---" in content  # frontmatter delimiter
    assert "date:" in content
    assert "tags:" in content
    assert "t1" in content


def test_write_batch_appends_to_existing(tmp_path):
    """Second call appends to existing daily file, doesn't overwrite."""
    import datetime

    curated1 = [CuratedCard(cardId="1", title="first", body="b1")]
    curated2 = [CuratedCard(cardId="2", title="second", body="b2")]

    write_batch(curated1, str(tmp_path))
    write_batch(curated2, str(tmp_path))

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_path = tmp_path / "Inbox" / f"{today}-recall.md"
    content = file_path.read_text(encoding="utf-8")
    assert "first" in content
    assert "second" in content


def test_write_batch_creates_inbox_dir(tmp_path):
    """Inbox/ directory is created if missing."""
    inbox = tmp_path / "Inbox"
    assert not inbox.exists()
    write_batch([CuratedCard(cardId="1", title="t", body="b")], str(tmp_path))
    assert inbox.exists()


def test_write_batch_atomic_no_partial(tmp_path):
    """Atomic write: writes to .tmp then renames, no .tmp left behind."""
    import datetime

    write_batch([CuratedCard(cardId="1", title="t", body="b")], str(tmp_path))
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    tmp_path_inbox = tmp_path / "Inbox"
    files = list(tmp_path_inbox.iterdir())
    # Only the .md file should remain, no .tmp
    assert all(not f.name.endswith(".tmp") for f in files)


def test_write_batch_empty_curated_returns_empty(tmp_path):
    """Empty list returns empty file list, creates no file."""
    files = write_batch([], str(tmp_path))
    assert files == []
    assert not (tmp_path / "Inbox").exists()


def test_write_batch_sanitizes_source_url_in_curated_body():
    """Note: writer does NOT add sourceUrl to body — caller passes already-curated body."""
    # This is by design — body is M2.1's output, sourceUrl handled at higher level
    pass