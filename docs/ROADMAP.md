# ROADMAP · 3-4 周实施路线图

> **代号**:Tianshu Integrations
> **日期**:2026-06-27
> **范围**:联动 1(Deep Reader + focus-quiz)+ 联动 2(recall-sticker + bridge + Obsidian)

---

## 1. 时间线总览

```
Week 1        Week 2        Week 3        Week 4
├─────────────┼─────────────┼─────────────┼─────────────┤
│ 联动 2 MVP  │ 联动 2 完整 │ 联动 1 实现 │ QA + 收尾    │
│ (优先做)    │ + 智能整理   │ (联动 1)    │             │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**为什么联动 2 先做**:用户痛点更尖锐(贴纸数据沉淀无解),且 bridge 基建一旦跑通,联动 1 的 M2.1 出题可以共用同一套基础设施。

---

## 2. 里程碑 (8 个 M)

| M-ID | 里程碑 | 验收标准 | 估计完成 |
|---|---|---|---|
| **M1** | 项目骨架 + bridge `/health` | `tianshu-bridge --port 7733` 启动,`curl /health` 返回 200 | Week 1 D2 |
| **M2** | bridge 接收卡片 + 写 .md(跳过 M2.1) | Recall Sticker 点按钮,Obsidian Inbox 出现 .md | Week 1 D5 |
| **M3** | Curator(M2.1 整理)+ ObsidianWriter | Obsidian .md 含 frontmatter/tags/双向链接 | Week 2 D3 |
| **M4** | Recall Sticker 联动完整(按钮 + 离线 fallback) | bridge 挂时自动 .md 下载,Side Panel 显示状态 | Week 2 D5 |
| **M5** | Deep Reader port page-extractor + QuizGenerator | "📝 开始测验" 按钮工作,3 题 < 8s 出题 | Week 3 D3 |
| **M6** | QuizPanel + MistakeStore + Anki 导出 | 答错自动进错题本,可导出 Anki CSV | Week 3 D5 |
| **M7** | E2E demo + 用户验收 | 两个联动端到端跑通,录屏 | Week 4 D2 |
| **M8** | QA + 收尾(README/INSTALL/ARCHITECTURE 更新) | 错误路径覆盖,性能基线,文档齐 | Week 4 D5 |

---

## 3. 任务清单 (18 个 T)

### Week 1 · 联动 2 MVP(优先)

| T-ID | 任务 | M | 文件 | 估时 |
|---|---|---|---|---|
| **T-01** | 建项目骨架 + pyproject.toml + console_script | M1 | `~/Developer/tianshu-integrations/{pyproject.toml,bridge/__init__.py}` | 2h |
| **T-02** | bridge FastAPI app + /health endpoint | M1 | `bridge/server.py` | 4h |
| **T-03** | bridge CLI 入口(tianshu-bridge) | M1 | `bridge/cli.py` | 2h |
| **T-04** | Pydantic schemas(RawCard/SyncRequest/Response) | M2 | `bridge/schemas.py` | 3h |
| **T-05** | POST /sync/recall-sticker endpoint(直写 .md,无 M2.1) | M2 | `bridge/server.py` | 4h |
| **T-06** | ObsidianWriter(简单版,无 frontmatter/tags) | M2 | `obsidian/writer.py` | 3h |
| **T-07** | Recall Sticker 端 storage-collector(从 chrome.storage 拉所有) | M2 | `recall-sticker/.../lib/storage-collector.js` | 2h |
| **T-08** | Recall Sticker 端 bridge-client(fetch 调用 + 错误处理) | M2 | `recall-sticker/.../lib/bridge-client.js` | 3h |

**Week 1 总估时**:23 小时 ≈ 3 个工作日

### Week 2 · 联动 2 完整 + 智能整理

| T-ID | 任务 | M | 文件 | 估时 |
|---|---|---|---|---|
| **T-09** | MiniMax OpenAI client(借鉴 mini-agent) | M3 | `llm/client.py` | 4h |
| **T-10** | Curator(两阶段整理:批量打 tag + 合并 + 单卡补链接) | M3 | `curator/curate.py` | 8h |
| **T-11** | Prompt 模板(curator/prompts.py) | M3 | `curator/prompts.py` | 4h |
| **T-12** | JSON 多层 fallback 解析(curator/parsers.py) | M3 | `curator/parsers.py` | 3h |
| **T-13** | ObsidianWriter 增强(frontmatter + tags + 双向链接) | M3 | `obsidian/{writer,frontmatter,naming}.py` | 4h |
| **T-14** | obsidian-exporter.js(本地 .md 生成,跟 bridge 格式一致) | M4 | `recall-sticker/.../lib/obsidian-exporter.js` | 3h |
| **T-15** | 离线 fallback 逻辑(bridge 不可达 → chrome.downloads) | M4 | `recall-sticker/.../lib/bridge-client.js` | 3h |
| **T-16** | Side Panel 加按钮 + vault path input + 状态显示 | M4 | `recall-sticker/.../sidepanel.html, sidepanel.js` | 4h |

**Week 2 总估时**:33 小时 ≈ 4 个工作日

### Week 3 · 联动 1 实现

| T-ID | 任务 | M | 文件 | 估时 |
|---|---|---|---|---|
| **T-17** | port page-extractor.js 到 TS(content-extractor-v2.ts) | M5 | `deep-reader/src/lib/content-extractor-v2.ts` | 4h |
| **T-18** | quiz-types.ts(Question/MistakeRecord schema) | M5 | `deep-reader/src/lib/quiz-types.ts` | 3h |
| **T-19** | QuizGenerator(buildPrompt + M2.1 调用 + normalizeP1Question) | M5 | `deep-reader/src/lib/quiz-generator.ts` | 6h |
| **T-20** | ReaderPanel 加"📝 开始测验"按钮 | M5 | `deep-reader/src/content/ReaderPanel.ts` | 2h |
| **T-21** | QuizPanel 组件(Shadow DOM 隔离 + 题/选项/答题/反馈) | M6 | `deep-reader/src/content/QuizPanel.ts` | 8h |
| **T-22** | MistakeStore(chrome.storage.local 持久化 + LRU) | M6 | `deep-reader/src/lib/mistake-store.ts` | 3h |
| **T-23** | Anki CSV 导出(port focus-quiz formatMistakesAsAnkiCsv) | M6 | `deep-reader/src/lib/anki-export.ts` | 3h |

**Week 3 总估时**:29 小时 ≈ 3.5 个工作日

### Week 4 · E2E + QA + 收尾

| T-ID | 任务 | M | 文件 | 估时 |
|---|---|---|---|---|
| **T-24** | 联动 2 E2E(从贴纸到 Obsidian 打开文件) | M7 | - | 4h |
| **T-25** | 联动 1 E2E(从读到测验到导出 Anki) | M7 | - | 4h |
| **T-26** | 录屏 + 用户验收 | M7 | - | 4h |
| **T-27** | 错误路径覆盖(bridge 挂 / M2.1 timeout / vault 路径错 / Readability 失败) | M8 | tests/ | 6h |
| **T-28** | 性能基线(出题 P95、同步 P95、bridge 内存) | M8 | tests/perf/ | 4h |
| **T-29** | README + INSTALL + 启动脚本 | M8 | `README.md`, `scripts/` | 4h |
| **T-30** | 飞书 base 状态更新 + Obsidian 镜像页 | M8 | 飞书 / Obsidian | 2h |

**Week 4 总估时**:28 小时 ≈ 3.5 个工作日

---

## 4. 总工作量

| Week | 任务数 | 总估时 |
|---|---|---|
| Week 1 | 8 | 23h |
| Week 2 | 8 | 33h |
| Week 3 | 7 | 29h |
| Week 4 | 7 | 28h |
| **总计** | **30** | **113h ≈ 14 个工作日** |

---

## 5. 风险与缓解

| # | 风险 | 触发阶段 | 缓解 |
|---|---|---|---|
| R1 | bridge 进程崩溃 → Recall Sticker 同步失败 | Week 1 | 自动降级 chrome.downloads(M2 已规划) |
| R2 | M2.1 返回格式不稳 | Week 2 | JSON 多层 fallback(T-12 已规划) |
| R3 | Obsidian vault 路径写错 | Week 1 | bridge 启动校验,T-05 二次校验 |
| R4 | chrome.storage 10MB 上限 | Week 3 | MistakeStore LRU ≤50/源(T-22 已规划) |
| R5 | focus-quiz 字段命名冲突 | Week 3 | `mistake_log_v1` 命名空间隔离 |
| R6 | M2.1 联网不通 | Week 2 | bridge 启动 ping api.minimaxi.com |
| R7 | Readability 失败(反爬强站) | Week 3 | 三级 fallback(T-17 已规划) |
| R8 | 用户改 vault 结构 | Week 4 | curator 严格按现有 vault 规范生成 |

---

## 6. 硬性完成标准 (Hard Cut)

| 指标 | 必须达到 |
|---|---|
| **联动 2 端到端跑通** | 用户贴 5 张卡 → 点按钮 → Obsidian 看到 .md 含 frontmatter + tags + 内容 < 60s |
| **联动 1 端到端跑通** | 用户读一篇 3000 字文章 → 点开始测验 → 3 题 < 8s 出现 → 答错 → 错题本有记录 |
| **离线 fallback 验证** | 手动 kill bridge → Recall Sticker 点按钮 → 拿到 .md 下载 |
| **Anki 导出验证** | 导出 .csv → 导入 Anki → 卡片正确显示 Cloze 格式 |
| **错误路径覆盖** | 单元测试覆盖 vault 路径错 / M2.1 timeout / Readability 失败 / chrome.storage 超限 4 类 |
| **性能基线** | 出题 P95 < 8s,批量同步 20 卡 P95 < 30s,bridge 内存 < 200MB |
| **文档齐** | README + INSTALL + Phase 0-1 文档全更新到飞书 + Obsidian |

---

## 7. Phase 边界(每个阶段必须有 visible deliverable)

| Phase | Visible Deliverable |
|---|---|
| Phase 1(本次已完成) | PROJECT_CHARTER + BRAINSTORM + PRD + ARCHITECTURE + ROADMAP(5 份 .md)+ 飞书 base + Obsidian 镜像页 |
| Phase 2(Week 1 D5) | **MVP 跑通**:桥接 + 写 .md(无 M2.1),Recall Sticker 端可同步 |
| Phase 3(Week 2 D5) | **M2.1 介入**:tag / 合并 / 双向链接,联动 2 完整 |
| Phase 4(Week 3 D5) | **联动 1 完整**:出题 + 答题 + 错题本 + Anki 导出 |
| Phase 5(Week 4 D2) | **E2E demo + 用户验收**,录屏 |
| Phase 6(Week 4 D5) | **QA + 收尾**:错误路径覆盖、性能基线、文档齐 |

---

## 8. 后续 backlog(本次不做)

- [ ] focus-quiz ↔ Deep Reader 错题聚合中心
- [ ] recall-sticker + focus-quiz 的"贴完卡片 → 自动出测验"整合
- [ ] vault 多 vault 支持
- [ ] LaunchAgent 开机自启 bridge
- [ ] M2.1 整理的评测集
- [ ] bridge Web UI(看历史同步记录)
- [ ] 错题本可视化复习日历

---

## 9. 引用

- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[Brainstorm|~/Developer/tianshu-integrations/docs/BRAINSTORM.md]]
- [[PRD|~/Developer/tianshu-integrations/docs/PRD.md]]
- [[Architecture|~/Developer/tianshu-integrations/docs/ARCHITECTURE.md]]