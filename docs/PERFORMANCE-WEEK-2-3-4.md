# Tianshu Integrations · Performance Baseline

> **date**: 2026-06-28
> **scope**: Week 2-4 cumulative performance baselines

---

## Test Results (Week 4 T-28)

| Test | Target | Actual | Status |
|------|--------|--------|--------|
| 1 card mock | < 500ms | ~250ms | ✅ |
| 5 cards mock | < 1s | ~680ms | ✅ |
| 100 cards mock | < 10s | ~7.5s | ✅ |
| 5 concurrent sync | data preserved | ✓ | ✅ |
| 5 cards real M2.1 | < 30s | ~21s (Week 3 demo) | ✅ |
| bridge startup | < 2s | ✓ | ✅ |

## Real M2.1 Performance (Week 3 demo)

| Cards | Time | Per-card |
|-------|------|----------|
| 1 | 9s | 9s (Phase A + Phase B) |
| 2 | 16.6s | 8.3s |
| 3 | 21s | 7s |
| 5 | 22.5s | 4.5s |
| 8 | 22.5s (real demo) | 2.8s |

**Observation**: Per-card time decreases with batch size (Phase A overhead amortizes). 20 cards estimated ~40-50s — over Week 1's 30s target.

## Recommendations

- **Accept current performance** for typical use (1-10 cards)
- **Optimize Phase B** for large batches (>10 cards) by:
  - Batching M2.1 calls (1 per 5 cards)
  - Caching recent wiki-link suggestions
  - Skipping Phase B for cards with no sourceUrl
