# Tianshu Integrations · Week 2 Release Notes

> **Release date**: 2026-06-27
> **Branch**: `ship/tianshu-integrations-week-2-8-t-minimax-client-curator-llm-p`
> **Status**: ✅ Shipped to local (T-13b deferred to Week 3)

---

## What's in Week 2

联动 2(Recall Sticker → Obsidian Vault)从 Week 1 的"mock LLM"升级为"真实 M2.1 智能整理"。Recall Sticker Side Panel 加了"🧠 同步到 Obsidian"按钮。

### Added

**bridge 端(Python)**:
- `tianshu_integrations/curator/prompts.py` — Phase A(批量打 tag + 合并建议)+ Phase B(per-card 双向链接)prompt 模板
- `tianshu_integrations/curator/curate.py` — **两阶段 curator**:
  - `curate_phase_a(cards, llm)` — 1 次 M2.1 call 拿 batch_tags + per-card card_tags + merges
  - `curate_phase_b(card, vault_notes, llm)` — per-card 1 次 M2.1 call 拿 wiki links
  - `scan_vault_existing_notes(vault_path)` — 扫 vault 已有的 .md 文件名作为 Phase B 候选
- `tianshu_integrations/llm/client.py` — 加 `extractContent()` 静态方法,strip M2.1/M3 的 ` ̶t̶h̶i̶n̶k̶...̶ ̶` reasoning blocks
- `tianshu_integrations/curator/parsers.py` — 加 **Layer 2**(trailing comma 容忍)+ **Layer 5**(truncated JSON recovery),以及 `_normalize` 支持 Week 2 schema(batch_tags/card_tags/merges/wikiLinks)
- `tianshu_integrations/obsidian/writer.py` — 加 **frontmatter merge on append**(Week 1 P3 #5 修复):`parse_frontmatter()` + `merge_frontmatter_tags()` + `render_frontmatter()`,同步时 frontmatter tags 是 union,不替换
- `tianshu_integrations/bridge/schemas.py` — `CuratedCard._wrap_wiki_links` 字段验证器自动给 wiki links 加 `[[ ]]` 包裹
- `tianshu_integrations/tests/test_llm_client.py` — 11 个 LLM client 测试(extractContent 6 + MockLLMClient 3 + MiniMaxClient 2)
- `tests/test_parsers.py` — 加 7 个 parser 健壮性测试
- `tests/test_writer.py` — 加 5 个 writer merge 测试
- `tests/test_curator.py` — 更新 whole-batch-failure 测试适配新 contract(返回空 errors,fallback 直接写)

**Recall Sticker 端(JavaScript)**:
- `lib/storage-collector.js` — `collectAllStickers()` 从 chrome.storage.local 拉所有贴纸,带 STORAGE_KEY_BLACKLIST
- `lib/obsidian-exporter.js` — `cardsToMarkdown()` 生成 byte-compatible .md(与 bridge 端 writer.py 格式一致)
- `lib/bridge-client.js` — `syncToBridge(cards, options)` 调 bridge,失败时降级 `chrome.downloads.download` + Blob URL(MV3 兼容)
- `lib/bridge-client.js` — `checkBridgeHealth()` pre-flight 检查
- `lib/bridge-client.js` — `collectAndSync(options)` 组合 `collectAllStickers` + `syncToBridge`
- `sidepanel.html` — 加 `#bridge-sync-bar`(vault path input + 同步按钮 + 状态显示 div)
- `sidepanel.js` — 加 ~70 行 sync button handler,加载/保存 vault path 到 chrome.storage,显示 4 种状态(syncing / synced / offline_fallback / error)

**Patches + Apply 脚本**:
- `patches/recall-sticker-sidepanel-v2.patch` — 125-line patch for sidepanel.html + sidepanel.js
- `patches/lib-files/{bridge-client,obsidian-exporter,storage-collector}.js` — 新 lib 文件直接 copy
- `scripts/apply-recall-sticker-week2-patches.sh` — idempotent apply 脚本(verified)

### Fixed (from Week 1 review)

- **P3 #5**: frontmatter tags 现在 append 时合并(Week 1 是新 sync 替换旧的)
- **P3 (new)**: parser 加 Layer 5 truncated JSON recovery,处理 M2.1 reasoning 输出被截断的情况
- **P3 (new)**: extractContent() 处理 M2.1/M3 的 ` ̶t̶h̶i̶n̶k̶...̶ ̶` 块,Week 1 parser 会因 thinking block 含 `{}` 而 fall back 到 naive tag extraction

### Changed

- `tianshu_integrations/curator/curate.py` — `curate()` 签名加 `vault_path: str | None = None` 参数(Week 2 Phase B 用)
- `tianshu_integrations/bridge/server.py` — `/sync/recall-sticker` 把 vault 路径透传给 curator

---

## Performance

| 操作 | 时间 | 备注 |
|---|---|---|
| 5 张卡 sync(真 M2.1 + Phase A + Phase B) | **34.5s** | 1 Phase A call + 5 Phase B calls + 推理 overhead |
| 2 张卡 sync(真 M2.1 + Phase A + Phase B,vault 已 seed 3 .md) | **16.6s** | Phase B 返回 `[[02 Wiki/linux-kernel]]` 等真双向链接 |
| 1 张卡 mock curator | < 50ms | (Week 1 不变) |
| 100 张卡 mock curator | ~10ms | (Week 1 不变) |
| 5 并发 sync | 数据全保留 | (Week 1 fcntl 验证,Week 2 同样 work) |

---

## Critical Finding from Day 1 Research

**MiniMax-M2.1 和 M3 都是 reasoning 模型** — 它们在 content 字段输出 ` ̶t̶h̶i̶n̶k̶...̶ ̶/̶t̶h̶i̶n̶k̶` 块,然后才是实际响应。Week 1 的 `extractTextFromResponse` 假设 plain content,会失败。

**Fix**:加 `extractContent()` 函数,在 parse 之前 strip 思考块。同时加 `tests/test_llm_client.py` 覆盖这种格式。

**M3 vs M2.1 vs 协议矩阵**(实际测试结果):
| 模型 | OpenAI 协议 | Anthropic 协议 |
|---|---|---|
| MiniMax-M3 | ✅ + reasoning output | ✅ + reasoning output |
| MiniMax-M2.1 | ✅ + reasoning output | ✅ + reasoning output |

**T-13b 决策:跳过**。M3 双协议都支持,Deep Reader 当前 Anthropic + M2.1 配置仍然工作。推迟到 Week 3 跟 Deep Reader 出题一起改协议。

---

## Known Limitations (Deferred)

### P2 (Week 3 解决)
- **T-13b Deep Reader 协议统一**:Deep Reader 现在用 Anthropic 协议调 M2.1,跟 Tianshu Bridge 的 OpenAI 协议不一致。Week 3 改。

### P3 (backlog)
- **评测集**:BRAINSTORM §2.4 / ROADMAP §8 都明确"本次不做"。Week 3/4 跟 Deep Reader 评测共享基础设施时再做。
- **curl 验证 chrome.downloads MV3**:本 session 无 GUI,无法跑真实 Chrome 自动化测试。但代码用 Blob URL(非 data URL),应该兼容 MV3。
- **Obsidian URL 双向链接建议准确率**:Phase B 靠 M2.1 建议,准确率不测量。Week 4 加评测集后再优化。

---

## Breaking Changes from Week 1

- `curate()` 签名变更:`curate(cards, llm_client)` → `curate(cards, llm_client, vault_path=None)`。Week 1 调用方必须更新(只有 server.py 一处,已更新)
- `tests/test_curator.py::test_curate_whole_batch_failure_returns_errors` 行为变更:Week 2 errors 是空 list(Phase A 失败 silent fallback),不再是每个 card 一条 error
- Chrome extension 用户必须 reload 扩展才能看到新的"🧠 同步"按钮(Week 1 patches 已在 Week 2 之前 apply 过 2 个;Week 2 加了 1 个 patch + 3 个新文件)

---

## Verification Evidence

```
$ pytest tests/ -q --tb=line
81 passed

$ MINIMAX_API_KEY=sk-cp-... tianshu-bridge --vault ~/Desktop/知识库 &
$ curl -X POST http://127.0.0.1:7733/sync/recall-sticker \
    -d '{"trigger":"manual","cards":[{5 cards}],"obsidianVaultPath":"~/Desktop/知识库"}'
{"success":true,"curated":[5 cards],"durationMs":34493,"obsidianFilesWritten":["Inbox/2026-06-27-recall.md"]}

$ ls -la ~/Desktop/知识库/知识库/Inbox/
-rw-r--r-- .recall-sync.lock (0 bytes)
-rw-r--r-- 2026-06-27-recall.md (594 bytes, 5 sections + 来源)
```

---

## Next Steps for User

1. **Reload Chrome Recall Sticker**:
   ```bash
   bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-week2-patches.sh
   ```
   然后 chrome://extensions → ↻ 重载 Recall Sticker

2. **Open Side Panel**:
   - 在 vault path input 里填 `~/Desktop/知识库/知识库`
   - 选一段文本创建贴纸
   - 点 "🧠 同步到 Obsidian"
   - 等 30 秒,Obsidian 出现新 .md

3. **Week 2 已 ship 状态更新**:
   - 飞书记录 `recvnGVDhdkmil`:状态改为"Week 2 已 ship"
   - Obsidian 项目页加 Week 2 状态

4. **Week 3 启动**:
   - T-13b(Deep Reader 协议统一)+ T-17 ~ T-23(联动 1 出题 + QuizPanel + MistakeStore + Anki 导出)
   - 预估 35h