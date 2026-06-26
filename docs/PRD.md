# PRD · 产品需求文档

> **代号**:Tianshu Integrations
> **版本**:v0.1(2026-06-27)
> **状态**:Phase 1 PM 调研完成

---

## 1. 背景

天枢(`~/Documents/trae_projects/api/`)包含两个核心系统:**Mini-Agent**(本地命令行 AI Agent)与 **Deep Reader**(Chrome MV3 网页降噪)。本项目解决天枢与既有工具 `focus-quiz`(网页认知压力测试)与 `recall-sticker`(网页贴纸抗遗忘)之间的联动问题。

### 1.1 用户痛点

| 痛点 | 当前 | 期望 |
|---|---|---|
| 读完一篇深度长文没有即时反馈 | Deep Reader 读完即走,过几天忘了 | 读完即做 3-5 道测验,答错自动沉淀 |
| 网页上贴的"我要记住"卡片散落在 Chrome storage | recall-sticker 只能导出 Anki,无法直接进 Obsidian | M2.1 自动整理 → 直接进 Obsidian 第二大脑 |
| 错题数据分散在多个 Chrome 扩展 | focus-quiz / 未来的 Deep Reader 错题不互通 | 命名空间隔离 + 各自独立,但 schema 对齐 |

### 1.2 机会窗口

四个项目都是 Chrome MV3(共享 `chrome.storage.local` / `fetch` API),且都依赖 MiniMax M2.1,**最自然的集成方式是在中间放一个 FastAPI bridge** 把 Mini-Agent 的 Python 能力(LLM client)暴露给 JS 扩展。

## 2. 用户画像与 JTBD

### 2.1 用户画像

**主用户**:奕枢(产品经理 / AI 工具重度用户)

| 属性 | 描述 |
|---|---|
| 角色 | PM,日常用 AI 工具辅助阅读、写作、调研 |
| 技术能力 | 不写代码,能跑命令行 |
| 工作流 | 浏览器阅读 → Obsidian 沉淀 → 飞书 / 飞轮跟踪 |
| 痛点 | 知识录入耗时;手动打 tag、双向链接;无法集中复习 |

### 2.2 JTBD(Job To Be Done)

> 当我**读完一篇深度长文 / 在网页上随手贴了多张"我要记住"的卡片**时,
> 我想**让 AI 自动整理成结构化的 Obsidian 笔记 + 即时出测验题帮我巩固**,
> 以便**我把时间花在思考上,而不是录入上**。

## 3. 目标与非目标

### 3.1 目标

- **G1**:用户在 Deep Reader 阅读面板内**一键启动测验**,3-5 道题 < 8s 出题,答错自动进错题本
- **G2**:用户在 recall-sticker Side Panel **一键同步**所有贴纸到 Obsidian,**1 分钟内**拿到结构化笔记
- **G3**:M2.1 智能整理(打 tag / 合并相似 / 双向链接)准确率 ≥ 80%
- **G4**:bridge 不可达时,Recall Sticker **自动降级**为本地 .md 下载,数据不丢
- **G5**:四件套 chrome.storage 命名空间隔离,**互不覆盖**

### 3.2 非目标

- 多 vault 并存(Phase 2)
- LaunchAgent 开机自启(Phase 2)
- 跨设备同步
- iOS / Android 客户端
- 实时联机多人测验
- focus-quiz 的 18 个 provider 抽象(只支持 MiniMax M2.1)
- 替换 Anki(只是导出兼容)

## 4. 用户故事与验收标准

### 4.1 联动 1 · Deep Reader + focus-quiz

| ID | 用户故事 | 验收标准 | 优先级 |
|---|---|---|---|
| **US-1.1** | 作为阅读者,我读完一篇文章后,想立即做 3 道测验 | Deep Reader 阅读面板有"📝 开始测验"按钮,点击后 < 8s 出题,渲染 QuizPanel | P0 |
| **US-1.2** | 我答错一道题,想它自动进错题本 | `chrome.storage.local.mistake_log_v1` 自动追加记录,字段含 question/userChoice/correct/explanation/sourceUrl/timestamp | P0 |
| **US-1.3** | 我想选择题型侧重(trap/counterfactual/transfer/open) | 测验开始前有题型选择 UI,可多选 | P1 |
| **US-1.4** | 我想导出当周错题成 Anki CSV | 错题本 UI 有"导出 Anki"按钮,生成标准 Anki Cloze CSV 触发 chrome.downloads | P1 |
| **US-1.5** | 我希望做完测验回到阅读面板,不丢失阅读位置 | QuizPanel 关闭后自动回到原 scroll 位置 | P0 |
| **US-1.6** | 同一篇文章可以多次出题 | 错题按 sourceUrl hash 累加,不覆盖 | P1 |
| **US-1.7** | Readability 抽取失败的页面也能出题 | 三级 fallback:Readability+Turndown → Readability+innerText → DOM innerText | P1 |

### 4.2 联动 2 · recall-sticker + Mini-Agent + Obsidian

| ID | 用户故事 | 验收标准 | 优先级 |
|---|---|---|---|
| **US-2.1** | 作为贴卡用户,我想一键把所有贴纸同步到 Obsidian | Side Panel 有"🧠 同步到 Obsidian"按钮,点击后 < 60s 内 Obsidian 看到新文件 | P0 |
| **US-2.2** | 我希望 M2.1 自动给每张卡打 1-3 个 tag | Obsidian .md 文件 frontmatter 含 `tags: [...]`,AI 打的 tag 用户可手动覆盖 | P0 |
| **US-2.3** | 我希望 M2.1 提示合并语义重复的卡片 | curator 输出 `merged[]` 字段,Side Panel 显示"已合并 X → Y" | P1 |
| **US-2.4** | 我希望新卡片自动建议双向链接到老卡片 | Obsidian .md 含 `相关: [[card-name]]`,建议来自 M2.1 | P1 |
| **US-2.5** | bridge 挂了,我至少能拿到 .md 文件 | bridge 不可达 → 自动触发 chrome.downloads 下载 .md,Side Panel 显示"bridge 不可达,已下载 .md" | P0 |
| **US-2.6** | 我希望 vault 路径配置一次,后续不需每次重输 | chrome.storage.local 持久化 `obsidianVaultPath`,bridge 启动时校验 | P0 |
| **US-2.7** | 我希望看到同步历史 | Side Panel 显示"上次同步: 3 分钟前 → ~/Desktop/知识库/Inbox/2026-06-27-recall.md" | P2 |
| **US-2.8** | 同步过程支持取消 | 同步中显示进度条 + 取消按钮 | P2 |

## 5. 功能拆解

### 5.1 联动 1 功能清单

| F-ID | 名称 | 文件 | 优先级 |
|---|---|---|---|
| **F-01** | port page-extractor.js 到 TypeScript + 加类型 | `deep-reader/src/lib/content-extractor-v2.ts` | P0 |
| **F-02** | 定义 quiz-types.ts(题型枚举 + Question/MistakeRecord schema) | `deep-reader/src/lib/quiz-types.ts` | P0 |
| **F-03** | 实现 QuizGenerator(M2.1 出题 prompt builder + 调用) | `deep-reader/src/lib/quiz-generator.ts` | P0 |
| **F-04** | 实现 MistakeStore(chrome.storage.local 持久化) | `deep-reader/src/lib/mistake-store.ts` | P0 |
| **F-05** | ReaderPanel 加"📝 开始测验"按钮 | `deep-reader/src/content/ReaderPanel.ts` | P0 |
| **F-06** | 实现 QuizPanel 组件(Shadow DOM 隔离) | `deep-reader/src/content/QuizPanel.ts` | P0 |
| **F-07** | Anki CSV 导出(port focus-quiz 格式) | `deep-reader/src/lib/anki-export.ts` | P1 |
| **F-08** | 题型选择 UI | `deep-reader/src/content/QuizPanel.ts` | P1 |

### 5.2 联动 2 功能清单

| F-ID | 名称 | 文件 | 优先级 |
|---|---|---|---|
| **F-09** | bridge FastAPI 服务 + 3 个 endpoint | `tianshu-integrations/bridge/server.py` | P0 |
| **F-10** | LLM client(MiniMax OpenAI 协议) | `tianshu-integrations/bridge/llm_client.py` | P0 |
| **F-11** | Curator(M2.1 智能整理:打 tag / 合并 / 双向链接) | `tianshu-integrations/bridge/curator.py` | P0 |
| **F-12** | ObsidianWriter(写 .md 到 vault,含 frontmatter) | `tianshu-integrations/bridge/obsidian_writer.py` | P0 |
| **F-13** | bridge CLI 入口(tianshu-bridge console script) | `tianshu-integrations/bridge/cli.py` | P0 |
| **F-14** | Recall Sticker 端 bridge-client(fetch 调用 + 离线 fallback) | `recall-sticker/Recall-Sticker/lib/bridge-client.js` | P0 |
| **F-15** | Recall Sticker 端 obsidian-exporter(本地 .md 生成,跟 bridge 端格式一致) | `recall-sticker/Recall-Sticker/lib/obsidian-exporter.js` | P0 |
| **F-16** | Recall Sticker 端 storage-collector(从 chrome.storage.local 拉所有贴纸) | `recall-sticker/Recall-Sticker/lib/storage-collector.js` | P0 |
| **F-17** | Side Panel 加"🧠 同步到 Obsidian"按钮 + vault path input + 状态显示 | `recall-sticker/Recall-Sticker/sidepanel.html`, `sidepanel.js` | P0 |

## 6. 优先级 (MoSCoW)

### Must Have (P0)
- F-01 ~ F-06(联动 1 核心)
- F-09 ~ F-17(联动 2 核心)

### Should Have (P1)
- F-07(Anki 导出)
- F-08(题型选择)
- F-03 合并相似 / F-12 双向链接(M2.1 整理的高级特性)

### Could Have (P2)
- F-08 vault 多 vault 支持(Phase 2)
- LaunchAgent 开机自启(Phase 2)
- 同步历史 UI(F-2.7)

### Won't Have (this phase)
- 跨设备同步
- 联机多人测验
- iOS / Android 客户端

## 7. 依赖与约束

### 7.1 内部依赖

| 依赖 | 说明 |
|---|---|
| Deep Reader (TS Chrome MV3) | 改动量 ~500 行 |
| Recall Sticker (JS Chrome MV3) | 改动量 ~280 行 |
| focus-quiz | **不直接改动**,只读源码复用 page-extractor.js / schema |
| Mini-Agent | **不直接改动**,只读源码借鉴 LLMClient 接口设计 |
| Obsidian Vault | 路径可写;frontmatter / wiki-link 规范按现有 vault |

### 7.2 外部依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python ≥ 3.10 | 系统 | bridge 服务 |
| FastAPI | latest | HTTP 服务 |
| uvicorn | latest | ASGI 服务器 |
| httpx | ≥ 0.27 | MiniMax API 调用 |
| pydantic | ≥ 2.0 | 数据模型 |
| Node.js ≥ 18 | 系统 | Deep Reader 构建 |
| Chrome ≥ 110 | 系统 | MV3 兼容 |

### 7.3 约束

- **bridge 必须用户手动启**(用户已确认)
- **M2.1 失败 = 优雅降级,不阻塞**用户主流程
- **chrome.storage key 命名空间隔离**(focus-quiz 用 `mistakeLog`,Deep Reader 用 `mistake_log_v1`,不互相覆盖)
- **不修改 focus-quiz 任何文件**(只 port 它已有的纯函数)

## 8. 成功指标 (KPI)

| KPI | 目标 | 测量方式 |
|---|---|---|
| 联动 1 出题 P95 延迟 | < 8s | console.log + 计时 |
| 联动 1 出题质量评分 | ≥ 4.0/5 | 用户答题后打分(1-5) |
| 联动 1 错题保留率(7 天) | ≥ 90% | chrome.storage.local 读取 |
| 联动 2 同步成功率(bridge 在线) | ≥ 95% | bridge log |
| 联动 2 M2.1 tag 准确率 | ≥ 80% | 人工 spot-check 50 张 |
| 联动 2 M2.1 合并建议采纳率 | ≥ 60% | Side Panel 反馈按钮 |
| 联动 2 Obsidian 写入成功率 | 100% | 文件存在性 + frontmatter 校验 |
| 离线 fallback 触发率 | < 10% session | bridge 日志 |

## 9. 引用

- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[Brainstorm|~/Developer/tianshu-integrations/docs/BRAINSTORM.md]]
- [[Architecture|~/Developer/tianshu-integrations/docs/ARCHITECTURE.md]]
- [[Roadmap|~/Developer/tianshu-integrations/docs/ROADMAP.md]]