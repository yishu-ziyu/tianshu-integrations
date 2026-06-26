# Diff Report · host spec vs peer spec

> **date**: 2026-06-27
> **task_id**: `roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini`

---

## 总体结论

| 维度 | host spec | peer spec | 是否冲突 |
|---|---|---|---|
| 可行性 | 9/10(基于 PM 文档) | **7/10**(基于独立调查) | ⚠️ peer 更悲观 |
| 主要盲点 | model name 错(M2.1 → M3) | manifest 没 host_permissions / protocol 分叉 / context prompt injection | peer 发现多个 host 漏掉的 P0 风险 |
| 30 T 任务排序 | 沿用 PM 4 周时间线 | 同意但**风险前移**:Week 1 加 T-04b (manifest 改) + T-05b (mock curator) | peer 提议加 2 个任务 |
| LLM 协议 | 没明确,默认用 ADR-004(OpenAI) | **必须明确,推荐 OpenAI** | ✅ 收敛到 OpenAI |
| Vault 配置 | CLI 启动锁 | 加 3 补充:默认 vault /health 比对 /reload 端点 | peer 提议加 `/config/reload` |

---

## 关键 divergences + 解决

### D-01 · `page-extractor.js` 不能字面 port(host 漏掉 P0)

**Host 立场**:ARCH §1 表格说"page-extractor.js 直接 port,99 行纯函数"。

**Peer 立场**:`page-extractor.js:9-99` 是 IIFE,内部用 `window.Readability` / `window.TurndownService`(页面级全局),而 Deep Reader 当前用 npm `@mozilla/readability`(`content-extractor.ts:3`)。**两者调用方式不同,不能字面 port**。只能 port **fallback 架构**(candidates 排序 + MIN_TEXT 阈值)。

**代码证据**:
- `page-extractor.js:15-19` 调 `window.Readability`
- `content-extractor.ts:3, 9-11` 调 `@mozilla/readability` (npm)

**Disposition:****conceded**(peer 正确)。我的 host spec §6.4 写"port focus-quiz 的 page-extractor.js 99 行,直接 inline" 是错的。**修正**:Deep Reader 用现有 `@mozilla/readability`(npm),**只**借鉴 focus-quiz 的 candidates 排序 + 三级 fallback 架构,不是字面拷贝。

### D-02 · Recall Sticker manifest 缺 host_permissions(host 漏掉 P0)

**Host 立场**:spec §11.3 写"manifest 加 host_permissions" 是常规改动,没标 P0。

**Peer 立场**:`Recall-Sticker/manifest.json:4-11` 只有 `activeTab/storage/sidePanel/tabs`,**没有 `host_permissions`**。**这意味着 F-14 bridge-client.js fetch 127.0.0.1:7733 会被 MV3 静默拦截**。Week 1 第一个会撞的墙。

**代码证据**:`manifest.json:4-11` 全列出。

**Disposition:****conceded**(peer 正确)。**修正**:
- T-04b "Recall Sticker manifest 加 host_permissions + downloads 权限" Week 1 D1 必做
- host spec §12.2 风险列表加 R14 "manifest 不改 = MV3 fetch 拦截"

### D-03 · LLM 协议分叉(Anthropic vs OpenAI) — host 没决断

**Host 立场**:spec §13 提到协议不一致但没明确选哪种。

**Peer 立场**:`minimax.ts:12, 92` 走 `/v1/messages`(Anthropic);bridge 端如果按 ADR-004 走 `/v1/chat/completions`(OpenAI),**两套 client 并存**。**统一走 OpenAI**。

**Disposition:****conceded**(peer 正确)。**决策**:
- bridge 端 MiniMax client:**OpenAI 协议**(`/v1/chat/completions`)
- Deep Reader 端:**改 minimax.ts** 改走 OpenAI 协议
- 评估影响:Deep Reader 当前 `AI 助手` 已有用户用,改动需谨慎;Phase 1 必改,不在 backlog

**新增 T-13b**(Week 2 D1,3h):"Deep Reader minimax.ts 协议统一(Anthropic → OpenAI) + 默认 model 改 `MiniMax-M3`"

### D-04 · MiniMax model 实际是 M3,不是 M2.1(host 没意识到)

**Host 立场**:PRD/ARCH 一直用 M2.1;我 spec §13 改成 M3 但没标影响。

**Peer 立场**:`minimax.ts:99` 写 `'MiniMax-M2.1'`,`openai_client.py:29` 写 `'MiniMax-M2.1'`,**代码默认 M2.1**。但用户用 Token Plan,**实际可用 M3**。代码不改成 M3,所有调用会失败。

**Disposition:****conceded**(peer 正确)。**修正**:
- bridge 端 model = `MiniMax-M3` 默认
- Deep Reader minimax.ts 默认 model 改 `MiniMax-M3`
- spec §13 表格更新,已写明

### D-05 · recall-sticker 卡片没有 `id` 字段,curator 需生成

**Host 立场**:spec §3.1 `RawCard.id: str | None` 当作可读字段。

**Peer 立场**:`content.js:49-56` 存的卡片 schema **没有 id 字段**,只有 `text/prefix/suffix/context/timestamp/sourceUrl` 6 个。curator 必须用 timestamp 字符串当 id(或生成 UUID)。

**Disposition:****conceded**(peer 正确)。**修正**:spec §3.1 `id` 字段明确"由 curator 生成,Recall Sticker 不存"。

### D-06 · Recall Sticker prefix/suffix 实际是 100 字符,不是 80

**Host 立场**:ARCH §3.1 注释 "上下文前缀(各 80 字符)"。

**Peer 立场**:`content.js:5` `PREFIX_SUFFIX_LENGTH: 100`。**实际 100 字符**。

**Disposition:****conceded**(peer 正确)。**修正**:spec §3.1 RawCard 注释改 100 字符。

### D-07 · context 字段可能为空 / 与 prefix+suffix 重复

**Host 立场**:spec §5.2 没特别处理 context 为空。

**Peer 立场**:`content.js:42` `saveSticker(text, prefix, suffix, context = "")` 默认空串;`getExportContext` 第 498 行 `clozeIndex === -1` 时返回全文,可能跟 prefix+suffix 拼起来差不多。**bridge 端 ObsidianWriter 必须先 `if not context: build from prefix + text + suffix`**。

**Disposition:****conceded**(peer 正确)。**修正**:spec §6.3 ObsidianWriter 加 context 兜底逻辑。

### D-08 · M2.1 prompt 注入风险(Anki Cloze `{{c1::...}}`)

**Host 立场**:没考虑过。

**Peer 立场**:context 字段含 `{{c1::text}}`,M2.1 看到可能误解成自己的 syntax,或被注入 prompt。

**Disposition:****conceded**(peer 正确)。**修正**:
- curator 送 M2.1 前先 `context.replace(/{{c1::(.*?)}}/g, '[$1]')`
- spec §5.2 流程加一步"curator prompt 预处理"

### D-09 · chrome.downloads API 需要 manifest 加 `downloads` 权限

**Host 立场**:spec §3.4 列了 vault path / sync time key,但**没列** downloads 权限。

**Peer 立场**:offline fallback 用 `chrome.downloads.download`,Recall Sticker manifest 当前没 `downloads` 权限。**必须加**。

**Disposition:****conceded**(peer 正确)。**修正**:T-04b 加 "manifest 加 `downloads` 权限"。

### D-10 · `focus-quiz` `sidepanel-logic.js` Question 字段缺 `expectedAnswer` / `rubric`

**Host 立场**:spec §3.3 抄 PRD 的 Question schema,只 8 字段。

**Peer 立场**:`sidepanel-logic.js:189-220` 实际有 10 字段(多 `expectedAnswer` + `rubric`,open 题用)。**PRD/ARCH 漏了**。

**Disposition:****conceded**(peer 正确)。**修正**:spec §3.3 Question 接口加 `expectedAnswer?` / `rubric?` 可选字段。

### D-11 · `normalizeP1Question` type 白名单只有 3 种(trap/counterfactual/transfer),不含 `open`

**Host 立场**:spec §3.3 列 4 种题型(含 open)。

**Peer 立场**:`sidepanel-logic.js:183-186` `type` 白名单 hardcode 只前 3 种,`open` 是独立 answerMode 分支。

**Disposition:****conceded**(peer 正确)。**修正**:spec §3.3 `QuestionType` 改为 3 种,`open` 走 `answerMode: 'open'` 分支(不是 type)。

### D-12 · Week 1 跳过 M2.1 是"省事但延后风险"

**Host 立场**:沿用 PM 4 周时间线,Week 1 跳过 M2.1。

**Peer 立场**:**风险前移**。Week 1 应该加 T-05b (4h) "curator 空骨架 + JSON parser + mock LLM",把 M2.1 prompt 风险提前到 Week 1 D4,而不是 Week 2 同时调 prompt + parser + 性能。

**Disposition:****conceded**(peer 部分正确)。**修正**:
- T-04b (2h) manifest 改,Week 1 D1
- T-05b (4h) mock curator 骨架,Week 1 D4
- 总计 Week 1 从 23h → 29h,稍多但风险前移

### D-13 · vault 路径校验 + 配置同步

**Host 立场**:ADR-003 "CLI 启动锁,Phase 1 不持久化"。

**Peer 立场**:用户是 PM,跑命令高摩擦。**加 3 补充**:① 默认 `--vault` 值;② `/health` 返回当前 vault,Recall Sticker 比对 chrome.storage;③ `/config/reload` 动态切换。

**Disposition:****conceded**(peer 正确)。**修正**:
- T-03 bridge CLI 加 `--vault` 默认值 `~/Desktop/知识库/知识库/`
- T-13b 加 `/health` 返回 `currentVault` 字段
- T-13c 留 `POST /config/reload` Phase 2 不实现

### D-14 · bridge 写 .md 用 atomic write 避免半文件

**Host 立场**:spec §6.3 写"追加到当日文件"。

**Peer 立场**:进程崩溃可能写半文件。**用 atomic write**(temp + rename)。

**Disposition:****conceded**(peer 正确)。**修正**:spec §6.3 加 `tmp = file_path + '.tmp'; tmp.write_text(...); tmp.rename(file_path)`。

### D-15 · chrome.storage key 命名空间隔离设计不当

**Host 立场**:spec §3.4 列了 key 命名空间。

**Peer 立场**:`sidepanel.js:46-48` `isStickerCollection = storageKey !== 'tags' && Array.isArray(value)`。**只要 array-typed key 都被当贴纸**。tianshu-integrations 加的 `mistake_log_v1` 是 array,会被**误读**成贴纸!

**Disposition:****conceded**(peer 正确)。**严重问题**。**修正**:
- T-04b 同时改 `sidepanel.js` 加 `STORAGE_KEY_BLACKLIST = new Set(['mistake_log_v1', 'lastSyncTime', 'obsidianVaultPath', 'tags'])`(或白名单,看哪个更稳)
- spec §3.4 警告:Deep Reader 错题本 `mistake_log_v1` 必须被 sidepanel.js 跳过

### D-16 · `obsidianVaultPath` / `lastSyncTime` 是 String/Number,不会被误读

**Host 立场**:没特别标注。

**Peer 立场**:这两个 key 不是 array,不会被 sidepanel.js 误读。**OK**。

**Disposition:****no change**。这两个 key 设计安全。

### D-17 · vault Inbox 文件夹不存在,bridge 启动时必须 mkdir

**Host 立场**:spec §6.3 写"写 vaultPath/Inbox/YYYY-MM-DD-recall.md"。

**Peer 立场**:vault 根目录**没有 Inbox 文件夹**(只有 01 Raw / 02 Wiki / 03 Projects / ...)。bridge 启动必须 `Path(vault) / 'Inbox' / .mkdir(exist_ok=True)`。

**Disposition:****conceded**(peer 正确)。**修正**:spec §6.3 加 `mkdir parents=True, exist_ok=True`。

### D-18 · 跨页面贴纸的 sourceUrl 标准化

**Host 立场**:默认用 `sticker.sourceUrl`(完整 URL)。

**Peer 立场**:content.js:30-32 storage key = `url.origin + url.pathname`,但 sourceUrl 存完整 URL。两者不一致。**bridge sync 时用完整 URL,但 curator 写 .md 时清理 utm_* 等追踪参数**。

**Disposition:****conceded**(peer 正确)。**修正**:
- storage-collector 传完整 sourceUrl 给 bridge
- ObsidianWriter 写 .md 时 `sourceUrl.replace(/[?&](utm_\w+|ref)=[^&]*/g, '')` 清理

### D-19 · Manifest 改的风险期

**Host 立场**:T-04b 简单改动。

**Peer 立场**:改 manifest 必须重载扩展,用户操作有摩擦。**Week 1 D1 做,留时间排查**。

**Disposition:****conceded**。**修正**:T-04b Week 1 D1 必做,后续工作不依赖 manifest 改就推迟验证。

### D-20 · MistakeStore LRU 估时严重偏低(3h → 6-8h)

**Host 立场**:T-22 估 3h。

**Peer 立场**:LRU 实现涉及读 / 分组 / 排序 / 裁剪 / 写回,至少 6-8h。

**Disposition:****conceded**(peer 正确)。**修正**:T-22 估时改 6h。

### D-21 · SPA 渲染延迟导致 Readability 失败(Week 1 没规划 mock)

**Host 立场**:E-1.2 边界条件覆盖了"Readability 失败",但**没说 SPA 场景**。

**Peer 立场**:SPA 路由切换时 document_idle 已触发,article 是 JS 渲染后才出现,Readability 抓不到。**需要 mock test** 验证 fallback。

**Disposition:****conceded**(peer 正确)。**修正**:
- T-30 新增"SPA 场景 E2E" 4h(Week 4)
- 测试 fixture: reactjs.org / vuejs.org 之类 SPA 站点

### D-22 · 跳过 M2.1 测不到 per-card 容错

**Host 立场**:per-card 容错在 Week 2 测。

**Peer 立场**:Week 1 跳过 M2.1 时只能测成功路径,失败路径 + per-card 容错**只有 Week 2 第一次测**。debug 矩阵爆炸。

**Disposition:****conceded**(peer 正确)。**修正**:T-05b mock curator 时**同时**测 per-card 容错(用 mock LLM 返回混合 success/error)。

### D-23 · bridge 启动后没监听 vault 路径变化

**Host 立场**:CLI 锁死。

**Peer 立场**:用户改 vault 后 bridge 不感知。

**Disposition:****deferred to Phase 2**。**Phase 1 接受这个折衷**,README 警告用户。

### D-24 · T-19 (QuizGenerator) 估时 6h → 8h

**Host 立场**:T-19 估 6h。

**Peer 立场**:要做 prompt + 调用 + normalizeP1Question + 边界情况,至少 8h。

**Disposition:****conceded**(peer 正确)。**修正**:T-19 估时改 8h。

### D-25 · T-17 (port page-extractor) 估时 4h → 6h

**Host 立场**:T-17 估 4h(直接 port)。

**Peer 立场**:不是简单 port,要重写 fallback 架构,至少 6h。

**Disposition:****conceded**(peer 正确)。**修正**:T-17 估时改 6h。

---

## 总结:已 patch 的 spec 改动

1. **§6.4 ContentExtractorV2 实现策略**:不字面 port focus-quiz,只 port fallback 架构(D-01)
2. **§11.3 manifest 改动**:T-04b 加 host_permissions + downloads,Week 1 D1 必做(D-02, D-09)
3. **§4.4 + §6 + 全部** LLM 协议统一为 OpenAI(/v1/chat/completions)(D-03)
4. **§4.4 + 全部** model 默认 `MiniMax-M3`(D-04)
5. **§3.1 RawCard**:id 由 curator 生成(D-05);prefix/suffix 注释改 100 字符(D-06)
6. **§6.3 ObsidianWriter**:加 context 兜底(D-07) + atomic write(D-14) + mkdir Inbox(D-17) + sourceUrl 清理追踪参数(D-18)
7. **§5.2 curator 流程**:加 prompt 预处理 `{{c1::...}}` → `[...]`(D-08)
8. **§3.3 Question**:加 `expectedAnswer?` / `rubric?` 可选字段(D-10);`QuestionType` 改 3 种,`open` 走 answerMode(D-11)
9. **§12.2 风险列表**:加 R14 "manifest host_permissions",R15 "协议分叉",R16 "context prompt 注入",R17 "SPA 渲染延迟"
10. **Roadmap T-04b / T-05b / T-13b 新增**:Week 1 风险前移任务(D-02, D-12, D-03)
11. **T-22 / T-17 / T-19 估时调整**:6h / 6h / 8h(D-20, D-25, D-24)
12. **§3.4 chrome.storage 命名空间**:加 T-04c "sidepanel.js 加 STORAGE_KEY_BLACKLIST"(D-15)
13. **T-30 新增 SPA E2E**(D-21)
14. **T-03 bridge CLI 加 `--vault` 默认值**;**T-13b /health 返回 currentVault**(D-13)
15. **T-22 mock LLM 时同时测 per-card 容错**(D-22)

## 没采纳的 peer 建议

- **§5.10 卸载清理路径**:Phase 1 Out of Scope(peer 也同意)
- **§5.2 API key 配置统一**:短期两个 key(Deep Reader chrome.storage + bridge env),Phase 2 收敛
- **§5.3 端口 7733 冲突**:peer 自己也说"不冲突保留",无改动

## 净增任务

| 新 T | 估时 | 阶段 |
|---|---|---|
| T-04b (manifest 改) | 2h | Week 1 D1 |
| T-05b (mock curator 骨架) | 4h | Week 1 D4 |
| T-04c (sidepanel.js blacklist) | 1h | Week 1 D2 |
| T-13b (minimax.ts 协议统一 + M3) | 3h | Week 2 D1 |
| T-30 (SPA E2E) | 4h | Week 4 |
| T-22 估时调整 | +3h | Week 3 |

**Week 1 总估时**:23h → 30h (+7h)
**Week 2 总估时**:33h → 36h (+3h)
**Week 3 总估时**:29h → 32h (+3h)
**Week 4 总估时**:28h → 32h (+4h)
**总估时**:113h → 123h (+10h, +9%)

权衡:多 10h 把 5 个 P0 风险前移,debug 矩阵降低,**净赚**。

## escalated (无)

零 escalated。peer 没需要用户决策的点。

## ready for plan 阶段

✅ 所有 divergence 已 conceded / patched。spec.md 是合并版本。Plan 阶段开始。