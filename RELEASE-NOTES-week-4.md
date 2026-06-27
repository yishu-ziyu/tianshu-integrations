# Tianshu Integrations Week 4 Release Notes

Date: 2026-06-28
Branch: ship/tianshu-integrations-week-4-...
Status: SHIPPED - Week 1-4 complete

## What's in Week 4

Week 4 is the closing phase: E2E demo, error path coverage, performance baseline, documentation, and status updates across Feishu + Obsidian.

### T-24 + T-25: End-to-end demo + recording script

- API-only E2E demo verified (no GUI Chrome automation in this session)
- 3-card sync: 21s (Phase A + 3x Phase B)
- Phase B returned real wiki links: [[02 Wiki/linux-kernel]]
- 8 unique tags merged into frontmatter
- docs/RECORDING-WEEK-2-3-4.md: 6 scenarios + 12 error path matrix + recording tool recommendations

### T-27: Error path coverage (12 scenarios)

- E1: M2.1 non-JSON -> 4-layer fallback
- E2: M2.1 truncated JSON -> Layer 5 recovery
- E3: M2.1 markdown wrapped JSON
- E4: M2.1 array response (not object)
- E5: M2.1 thinking block stripped via extractContent
- E6: M2.1 returns null
- E7: Pydantic rejects empty text (Week 1 P3 #4 fix)
- E8: Pydantic rejects missing sourceUrl
- E9: Pydantic rejects invalid trigger
- E10: vault read-only (chmod 555) returns 400
- E11: vault = /etc returns 400 (Week 1 P2 security)
- E12: vault subdirectory of OBSIDIAN_VAULT allowed

Fix: schemas.py RawCard.text added min_length=1, max_length=500
Fix: conftest.py added _reset_obsidian_vault autouse fixture

### T-28: Performance baseline

- 1 card mock: ~250ms (target < 500ms) PASS
- 5 cards mock: ~680ms (target < 1s) PASS
- 100 cards mock: ~7.5s (target < 10s) PASS
- 5 concurrent sync: data preserved PASS
- 5 cards real M2.1: ~21s (target < 30s) PASS
- bridge startup: < 2s PASS

### T-29: README + INSTALL

- README updated with Week 2/3/4 sections
- INSTALL.md created (12-step guide)
- Status line: Week 1-4 全部 ship, 98 pytest pass

### T-30: Feishu + Obsidian status update

- Feishu record recvnGVDhdkmil: status -> 已完成
- Obsidian mirror page: Week 1-4 全部 ship + Week 4 milestone section

## Test Results

- 98 pytest pass, 4 skipped (real API), 2 warnings
- Deep Reader TypeScript: 8 files compile clean
- Deep Reader Vite build: 491ms, 25 modules, 0 errors

## Commit History (Week 4, 5 commits)

- 18cadd9 docs(week-4): T-30 fix README status line + Feishu + Obsidian
- ce66885 docs(week-4): T-29 README + INSTALL update
- 260e214 test+docs(week-4): T-28 performance baseline
- 086e882 test+fix(week-4): T-27 error path coverage + Pydantic fix
- 527fb0e docs(week-4): T-24+T-25 end-to-end demo + recording script

## Final Project State

- 2 联动全部完成 (Deep Reader quiz + Recall Sticker -> Obsidian)
- 98 pytest pass
- 12 error path scenarios covered
- 6 performance baselines established
- GitHub: yishu-ziyu/tianshu-integrations (public)
- Feishu: recvnGVDhdkmil status = 已完成
- Obsidian: ~/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md
