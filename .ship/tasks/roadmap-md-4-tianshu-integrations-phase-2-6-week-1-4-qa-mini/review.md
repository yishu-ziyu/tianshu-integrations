# Code Review · Tianshu Integrations Week 1

> **task_id**: `roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini`
> **date**: 2026-06-27
> **reviewer**: host (self-review against spec + CLAUDE.md 12 rules)
> **scope**: 1 commit ship/roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini (25 files, 1517 lines)

---

## Findings

### P2: sourceUrl missing from .md — user loses traceability
- **File**: `tianshu_integrations/obsidian/writer.py:24-30` (function `render_card_section`)
- **Trigger**: Sync any card → open `vault/Inbox/<date>-recall.md`
- **Observation**: The rendered Markdown contains only `## title`, body, and `相关:` wikiLinks. The original `sourceUrl` from Recall Sticker (which the user explicitly chose to remember) is not included anywhere in the .md.
- **Impact**: User sees a curated note but cannot trace back to the original webpage. Defeats the entire purpose of recall-sticker (remembering things from pages you've read).
- **Spec violation**: `plan.md` §6.3 explicitly shows the .md template should include `来源: {{sourceUrl}}` (e.g., the ObsidianWriter.render_card_section docstring or test fixtures).
- **Fix direction**: Either add `sourceUrl` to the `CuratedCard` schema (preferred — M2.1 may want to keep or modify URL) and render it, OR add a separate "Metadata" line per card section.

### P2: Concurrent /sync calls race → data loss
- **File**: `tianshu_integrations/obsidian/writer.py:33-71` (function `write_batch`)
- **Trigger**: Two concurrent `/sync/recall-sticker` calls within the same day
- **Observation**: Both calls read existing file, append their content, write to `.tmp`, rename. If call A reads at t=0, call B reads at t=0+ε (before A's rename), B sees old content (no A's data). Then both write; B's rename lands after A's → A's content lost.
- **Impact**: User loses one batch of synced cards. Silent — no error message, .md just doesn't contain all data.
- **Fix direction**: Add `fcntl.flock(LOCK_EX)` around read+write+rename, OR rotate per-batch with timestamp suffix (`<date>-recall-<timestamp>.md` and merge on startup).
- **Severity rationale**: P2 not P1 because (a) Recall Sticker UI doesn't currently allow concurrent sync, (b) most users don't run cron, (c) error manifests as "missing cards in .md" which user notices on review.

### P2: /sync accepts arbitrary vault path from request body
- **File**: `tianshu_integrations/bridge/server.py:50-107` (function `sync_recall_sticker`)
- **Trigger**: Bridge runs on default 127.0.0.1:7733; attacker on same machine POSTs to /sync with `obsidianVaultPath: "/etc/"` or `/Users/victim/Documents/`
- **Observation**: The endpoint validates that the path is a writable directory but does not check it is INSIDE the bridge's configured vault (set via env `OBSIDIAN_VAULT` at startup).
- **Impact**: On a single-user machine, risk is low (attacker needs local access). But if user accidentally binds to `0.0.0.0` (e.g., `tianshu-bridge --host 0.0.0.0`), anyone on the LAN can write arbitrary files to writable paths on the machine.
- **Fix direction**: Validate `req.obsidianVaultPath == os.environ["OBSIDIAN_VAULT"]` (exact match) OR `Path(req.obsidianVaultPath).resolve().is_relative_to(Path(env_vault).resolve())` (subdirectory check). If mismatch → 400.

### P3: Pydantic accepts empty `text` field
- **File**: `tianshu_integrations/bridge/schemas.py` (class `RawCard`)
- **Trigger**: Client sends `{"text": "", "sourceUrl": "...", "timestamp": 1}`
- **Observation**: `RawCard.text: str` has no `min_length=1` constraint. Empty text accepted. Server then writes an empty section to .md (`## \n\n\n`).
- **Impact**: Useless .md section, pollutes vault, no error returned to caller. Recall Sticker UI doesn't allow this, but a malicious or buggy client could.
- **Fix direction**: Add `Field(..., min_length=1)` to `text`, optionally `max_length=200` (Recall Sticker max text length).

### P3: tags frontmatter uses curated tags only — drops the "recall-sticker" tag from existing files
- **File**: `tianshu_integrations/obsidian/writer.py:54-55`
- **Trigger**: Second sync on same day appends to existing file
- **Observation**: When file already exists, `existing` is read as-is (with its original frontmatter). The `all_tags` calculation only runs for NEW files. This is correct behavior (preserves the original tags), but if user wants to add a tag from a new batch, they'd need to manually edit the frontmatter.
- **Impact**: Tags added later don't appear in frontmatter (they DO appear in body though).
- **Fix direction**: Either document this as by-design, OR compute merged tags on every write.
- **Severity rationale**: P3 because it's a UX nit, not a bug — body sections always have their tags via `## title`.

---

## Items checked and OK

- ✅ `MiniMaxClient()` raises `KeyError` if env unset → caught at `server.py:86` → mock fallback. Safe.
- ✅ Anki Cloze `{{c1::...}}` is sanitized before M2.1 prompt — prompt injection prevented.
- ✅ Atomic write via `.tmp` + rename prevents half-written files (test `test_atomic_write_no_temp_files` passes).
- ✅ Inbox directory auto-created if missing (test passes).
- ✅ Per-card isolation in curator: one card's failure doesn't block the batch (test `test_curate_per_card_isolation` passes).
- ✅ `isStickerCollection` blacklist patch for Recall Sticker prevents cross-extension data leak.
- ✅ Vault path validation in CLI: exits 1 if vault doesn't exist or isn't writable (test passes).
- ✅ Manifest host_permissions patch enables bridge fetch (otherwise MV3 would silently block).
- ✅ 56 tests pass (43 unit + 13 E2E).
- ✅ E2E smoke verified real bridge startup + real HTTP calls + real .md writes.

---

## Diagnosis

Two findings share a root cause: the bridge trusts the request body for path/file operations.

- **P2 (sourceUrl missing)** — writer doesn't take ownership of metadata; assumes the curator kept it, but the schema doesn't preserve it.
- **P2 (race condition)** — write_batch has no file-level transaction; relies on sequential single-user usage.
- **P2 (vault path trust)** — server validates vault path is writable but doesn't validate it's the configured vault.

**Common root cause**: bridge makes implicit trust assumptions about caller behavior (single user, no concurrent calls, no malicious paths). The spec calls out "manual启服务 (推荐)" — meaning the user is the only caller. But the design should still enforce what it assumes.

---

## Open questions

- Should `trigger: "auto_on_save"` actually trigger anything in Week 1? Current code accepts the field but doesn't differentiate behavior. Spec calls for Phase 2.
- Should the bridge expose a "list synced files" endpoint for the user to verify state? Currently they must open Obsidian directly.

---

## Recommendation

**Fix the P2s before merge to Phase 2.** The P3s can ship as-is and be addressed in Week 2:
1. Add sourceUrl to .md rendering (5 line change in writer.py)
2. Add file lock to write_batch (10 line change)
3. Add vault path equality check to /sync (3 line change)

If user wants faster turnaround, fix only P2#3 (vault path trust) and defer others.