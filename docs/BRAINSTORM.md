# BRAINSTORM · 脑暴记录

> **日期**:2026-06-27
> **目的**:在写 PRD 前,把两个联动的用户故事、边界、方案对比全部摊开

---

## 1. 联动 1 · Deep Reader + focus-quiz(读完长文 → 测验)

### 1.1 用户故事

**US-1.1**(核心)
> 作为深度阅读者,我读了一篇 5000 字的论文摘要,我想**立即在原页面**做 3-5 道测验确认我真的读懂了,而不是切到 Anki 再录入。

**US-1.2**(错题沉淀)
> 我答错了一道题,我想这道题自动进错题本,下次访问相关主题的文章能提醒我重做。

**US-1.3**(导出)
> 我想把一周的错题导出成 Anki CSV,导入到我的主力 Anki deck。

**US-1.4**(题型选择)
> 我想让测验侧重"反事实"(如果 X 相反会怎样)和"迁移"(X 在 Y 领域怎么应用),不要简单的"复述"题。

**US-1.5**(不打断阅读)
> 我希望做完测验后,阅读面板自动回到刚才的位置,不要让我重新找。

### 1.2 边界条件

| # | 条件 | 当前决策 |
|---|---|---|
| E-1.1 | 文章 < 200 字(太短) | 禁用测验按钮,提示"文章太短" |
| E-1.2 | Readability 抽取失败(反爬强站) | 用 DOM innerText 兜底,仍失败则禁用按钮 |
| E-1.3 | M2.1 返回非 JSON | 走 prompt 重试 1 次,仍失败提示"AI 出题失败" |
| E-1.4 | 用户在测验中途关闭面板 | 进度存 chrome.storage.local,重开可继续 |
| E-1.5 | 同一篇文章多次出题 | 错题本按 sourceUrl hash 累加,允许不同批次的题混存 |
| E-1.6 | focus-quiz 已存在同样的功能 | 我们的 `mistake_log_v1` 跟它的 `mistakeLog` 命名空间隔离,不互覆盖 |

### 1.3 方案对比

| 方案 | 工作量 | 体验 | 复用度 | 推荐 |
|---|---|---|---|---|
| **A. 极简版**:Deep Reader 加按钮 → 调 M2.1 出 3 道复述题 → 显示在 popup | 0.5 周 | ★★★ | 仅复用 M2.1 client | ❌ 题型太单一 |
| **B. MVP**:复用 focus-quiz 的 page-extractor.js + port 出题归一化 + 错题本 | 1.5 周 | ★★★★ | 9/10 | ⚠️ 可选 |
| **C. 完整版**(本次选):上面 + QuizPanel UI + Anki 导出 + chrome.storage 隔离 + 题型选择 | 2 周 | ★★★★★ | 9/10 | ✅ |

### 1.4 风险

- **Readability port 失败**:focus-quiz 是 IIFE UMD,Deep Reader 是 ESM,需要小幅改写 — **低风险**
- **M2.1 出题 JSON 不稳定**:需要严格 parser + fallback — **中风险**
- **QuizPanel 注入原页面样式冲突**:用 Shadow DOM 隔离 — **已缓解**

---

## 2. 联动 2 · recall-sticker + Mini-Agent + Obsidian(贴纸沉淀)

### 2.1 用户故事

**US-2.1**(核心)
> 我在阅读一篇 K8s 文档时,贴了 8 张"我要记住"的术语卡。我想**晚上回家**打开 Obsidian,**它们已经变成结构化笔记**,带 tag 和双向链接,而不是要我手动重新录入。

**US-2.2**(打 tag)
> 我希望 M2.1 帮我打 1-3 个 tag(比如 `#k8s #networking`),不要我自己想。

**US-2.3**(合并相似)
> 我贴了"service mesh"和"sidecar pattern",我希望 M2.1 提示我"这两张可能说的是同一件事,要合并吗?",而不是塞两篇笔记。

**US-2.4**(双向链接)
> 我之前贴过"eBPF"卡片,M2.1 应该建议在新卡片里加 `[[eBPF]]`,而不是每次重新解释。

**US-2.5**(失败回退)
> bridge 没起 / M2.1 挂 / 路径写错,我希望至少拿到一份 .md 文件,不至于丢数据。

**US-2.6**(不打断创建)
> 我贴卡片的动作必须 < 1 秒,智能整理是后台异步的,不要等我。

### 2.2 边界条件

| # | 条件 | 当前决策 |
|---|---|---|
| E-2.1 | bridge 进程没起 | Recall Sticker 自动降级为本地 .md 下载(`chrome.downloads`) |
| E-2.2 | vault 路径不存在 / 不可写 | bridge 启动时退出 1;Recall Sticker 端显示"路径错误,请检查" |
| E-2.3 | M2.1 timeout(>30s) | 单卡失败不阻塞整批,errors 字段返回该卡 |
| E-2.4 | 同一 prefix/suffix 的卡片已存在 | curator 去重,跳过;返回 `skipped[]` 字段 |
| E-2.5 | 用户同时维护多个 vault | Phase 1 不支持,bridge 启动时锁一个 vault 路径 |
| E-2.6 | 单次同步超过 100 张卡 | curator 分批处理(每批 20),避免 M2.1 prompt 超限 |
| E-2.7 | 用户中途取消 | bridge 用 `asyncio.CancelledError` 优雅退出,Recall Sticker 端显示"已取消" |
| E-2.8 | 卡片 context 太长(>2000 字) | 截断 prefix/suffix 到 200 字,保留 context 完整 |

### 2.3 方案对比

| 方案 | 工作量 | 体验 | 复用度 | 推荐 |
|---|---|---|---|---|
| **A. 文件轮询**:Recall Sticker 导出 .anki.txt,Mini-Agent 监听变化 | 1 周 | ★★★ | 5/10 | ❌ 不实时 |
| **B. MVP HTTP**:bridge 服务,只做"读 → 写 .md",无 M2.1 整理 | 1.5 周 | ★★★ | 8/10 | ⚠️ Phase 2 可先用 |
| **C. 完整版**(本次选):bridge + M2.1 curator + Obsidian writer + 离线 fallback | 2-3 周 | ★★★★★ | 9/10 | ✅ |

### 2.4 风险

- **bridge 部署摩擦**:用户必须手动启 — **中风险**(README + 启动脚本缓解)
- **M2.1 整理质量不稳**:可能打错 tag / 错误合并 — **高风险**(需要评测集 + prompt 迭代)
- **Obsidian 双向链接建议错误**:M2.1 不知道 vault 里有什么 — **中风险**(Phase 2 加 vault index 缓存)
- **chrome.downloads API 在某些公司电脑被禁**:离线 fallback 失效 — **低风险**(提前 README 警告)

---

## 3. 跨联动的横向取舍

### 3.1 bridge 部署位置

| 方案 | 优点 | 缺点 | 决定 |
|---|---|---|---|
| A. 独立项目 `~/Developer/tianshu-integrations/` | 职责单一,可独立测试,不影响其他仓 | 多一个 git 仓 | ✅ 选 |
| B. 塞进 Mini-Agent 主仓 | 改动小 | 耦合严重 | ❌ |
| C. 塞进 recall-sticker 主仓 | 少一个仓 | 引入 Python 依赖到 JS 项目 | ❌ |

### 3.2 M2.1 整理策略

| 方案 | 优点 | 缺点 | 决定 |
|---|---|---|---|
| A. 单卡独立整理 | 实现简单,失败隔离 | 不合并、不链接 | ❌ 体验差 |
| B. 批量整理 + 一次性输出 JSON | 一次 M2.1 调用,token 省 | 失败重试成本高 | ⚠️ 不选 |
| C. 两阶段:先批量打 tag + 合并,再单卡补双向链接 | 平衡 | 实现复杂 | ✅ 选 |
| D. 全量 vault index 喂 M2.1 | 链接准 | token 大,延迟高 | ❌ Phase 3 再考虑 |

### 3.3 错题本 / 卡片数据归属

| 方案 | 优点 | 缺点 | 决定 |
|---|---|---|---|
| A. 每个扩展存自己的 storage.local | 不互相干扰 | 分散管理 | ✅ 选 |
| B. 全聚合到一个 storage key | 统一管理 | 互相覆盖风险 | ❌ |
| C. 推到 bridge 端,扩展只缓存 | 统一持久化 | bridge 单点 | ❌ Phase 2 评估 |

## 4. 未来 backlog(本次不做)

- [ ] focus-quiz ↔ Deep Reader 错题聚合中心
- [ ] recall-sticker 与 focus-quiz 的"测验模式"整合(贴完卡片 → 自动出关于这些卡片的题)
- [ ] vault 多 vault 支持
- [ ] LaunchAgent 开机自启 bridge
- [ ] M2.1 整理的评测集
- [ ] bridge Web UI(看历史同步记录)
- [ ] 错题本可视化复习日历

## 5. 引用

- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[PRD|~/Developer/tianshu-integrations/docs/PRD.md]]
- [[Architecture|~/Developer/tianshu-integrations/docs/ARCHITECTURE.md]]
- [[Roadmap|~/Developer/tianshu-integrations/docs/ROADMAP.md]]