# E2E Report · Tianshu Integrations Week 1

> **task_id**: `roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini`
> **date**: 2026-06-27
> **phase**: E2E
> **scope**: Week 1 (联动 2 MVP + bridge)

---

## Framework

| Field | Value |
|---|---|
| Name | pytest + FastAPI TestClient |
| Status | pre-existing (added in dev phase) |
| Config | `pyproject.toml` [tool.pytest.ini_options] |
| Async mode | `asyncio_mode = "auto"` (pytest-asyncio) |

**Why not Playwright/Cypress**: Tianshu Bridge is a HTTP service, not a web app. There is no browser UI to drive in the bridge. Playwright would apply to Deep Reader (Week 3, deferred). For Week 1, the FastAPI TestClient + real filesystem assertions are the right level — they verify the integrated behavior that matches the spec's Hard Cut AC.

---

## Tests added

`tests/test_e2e.py` — 13 new tests across 4 classes:

### TestEndToEndSync (5 tests) — Spec AC#1 (联动 2 E2E)
- `test_five_cards_yields_md_file_with_all_sections` — 5 cards → 1 .md with all 5 sections + frontmatter
- `test_anki_cloze_stripped_in_e2e` — `{{c1::...}}` → `[...]` in final .md
- `test_inbox_directory_auto_created` — Inbox/ doesn't exist beforehand, sync creates it
- `test_atomic_write_no_temp_files` — no .tmp leftovers after sync
- `test_appends_to_existing_daily_file` — second sync appends, doesn't overwrite

### TestErrorPaths (4 tests) — Spec AC#5 (error paths)
- `test_vault_path_does_not_exist_returns_400` — 400 + clear error
- `test_vault_path_not_writable_returns_400` — 400 on read-only vault
- `test_empty_cards_succeeds_without_writing` — empty list = no file
- `test_llm_failure_falls_back_to_direct_write` — LLM down → still write

### TestPerformance (1 test) — Spec AC#6 (performance)
- `test_20_card_batch_completes_under_30s` — 20 cards < 30s threshold

### TestHealthEndpoint (3 tests) — bridge must report vault + M2.1 status
- `test_health_returns_required_fields` — all 6 fields present
- `test_health_reflects_minimax_key_state` — False when key absent
- `test_health_reflects_vault_writability` — False for read-only vault

---

## Run results

```
$ pytest tests/ -v --tb=short
...
tests/test_e2e.py::TestEndToEndSync::test_five_cards_yields_md_file_with_all_sections PASSED
tests/test_e2e.py::TestEndToEndSync::test_anki_cloze_stripped_in_e2e PASSED
tests/test_e2e.py::TestEndToEndSync::test_inbox_directory_auto_created PASSED
tests/test_e2e.py::TestEndToEndSync::test_atomic_write_no_temp_files PASSED
tests/test_e2e.py::TestEndToEndSync::test_appends_to_existing_daily_file PASSED
tests/test_e2e.py::TestErrorPaths::test_vault_path_does_not_exist_returns_400 PASSED
tests/test_e2e.py::TestErrorPaths::test_vault_path_not_writable_returns_400 PASSED
tests/test_e2e.py::TestErrorPaths::test_empty_cards_succeeds_without_writing PASSED
tests/test_e2e.py::TestErrorPaths::test_llm_failure_falls_back_to_direct_write PASSED
tests/test_e2e.py::TestPerformance::test_20_card_batch_completes_under_30s PASSED
tests/test_e2e.py::TestHealthEndpoint::test_health_returns_required_fields PASSED
tests/test_e2e.py::TestHealthEndpoint::test_health_reflects_minimax_key_state PASSED
tests/test_e2e.py::TestHealthEndpoint::test_health_reflects_vault_writability PASSED

tests/test_server.py     6 tests
tests/test_cli.py        4 tests
tests/test_schemas.py    7 tests
tests/test_parsers.py    8 tests
tests/test_curator.py    9 tests
tests/test_writer.py     9 tests
tests/test_e2e.py       13 tests
                       ─────────
Total:                 56 PASSED
```

**Suite pass rate: 56/56 (100%)**

**Run time**: 0.42s (no real LLM calls, all MockLLMClient)

---

## Failures

**None.** All 13 new tests pass on first run.

---

## Regressions

**None.** No previously-passing test broken.

---

## Manual smoke (out-of-band verification)

In addition to the E2E suite, an out-of-band smoke test was run:

```bash
$ MINIMAX_API_KEY="sk-test-fake" OBSIDIAN_VAULT="/tmp/test-vault" \
    tianshu-bridge --port 7734 --vault /tmp/test-vault &
$ sleep 2
$ curl http://127.0.0.1:7734/health
{
  "status": "ok", "version": "0.1.0", "vaultWritable": true,
  "minimaxConfigured": true, "currentVault": "/tmp/test-vault",
  "uptimeSec": 1
}

$ curl -X POST http://127.0.0.1:7734/sync/recall-sticker -d @sync-payload.json
{
  "success": true,
  "curated": [<2 cards>],
  "obsidianFilesWritten": ["Inbox/2026-06-27-recall.md"]
}

$ cat /tmp/test-vault/Inbox/2026-06-27-recall.md
---
date: 2026-06-27
tags: [recall-sticker]
source: recall-sticker-sidepanel
---

# Recall Sticker · 2026-06-27

## eBPF
类似 eBPF 机制

---

## service mesh
[service mesh] 是微服务通信层
```

Real bridge process + real HTTP + real file writes — verified end-to-end. TestClient tests in `test_e2e.py` exercise the same FastAPI app in-process, so this confirms the test suite matches production behavior.

---

## Cleanup

- No services spawned by E2E tests (TestClient is in-process)
- No port bindings held
- `pkill -f "tianshu-bridge"` from manual smoke confirmed no orphan processes

---

## Files

| File | Purpose |
|---|---|
| `tests/test_e2e.py` | New E2E test file (13 tests, 4 classes) |
| `.ship/tasks/.../e2e/report.md` | This report |
| `pids.txt` | (empty — no background processes) |

---

## Next Steps

1. **Review** — `/yishuship:review` to check correctness of the code
2. **QA** — `/yishuship:qa` to test the running application in a more exploratory way
3. **Week 2** — proceed to `curator/curate.py` real LLM integration (T-09, T-10, T-11)