# Peer Spec · Tianshu Integrations

> **独立调查结论:这个 ship 计划可行性 7/10,主要风险是 [Recall Sticker manifest 缺 host_permissions + Deep Reader / bridge 的 LLM 协议不一致 + bridge MVP 阶段跳过 M2.1 反而延后真正的整合风险发现]**。

> 这是 peer investigator 的独立调查,只读源文件和 PM 文档,没看 host 任何产出。报告里每条声明都给 `file:line` 证据,跟 PM 文档的差异直接标出,便于 Phase 2 设计前纠正。

---

## 1. 关键源文件核实(PM 文档声明 vs 实际代码)

### 1.1 focus-quiz · page-extractor.js

**PM 文档声明**(BRAINSTORM 1.2、ARCHITECTURE 1 / §4.1):
- "99 行纯函数,可直接 port"
- "Readability + Turndown 三级 fallback"
- "IIFE UMD,Deep Reader 是 ESM,需要小幅改写"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| 99 行纯函数可 port | **基本符合**,但**不是纯函数**:第 9 行 `(function() { ... })();` 是 IIFE,执行体直接调用 `document.cloneNode` / `window.Readability` / `window.location.href`(副作用);直接拷贝到 ESM 需去掉顶层 IIFE,改成 `export function extract()` | `page-extractor.js:9-99` |
| Mozilla Readability 抽取 | **符合**,用 `window.Readability`(需要 content script 通过 `<script>` 注入或 manifest 的 `web_accessible_resources` 让页面引入,不是 npm 的 `@mozilla/readability`) | `page-extractor.js:15-19` |
| Turndown 服务 | **符合**,同样需要页面级 `window.TurndownService`;Deep Reader 当前 `content-extractor.ts:3` 是 `import { Readability } from '@mozilla/readability'`(npm 包),**不**依赖 window 全局。**两种 Readability 用法不一致,这是隐性的实现分歧** | `page-extractor.js:25-32` 对比 `content-extractor.ts:3,9-11` |
| 三级 fallback | **部分符合**:Readability + Turndown → Readability + innerText → candidates-DOM(`article, main, [role="main"], ...`)排序。但**没有**第三级的"全文档 innerText"兜底;candidates 只看 article/main/body,正文是 article 失败就降级到 body 抽取 | `page-extractor.js:81-91` |
| MIN_TEXT 阈值 | `MIN_TEXT = 120`(line 11);PRD F-04 没明确阈值,只在 E-1.1 说 "< 200 字禁用" | `page-extractor.js:11` |
| MAX_CHARS 截断 | `MAX_CHARS = 12000`(line 10);M2.1 出题一般 8000-12000 字够用,但 PRD US-1.7 没明确上限 | `page-extractor.js:10,48` |

**关键风险**:**focus-quiz 用 `window.Readability`,Deep Reader 用 npm `@mozilla/readability`**。如果按 ARCH §4.1 字面 port,会出现"必须把 Readability.js 通过 web_accessible_resources 注入页面"的复杂副作用。**PM 文档没说怎么调和这俩**。建议:Deep Reader 直接复用 npm 版(content-extractor.ts 已有),**只** port focus-quiz 的"DOM innerText candidates 排序"逻辑(那才是真正缺失的部分)。

---

### 1.2 focus-quiz · sidepanel-logic.js

**PM 文档声明**:
- "normalizeP1Question" 是 port 的核心
- "题型侧重 trap/counterfactual/transfer"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| `normalizeP1Question` 函数位置 | 第 182-221 行;接受 `(rawQuestion, idx = 0)`,做类型白名单 + answerMode 分支 | `sidepanel-logic.js:182-221` |
| 字段约定 | 多 choice: `{ type, answerMode:'multiple_choice', question, options, correct, explanation, evidenceQuote, evidenceLocator, sourceHint }`;open 题多两个字段 `expectedAnswer`, `rubric`。**注意 PRD §3.5 的 Question schema 缺 `expectedAnswer` 和 `rubric`**(只列了 type/question/options/correct/explanation/evidenceQuote/evidenceLocator/sourceHint)。这是 port 时的小遗漏 | `sidepanel-logic.js:189-220` 对比 ARCH §3.5 |
| 允许的 type 白名单 | `['trap', 'counterfactual', 'transfer']`,**不含 `'open'` 和 PRD 提的 `'transfer'` 第 4 种**,但 `answerMode: 'open'` 独立分支。**PRD §3.5 列了 'trap'/'counterfactual'/'transfer'/'open' 4 种,而代码 hardcode 只接受前 3 种** | `sidepanel-logic.js:183-186` |
| `formatMistakesAsAnkiCsv` | 第 228-250 行,字段顺序 `Front,Back,Source,Evidence,Tags`,每条用 `csvCell` 加双引号转义;**注意 PRD US-1.4 的导出格式没有规定列顺序**,port 时应当沿用 focus-quiz 现有列定义以保持 Anki 兼容 | `sidepanel-logic.js:228-250` |
| 副作用 | 第 264 行 `globalThis.FocusQuizSidepanelLogic = ...`,第 267 行 `module.exports = ...` — **同时暴露给浏览器和 Node**,说明 focus-quiz 是真的把这套函数 unit test 跑过;Deep Reader port 时也应当保留 ESM 导出 + Node 单测能力(用于 BDD 阶段) | `sidepanel-logic.js:264-268` |
| P2 文章类型分类 | `classifyArticleForP2` + `buildP2PromptGuidance` 是 focus-quiz 的"个性化出题"能力,PRD 没提到 port 这部分,**但实际上对于"出题质量 ≥ 4.0/5" 这个 KPI 是关键**。如果只 port normalizeP1Question,出题质量难达标 | `sidepanel-logic.js:87-175` |

---

### 1.3 recall-sticker · content.js

**PM 文档声明**(ARCH §3.1 / §4.2):
- `RawCard` schema: `{ id, text, prefix, suffix, context, sourceUrl, tags, timestamp }`
- "Anki 导出函数签名"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| 卡片 schema | content.js saveSticker 第 49-56 行存的是 `{ text, prefix, suffix, context, timestamp, sourceUrl }`,**没有 `id` 字段**(没 UUID),也没有 `tags`(tags 单独存,见 sidepanel.js)。**PRD/ARCH 的 `id: str` 字段在 Recall Sticker 中不存在**,curator 需要在 sync 时**生成** id(用 timestamp 或 UUID),不能从 chrome.storage 读到 | `content.js:42-58` 对比 ARCH §3.1 `RawCard` |
| prefix/suffix 长度 | `PREFIX_SUFFIX_LENGTH = 100`(line 5),**实际 100 字符,不是 PRD/ARCH 写的 80**(ARCH §3.1 RawCard 注释只说"上下文前缀(各 80 字符)")。port 时需对齐:要么调 Recall Sticker,要么 PRD 改 100 | `content.js:5` vs `ARCH §3.1` |
| context 字段 | 含 Anki Cloze `{{c1::text}}` 的完整句子,由 `getExportContext()` 生成(第 480-523 行)。**该函数做的是"以 cloze 为锚,找最近的 .!?。！？\n 边界,返回完整一句"**,不是整段。所以 PRD E-2.8 说 "卡片 context 太长(>2000 字)截断 prefix/suffix 到 200 字",这里 context 不一定长(它就是单句) | `content.js:480-523` |
| Anki 导出函数 | `App.exportToAnki()`(第 734-768 行),**不是单独的可重用函数**。它直接构造 CSV 字符串 + 用 `<a download>` 触发下载,不暴露给外部。如果要给 bridge-client.js 复用,**需要重构**成纯函数 `buildAnkiCsv(stickers)`,或者用 chrome.downloads API 重写 | `content.js:734-768` |
| storage key 命名 | `url.origin + url.pathname`(第 30-32 行),**不含 query string / hash**。但 `sourceUrl` 字段存的是 `window.location.href`(完整 URL)。**这两个不一致意味着同一篇文章不同 query 的贴纸都进同一个 bucket,但 sourceUrl 跨页面可能重复** | `content.js:30-32,55` |
| 去重逻辑 | `saveSticker` 第 46 行 `(s) => s.text === text && s.prefix === prefix && s.suffix === suffix` 去重;但 **context 字段不参与去重**,意味着同一句贴两次(不同 DOM 操作)可能产生两条 | `content.js:45-48` |

---

### 1.4 recall-sticker · sidepanel.js / sidepanel.html

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| chrome.storage 读法 | `chrome.storage.local.get(null, ...)`(第 163 行),然后遍历所有 key;`isStickerCollection(url, value)` 判定 `storageKey !== 'tags' && Array.isArray(value)`。**这意味着只要 chrome.storage 里有任何 array-typed key,都会被当贴纸**。tianshu-introductions 如果新加 `obsidianVaultPath` 是字符串,不会被误判;但如果新加 `mistakeLog`(与 Deep Reader 错题本同名),会被误读成贴纸集合! | `sidepanel.js:46-48,162-179` |
| 按 URL 分 key 存? | content.js 写是按 URL 分;**sidepanel.js 用 get(null) 拉所有后聚合,不分页**。Phase 2 拉 1000 张贴纸性能可能爆,但当前 UX 设计就没考虑分页 | `sidepanel.js:162-179` |
| host_permissions 状态 | **Recall Sticker manifest.json (line 4-11) 只有 `activeTab/storage/sidePanel/tabs`,没有 host_permissions 也没有 `scripting` 权限**。**这意味着 recall-sticker/content.js 当前完全无法 fetch 任何外部 URL**。PRD/ARCH §3.4 设计的 `bridge-client.js` fetch `127.0.0.1:7733` 必须先**修改 manifest.json**,否则 MV3 的 `chrome.webRequest`/fetch 拦截会失败 | `Recall-Sticker/manifest.json:4-11` |
| sidepanel.html 结构 | 没有 vault path input / "同步到 Obsidian" 按钮 / bridge 状态显示(只有 refresh/reveal/tag/multi-select 这 4 个按钮)。F-17 需要从 0 开始加 | `sidepanel.html:9-18` |

---

### 1.5 deep-reader · content-extractor.ts

**PM 文档声明**(ARCH §4.1):
- "port 自 focus-quiz"
- "三级 fallback:Readability+Turndown → Readability+innerText → DOM innerText"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| 当前能力 | **已经在用 `@mozilla/readability`**(npm 包),不依赖 `window.Readability`;**已经实现了 article 抽取 + cleanContent (script/style/nav/footer/... 移除) + 段落拼接 + 字数统计 + readingTime**。**不是简单 wrapper,有自己的一套内容清理逻辑** | `content-extractor.ts:1-97` |
| 与 focus-quiz 的关系 | focus-quiz page-extractor.js 走 `window.Readability` + `window.TurndownService`(都是页面级 CDN 注入);Deep Reader 走 npm 包,无 Turndown。**两个项目用的是不同的 Readability 调用方式,不可能直接 port focus-quiz 的代码**;最多 port focus-quiz 的 candidates 排序(article/main/role=main/...)和 MIN_TEXT 阈值思想 | `page-extractor.js:15-32` vs `content-extractor.ts:3,9-11` |
| 三级 fallback | **Deep Reader 当前只有 1 级**(Readability),失败就返回 `null`(第 13 行)。**focus-quiz 有完整 3 级 fallback**。这是 port 的真正价值,但 PM 文档说"复用 page-extractor.js"会让人误以为只是搬 Readability 调用,实际上要搬的是 fallback 架构 | `content-extractor.ts:7-36` 对比 `page-extractor.js:14-99` |
| ExtractedContent schema | 第 21-31 行:`{ title, author, publishDate, content, excerpt, readingTime, wordCount, url, extractedAt }`。**content 是已经清理过的纯文本(paragraphs.join('\n\n'))**,不是 Markdown。**PRD/ARCH §3.5 的 QuizGenerator 输入是 `ExtractedContentV2 { title, content, url, engine }`**(ARCH line 255)。如果想直接喂给 LLM 出题,content 已经是纯文本格式,够用 | `content-extractor.ts:21-31` 对比 `ARCH §3.5` |

---

### 1.6 deep-reader · minimax.ts

**PM 文档声明**(BRAINSTORM 1.4 / PRD 1.2):
- "都依赖 MiniMax M2.1"
- "bridge 借鉴 mini-agent 接口"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| API 协议 | **用 Anthropic 协议**:第 12 行 `apiHost: 'https://api.minimaxi.com/anthropic'`,第 92 行 `fetch(... /v1/messages)` 走 `Authorization: Bearer`,body 是 `{ model, max_tokens, messages: [{role, content}] }`。**这是 Anthropic Messages API 协议,不是 OpenAI chat.completions** | `minimax.ts:12, 91-107` |
| 与 bridge 的协议冲突 | PRD §3.5 写 "M2.1 client",ARCH §3.1 m2xModel 默认 "MiniMax-M2.1" 也对。但 **bridge 端 ADR-004 说"独立实现简化版 LLM client" + "借鉴 LLMClientBase 接口设计"**,**没说用哪种协议**。如果 bridge 走 OpenAI 协议(/v1/chat/completions),Deep Reader 走 Anthropic 协议(/v1/messages),**两套 client 代码需要并存**。**统一协议是更好的选择**,但 PM 文档没决断 | `minimax.ts:12, 92` 对比 `Mini-Agent/.../openai_client.py:28, 76` |
| 模型名称 | `'MiniMax-M2.1'`(minimax.ts:99);Mini-Agent 默认 `'MiniMax-M2.1'`(openai_client.py:29)。一致 | `minimax.ts:99` 对比 `openai_client.py:29` |
| 配置来源 | 优先 chrome.storage `deep-reader-settings`,fallback 到 `import.meta.env.VITE_MINIMAX_API_KEY`。bridge 端用 `MiniMaxApiKey` CLI arg 或 env。**两边配置入口不一致,需要统一约定** | `minimax.ts:71-83` 对比 `ARCH §3.1 SyncRequest.minimaxApiKey` |

---

### 1.7 deep-reader · ReaderPanel.ts

**PM 文档声明**(PRD F-05):
- "ReaderPanel 加 '📝 开始测验' 按钮"
- "位置:ReaderPanel.ts"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| 文件路径 | **PRD F-05 / ARCH §2 写的 `deep-reader/src/content/ReaderPanel.ts` 不存在**,实际是 `src/content/components/ReaderPanel.ts`(在 components 子目录)。这是文档小错误,不影响实施但要修正 | 实际 `src/content/components/ReaderPanel.ts` |
| 当前 header 按钮 | 第 64-78 行:`dr-toggle-ai`(AI 助手)、`dr-settings`(设置)、`dr-close`(关闭)。**没有"开始测验"按钮**,需要新增。建议放在 `dr-toggle-ai` 旁边 | `ReaderPanel.ts:64-78` |
| AI 助手 panel | 第 99-108 行已经有 "AI 助手" sidebar section,内容是聊天框,**不是测验**。"开始测验"应该作为独立 section 或新 tab,不应当塞进聊天区 | `ReaderPanel.ts:99-108` |
| LLM 调用方式 | 通过 `chrome.runtime.sendMessage({ action: 'generateGuides' })`(第 198 行) → background/service-worker.ts 第 26 行处理 → 调 minimaxClient。**QuizGenerator 应走同一条路**,而不是在 content script 里直接 fetch,避免 API key 暴露和 CORS 复杂度 | `ReaderPanel.ts:198-201`, `service-worker.ts:26-41` |
| scroll 位置恢复 | PRD US-1.5 "做完测验回到阅读面板不丢失阅读位置"。当前 ReaderPanel 第 178 行 `document.body.style.overflow = 'hidden'`,quiz panel 弹出时应当不破坏 body 滚动状态;QuizPanel 关闭后需 scrollIntoView 或保留当前 .dr-paragraph 焦点 | `ReaderPanel.ts:178` |

---

### 1.8 Mini-Agent · openai_client.py

**PM 文档声明**(ADR-004):
- "不直接 import Mini-Agent,只借鉴接口"
- "bridge 只需一次 chat.completions 调用,引入全栈依赖拖入 100+MB"

**核实结果**:

| 声明 | 实际情况 | file:line |
|---|---|---|
| import 的副作用 | `from openai import AsyncOpenAI`(line 8) + `from ..retry import async_retry`(line 9) + `from ..schema import ...`(line 10) + `from .base import LLMClientBase`(line 11)。**这个文件本身只依赖 openai SDK + 内部 schema/retry**,不拖入 CLI runtime。但 `mini_agent` 包整体 import 会触发 `__init__.py` 加载 llm_wrapper / agent / tools 等**整套** | `openai_client.py:7-11` |
| CLI runtime 拖累 | cli.py 第 25-35 行 import 了 `prompt_toolkit` / `mini_agent.agent.Agent` / `mini_agent.config.Config` / `mini_agent.tools.*` / `mini_agent.utils` / `mcp_loader`。**bridge 直接 `from mini_agent.llm.openai_client import OpenAIClient` 会触发 mini_agent/__init__.py → agent → tools → mcp_loader → 加载 prompt_toolkit 等 CLI 依赖**。**ADR-004 决策是对的**,理由成立 | `cli.py:25-35` |
| 接口借鉴 | `LLMClientBase` + `Message/LLMResponse/TokenUsage` schema + `RetryConfig` 可借鉴接口设计;但 **schema 用 dataclass 风格 + Pydantic 不兼容**,bridge 端 Pydantic v2 自己定义即可,不要为了对齐 mini-agent 的 schema 而放弃 Pydantic 校验 | `openai_client.py:7-11`, `schema.py`(Mini-Agent 内部) |
| AsyncOpenAI 可借鉴 | bridge 端可以直接 `pip install openai` + `from openai import AsyncOpenAI`,**不依赖 mini_agent**。这是个干净的方案。**重点是协议选 /anthropic vs /v1**(见 1.6) | `openai_client.py:8, 43-46` |

---

### 1.9 Obsidian Vault · frontmatter 规范

**核实结果**(抽样 3 个文件):

| 文件 | frontmatter 字段 | file:line |
|---|---|---|
| `02 Wiki 维基/写作/阮一峰风格7条铁律.md` | `name`, `description`, `type: feedback`, `originSessionId`(UUID) | 行 1-6 |
| `02 Wiki 维基/视觉/design-style-guide.md` | **无 frontmatter**(只有 1 个 H1)。**不是 vault 所有文件都有 frontmatter,有些是纯 markdown** | 行 1-2 |
| `03 Projects/Tianshu Integrations/index.md` | `type: project`, `status`, `created`, `parent`, `related`(wiki-link 列表), `tags`(数组) | 行 1-16 |

**关键发现**:
- vault **不是所有 .md 都有 frontmatter**,有 frontmatter 的文件也字段不统一(阮一峰那篇有 `name`/`description`,Tianshu 这篇有 `type`/`status`/`related`/`tags`)。
- ARCH §3.1 RawCard 的 `tags: list[str] = []` 对齐 vault 习惯。
- ARCH §4.2 的 frontmatter 模板 `date/tags/source` **缺** `type` / `status` / `related`。如果 Inbox 文件夹未来需要被检索,会缺这些。
- **`Inbox/` 文件夹 PRD/ARCH 都假设它存在**,实际 vault 根目录没有 Inbox(只有 01 Raw / 02 Wiki / 03 Projects / 03 学习 / 05 Daily Notes / 99 System / logs)。**bridge 启动时必须 mkdir Inbox**。

---

## 2. 我对实现路径的独立判断

### 2.1 "bridge 放独立项目" 决策 — 我同意

ADR-001 的判断对。理由 PM 已写得很清楚,我补充 3 点:

1. **focus-quiz 和 Deep Reader 当前都没用 Python**,引入 Python 依赖到 recall-sticker(JS Chrome MV3)是污染;独立项目避免了这个冲突。
2. **bridge 可以独立测试**,FastAPI TestClient + pytest,不必拉起 Chrome 扩展做 E2E 也能跑单元测试。
3. **未来 focus-quiz 也可以接同一个 bridge**(recall-sticker 不是唯一客户),独立项目便于横向扩展。

**唯一修正点**:`~/Developer/tianshu-integrations/` 下已经有 `bridge/` 和 `curator/` 和 `obsidian/` 空目录(我 `ls` 看了,空)。是骨架预留,符合 PM 文档。

### 2.2 "Week 1 跳过 M2.1 先做 bridge + 写 .md" — 我**部分不同意**

**同意的部分**:
- Week 1 跑通"Recall Sticker → bridge → 写 .md"端到端确实能验证 chrome MV3 host_permissions、bridge HTTP、写文件这条主干,后续 M2.1 接入不会改架构。
- M2.1 prompt 调优确实是 Week 2 的核心工作,Week 1 没必要先做。

**不同意的部分 / 风险**:
1. **跳过 M2.1 意味着跳过 prompt 设计 + JSON parser fallback + token 预算这三件事**。这恰恰是整个联动 2 的"质量核心"。如果 Week 2 才碰到 M2.1 返回格式不稳,会**同时**卡 prompt / parser / 性能,debug 难度高。**建议 Week 1 D5 之前用一组 mock LLM 数据(可以是 LLM 调用但 mock response)先把 curator 主流程跑通**,把 M2.1 prompt 风险提前到 Week 1 D3-D4。
2. **跳过 M2.1 跑通的端到端,只能验证 plumbing(网络 + 文件 IO)**。但 PRD 成功指标里"打 tag 准确率 ≥ 80%"这种质量指标,在 Week 1 测不了,等到 Week 2 才第一次跑,可能发现 M2.1 对 prefix/suffix 这种短文本的 tag 质量根本不行,**只有 1 周时间调,风险高**。
3. **同步失败时的 per-card 容错**(ADR-002)在 Week 1 跳过 M2.1 时根本测不到。Week 1 写的是"成功路径" .md,失败路径全在 Week 2 测,但那时还要测 M2.1 失败 = 测试矩阵爆炸。

**我的建议**:Week 1 在 M2 之前加一个小任务 T-05b "LLM client mock + curator 空骨架 + JSON parser skeleton",把风险前移。这只多 4-6 小时。

### 2.3 "vault 路径 CLI 启动时锁" 决策 — 我**部分不同意**

ADR-003 说"用户极可能同时维护多个 vault,Phase 1 只服务一个",所以 CLI 启动锁死一个 vault。

**同意**:Phase 1 简化是对的。

**不同意 / 用户场景考虑**:
1. **用户是产品经理不是开发者**(PRD §2.1 明确),跑 `tianshu-bridge --vault ~/Desktop/知识库/知识库/` 是高摩擦动作。**用户极可能忘带 --vault 参数启动 → bridge 启动失败 → 不知道为啥**(ARCH §7 R3 已有,但 R3 没说"忘带参数"是触发场景之一)。
2. **CLI 启动锁死的另一个问题**:用户改 vault 路径(比如把 Inbox 整理到别的 vault)后,bridge 还在写旧路径。**CLI 启动后无法校验 vault 是否变更**。
3. **更糟的边界场景**:Recall Sticker 端的 `obsidianVaultPath` chrome.storage 配置,跟 bridge 启动的 `--vault` **没有同步机制**。两边各管各的,配置漂移是必然的。

**我的建议**:
- Phase 1 保留 CLI 锁,**但**加 3 个补充:① 默认 `--vault` 值为 `~/Desktop/知识库/知识库/`(用户当前 vault);② bridge `/health` 返回当前锁定的 vault 路径,Recall Sticker 启动时 fetch /health 比对 chrome.storage 的 obsidianVaultPath,**不一致就警告用户**;③ bridge 端加 `POST /config/reload` 重新读 vault,不用重启。

---

## 3. 风险与盲点(PM 文档漏掉的)

### 3.1 Recall Sticker **manifest.json 没有 host_permissions** — **P0 必改**

**证据**:`Recall-Sticker/manifest.json:4-11` 只列了 `activeTab/storage/sidePanel/tabs`。**没有 `host_permissions`**。

**影响**:F-14 bridge-client.js 调 `fetch('http://127.0.0.1:7733/...')` 会被 MV3 静默拦截,不会报错但永远拿不到响应。

**PRD/ARCH 没提这件事**。这是 Week 1 第一个会撞上的墙。

**建议加进 F-14 / T-08**:T-08a "Recall Sticker manifest.json 加 host_permissions: ['http://127.0.0.1:7733/*']"。

### 3.2 LLM 协议分叉(Deep Reader Anthropic vs bridge OpenAI) — **P0**

**证据**:`minimax.ts:12, 92` 走 `/anthropic/v1/messages`(Anthropic 协议);`openai_client.py:28, 76` 走 `/v1/chat/completions`(OpenAI 协议)。

**影响**:bridge 端如果按 ADR-004 自己实现 LLM client,会假设是 OpenAI 协议(/v1/chat/completions);但 Deep Reader 当前是 Anthropic 协议(/v1/messages)。**如果 QuizGenerator 调用 Deep Reader 的 minimaxClient 出题,出题协议是 Anthropic;bridge 用 OpenAI 协议整理卡片 — 两套代码并存**,维护负担翻倍。

**PRD 没决断**:"只支持 MiniMax M2.1" ≠ "只支持一种协议"。

**建议**:**统一走 OpenAI 协议(/v1/chat/completions)**,因为:
- Mini-Agent 已实现 OpenAIClient(openai_client.py),可借鉴
- OpenAI 协议 ecosystem 更广
- bridge 场景不需要 Anthropic-specific features(tool_use, vision)

改 Deep Reader minimax.ts 即可,从 ~50 行代码改动。

### 3.3 chrome.storage 10MB 上限 + MistakeStore 设计缺失 — **P1**

**证据**:Deep Reader 当前 chrome.storage 用了 `highlights` / `notes` / `deep-reader-settings`(`ReaderPanel.ts:29`)。新加 `mistake_log_v1`(PRD §5 F-04)叠加上去。如果用户答错 1000 道题,每条 ~500 字节,**500KB**,远没到 10MB。**但 PRD 说 "MistakeStore LRU ≤50/source"**(`ROADMAP §5 R4`),50 × N 个 sourceUrl,用户读 100 篇文章答错就是 5000 条,**2.5MB**,开始逼近上限。

**PRD 没给 LRU 实现细节**。F-22 "MistakeStore(chrome.storage.local 持久化 + LRU)"只有 3 小时估时,但 LRU 实现涉及 ① 读所有 records ② 按 sourceUrl 分组 ③ 按 timestamp 排序 ④ 裁剪到 50/source ⑤ 写回 — **实际至少 6-8 小时**,3 小时估时严重偏低。

### 3.4 Recall Sticker context 字段可能为空 / 与 text 重复 — **P1**

**证据**:content.js 第 42 行 `saveSticker(text, prefix, suffix, context = "")`,context 默认空串。如果贴纸创建时 DOM 异常(`getExportContext` 第 498 行 `if (clozeIndex === -1) return fullText.trim()` 返回全文),或者用户选区正好是一整个段落,**context 可能跟 prefix+suffix 拼起来差不多**,curator 拿去做 M2.1 整理时冗余。

**建议**:bridge 端 ObsidianWriter 必须先 `if not context: build context from prefix + text + suffix`,再写 .md,不能直接信 `context`。

### 3.5 MiniMax M2.1 在 prompt 含 Anki Cloze `{{c1::...}}` 时的行为未知 — **P1**

**证据**:context 字段可能含 `{{c1::some text}}`(content.js:493)。**M2.1 看到 `{{c1::...}}` 会不会误解成自己的语法?**Anki Cloze 跟 M2.1 不直接冲突,但 M2.1 prompt 里如果有 `{}` 模板占位符(context 误注入),**prompt injection 风险**。

**建议**:curator 在送 M2.1 前先把 context 里的 `{{c1::xxx}}` 替换成 `[xxx]` 或 `[回忆点]`,写 .md 时再换回。

### 3.6 chrome.downloads 在某些企业电脑被禁 — **P2 但 PM 已标**

**证据**:BRAINSTORM §2.4 提到"chrome.downloads API 在某些公司电脑被禁:离线 fallback 失效 — 低风险"。**低风险判定合理**,但 Recall Sticker 当前 manifest 没有 `downloads` 权限(content.js:536 `createExportLink` 用 `<a download>` 不是 chrome.downloads API),新增 F-15 才需要 manifest 加 `downloads` 权限。

**建议**:T-08b "manifest 加 `downloads` 权限"。

### 3.7 Readability 对 Vue/React SPA 渲染延迟 — **P1**

**证据**:content-extractor.ts 第 9 行 `document.cloneNode(true)`,Deep Reader content-script run_at 是 `document_idle`(manifest.json:21)。**SPA 路由切换时**document_idle 已经触发,但 article 内容是 JS 渲染后才出现 — Readability 抓不到正文。

**focus-quiz 同样问题**(page-extractor.js:9 也立即抽),**PM 文档没讨论 SPA 场景**。

**建议**:Week 1 加一个 mock test fixture,SPA 站点(如 https://reactjs.org/)验证 Readability 失败时三级 fallback 能不能救。**E-1.2 边界条件没覆盖 SPA**。

### 3.8 bridge CLI 启动时校验 vault 的"可写性"测试本身不可靠 — **P2**

**证据**:ARCH ADR-003 "bridge 启动时校验路径可写"。**校验"路径可写"就是 `os.access(vault, os.W_OK) | os.access(vault+'/Inbox', os.W_OK) | try makedirs` 之类**。但:
- macOS 上 admin 用户对 `~/Desktop/...` 默认可写,但**Time Machine 在备份时可能临时锁定文件**;
- 用户挂载的 SMB/NFS 网络 vault(常见)可能在断网时变成只读;
- Obsidian 自己持锁 .lock 文件时,新建文件可能短暂失败。

**建议**:T-05 不只校验"可写",还要测**实际写一个 .md.tmp + rename 成 .md** 测一次真写。

### 3.9 Recall Sticker 跨页面同步的 key 错乱 — **P1**

**证据**:content.js:30-32 `url.origin + url.pathname` 当 storage key,但 sourceUrl 存的是 `window.location.href`(完整 URL)。**意味着**用户从 `https://example.com/article?utm=x` 到 `https://example.com/article?utm=y` 是同一个 storage key,但 sidepanel 列表里 sourceUrl 不同 — 用户感觉"同一个 bucket 两条 source"会困惑。

**更糟的**:`#hash` 不在 key 里,意味着 `#section1` 和 `#section2` 同一桶,贴纸恢复时 `findRangeByContext` 用 prefix+suffix 找,但 SPA 切 hash 时 anchor 元素变了 — 恢复可能贴错位置。

**建议**:F-16 storage-collector 拉数据时,主动把 `sticker.url`(=完整 URL,含 query+hash)同步写入 bridge 请求,**不要只传 sticker.sourceUrl**。curator 端按完整 URL 去重。

### 3.10 bridge 进程崩溃时 Recall Sticker 的 chrome.downloads fallback 触发逻辑 — **P2 但 PRD 没写清**

**证据**:ARCH §4.3 "fetch 抛 TypeError (网络断) / 收到 503 → catch → chrome.downloads"。**但**:
- bridge 进程没起 → fetch 抛 `TypeError: Failed to fetch`,触发 fallback,**OK**。
- bridge 启动中(race condition) → fetch 抛 `ECONNREFUSED`,触发 fallback,**OK**。
- bridge 启动但 vault 路径校验失败 → bridge 早就 exit(1),**Recall Sticker 端 fetch 抛 ECONNREFUSED**,触发 fallback — **但用户的 vault 路径问题没被告知**!fallback 下载的 .md 用户得手动放进 Obsidian,但他自己都不知道 vault 路径错了。

**建议**:bridge 启动失败(端口冲突、vault 路径错、MiniMax key 缺)时,记录到 `~/.tianshu-bridge/error.log`,Recall Sticker 端 fallback 时把"上次错误原因"作为 toast 提示。

---

## 4. 实现顺序建议

### 4.1 我的 30 个 T 任务排序

**保留 PM 的 4 周时间线**。113 小时 ≈ 14 工作日,假设用户每天投入 4 小时,需要 3.5 周,加上收尾 ≈ 4 周,合理。

但**优先级和依赖顺序调整**:

| Week | 调整 |
|---|---|
| Week 1 | **保留 D1-D3 跑 bridge 骨架 + /health**(T-01 ~ T-03)。**新增 T-04b**(2h)"Recall Sticker manifest 加 host_permissions + downloads 权限" — 必须先做,否则 T-07/T-08 fetch 跑不通。**Week 1 D4 新增 T-05b**(4h)"curator 空骨架 + JSON parser skeleton + mock LLM client" — **风险前移**,见 §2.2。D5 M2 验收 = bridge 直写 .md + Recall Sticker → bridge 真打通 + mock curator 跑通 dry-run |
| Week 2 | **核心改 T-09 顺序**:把 T-09 "MiniMax OpenAI client" 提前到 Week 2 D1,跟 T-10 Curator 并行,**别等 M3 才开始 LLM client**。**新增 T-13b**(3h)"Deep Reader minimax.ts 协议统一(Anthropic → OpenAI)" + "Deep Reader manifest 检查 host_permissions(已有) + 移除 minimax 配置入口(改走 bridge)" — **风险前移**(见 §3.2) |
| Week 3 | 保留联动 1 任务。**T-17 估时从 4h 提到 6h** — 实际要写 content-extractor-v2.ts,**不是简单 port**,加上自己实现 Turndown / fallback candidates 排序逻辑(见 §1.5)。**T-19 估时从 6h 提到 8h** — 要做 prompt + 调用 + normalizeP1Question + 边界情况(空 content / Readability 全失败 / M2.1 返回非 JSON) |
| Week 4 | **新增 T-31**(4h)"Recall Sticker SPA 场景 E2E" — 在 reactjs.org / vuejs.org 之类站点贴纸 + 出题 + 同步,验证 §3.7 风险。**T-30 飞书 + Obsidian 同步保持** |

### 4.2 几个我建议**提前做**的事

1. **Week 1 D1**:`pytest tests/test_health.py`(空测试,确认 pytest 能跑) — 验证开发环境,别等 Week 2 才发现在用 Python 3.9 而不是 ≥3.10(ARCH §7.2 要求)
2. **Week 1 D2**:Recall Sticker manifest 改 + 跑一次现有的 content.js 验证不退化 — **改 manifest 是有风险的**(重载扩展用户会烦),提前做,留时间排查
3. **Week 2 D1**:写一组 MiniMax M2.1 prompt 测试集(10 个 sample input → expected output JSON) — M2.1 prompt 调优**必须**有评测集(ADR-006 已经说 Phase 2 才做,但实际上 Week 2 D3 就开始 curate 了,没评测集等于盲调)

### 4.3 我会砍掉的事(简化)

- **F-08 题型选择 UI(P1)**:延后到 Phase 2。Week 3 已经够挤,4 种题型(trap/counterfactual/transfer/open)在 QuizPanel 全部默认勾上,Phase 2 再加选择 UI
- **F-22 错题本可视化复习日历(backlog)**:这是另一整个项目,别塞进 Phase 1

---

## 5. Spec 里应该明确但 PM 文档里没说清的事

### 5.1 LLM 协议必须明确选一种

**问题**:Deep Reader 当前走 Anthropic(/anthropic/v1/messages),bridge 默认按 ADR-004 "OpenAI 协议"(/v1/chat/completions)。

**需要决策**:bridge + Deep Reader 都走 OpenAI(/v1/chat/completions),还是都走 Anthropic?

**我的推荐**:**OpenAI**,理由见 §3.2。

### 5.2 MiniMax API key 配置入口统一

**问题**:Deep Reader 用 `chrome.storage.deep-reader-settings`(minimax.ts:73-83);bridge 用 CLI arg 或 env。**两个入口不一致**,用户配置两次。

**需要决策**:API key 放哪?
- A. 只放 bridge env,Deep Reader 不直接调 MiniMax(走 bridge) — 架构最干净,但 Deep Reader 当前已有 AI 助手功能必须改
- B. Deep Reader 自己的 key 在 chrome.storage,bridge 用独立 key — 两个 key,用户配置两次
- C. bridge 暴露 `GET /config/minimax-key` 给 Deep Reader,Deep Reader 不直连 MiniMax — 干净但引入新依赖

**我的推荐**:**B**(短期)+ Phase 2 收敛到 A。Deep Reader 当前 AI 助手功能不动,bridge 独立 key。

### 5.3 chrome.storage key 命名空间规则

**问题**:Recall Sticker sidepanel.js 第 46-48 行 `isStickerCollection(url, value) = storageKey !== 'tags' && Array.isArray(value)`。**只要 chrome.storage 里出现 array-typed key 都会被当贴纸集合**。tianshu-integrations 加新 key 时必须避免 `Array.isArray(value) === true`。

**需要决策**:tianshu-integrations 加什么 chrome.storage key?ARCH §5 列了:
- Deep Reader: `mistake_log_v1`(array,OK)
- Recall Sticker: `obsidianVaultPath`(string,OK)、`lastSyncTime`(number,OK)

**但** `tags` 也是 string-array 类型(Recall Sticker 自己的标签管理),sidepanel.js 第 47 行只 skip 了 `tags`,**没有 skip `obsidianVaultPath` / `lastSyncTime`** — 等 bridge-client 写这两个 key 时,sidepanel.js 不会误判(因为不是 array),**OK**。但如果以后想加 `cardIdsQueue: number[]`,就会被误读。

**我的建议**:tianshu-integrations 所有 chrome.storage key 写注释 `// NOT an array` 或用对象包装 `{version: 1, value: [...]}`。sidepanel.js 端等 T-08b 时一并改成"白名单 isStickerCollection"。

### 5.4 跨页面贴纸的 sourceUrl 标准化

**问题**:Recall Sticker content.js:55 `sourceUrl: window.location.href` 是完整 URL;但 storage key 用 `url.origin + url.pathname`(content.js:31)。**两者不一致**。

**需要决策**:Phase 1 不改现有 Recall Sticker schema,但 bridge sync 时 sourceUrl 字段填什么?
- A. 用 `sticker.sourceUrl`(完整 URL)
- B. 用 `sticker.url`(即 storage key,无 query/hash)
- C. 重新组合成统一格式

**我的推荐**:**A**(完整 URL),保留 query/hash 信息便于后续 trace 回原文,但需要 curator 在写 .md 时清理掉 utm_* / ref 等追踪参数。

### 5.5 bridge 进程崩溃后的 stale .md 文件处理

**问题**:T-05/M2 写 .md 时如果 bridge 进程崩溃(信号杀、OOM、系统休眠),文件可能写一半(0 字节)或写完未 sync。**下次启动 bridge 时如何发现 stale .md**?

**需要决策**:
- A. bridge 启动时扫 Inbox,找 `.tmp` 文件并清理
- B. 写 .md 用 atomic write(temp + rename),崩了不污染
- C. 不管,用户自己清理

**我的推荐**:**B**(atomic write),约 5 行 Python 代码,避免很多后续问题。

### 5.6 Recall Sticker 的 tags 在 chrome.storage 里是 string-array,但结构复杂

**证据**:sidepanel.js 第 142 行 `tags` 是 tag 对象数组 `{ id, name, color }`,不是 string-array。Recall Sticker 卡片存的是 `sticker.tags: string[]`(tag id 列表)。**跟 PRD RawCard.tags 描述("list[str]" "贴纸的 tag")对得上**,但实际 Recall Sticker tags 是 tag id 引用,不是 tag 名称。

**影响**:curator 拿到 sticker.tags 时是 id 列表,要 join sidepanel 加载的 tag 列表才能拿到 name。M2.1 出 tag 建议时输入也得是 name 列表。

**需要决策**:bridge 端是否需要 sidepanel 的 tag 列表?简单做法是 F-16 storage-collector.js 同步读 tags key + sticker 列表,curator 端 join。

### 5.7 bridge 监听端口(7733)是否会跟用户其他服务冲突

**问题**:ARCH §2 / §3.2 写 `127.0.0.1:7733`,但用户可能有别的开发服务(Mini-Agent 是不是也用端口?需要确认)。

**需要决策**:端口选什么?常见冲突端口:3000(React dev)、5000(Flask)、8000(Django)、8080(通用 HTTP)、5432(Postgres)。

**我的建议**:**7733** 不冲突保留,但 bridge 启动失败时优雅提示"端口被占,请用 --port 指定"。

### 5.8 M2.1 prompt 模板必须 Week 1 末出 v0

**问题**:BRAINSTORM 2.4 提到"M2.1 整理质量不稳 — 高风险"。但 Week 1 没规划 prompt 工作,Week 2 才做(T-10/T-11)。

**需要决策**:Week 1 D5 之前出 v0 prompt(含 stub),用 mock LLM 跑通 curator JSON 输出。

**我的建议**:Week 1 D4 加 T-05b(已在 §4.1 推荐)。

### 5.9 MiniMax M2.1 真实 API 行为需要在 Phase 2 Week 1 摸一次

**问题**:minimax.ts 和 openai_client.py 的代码**只展示协议**,没展示 MiniMax M2.1 实际响应。**M2.1 是否真有 reasoning_details?是否真有 tool_calling?response_format 是否支持?**这些只有真打一次 API 才知道。

**需要决策**:Phase 2 D1 必须做一次"裸 API 测试",写一个 test_api_basics.py,实际打 MiniMax:
1. 普通 chat
2. response_format=json_object
3. response_format=json_schema
4. tool_use(可选)
5. 长 context(8k+)

**失败模式提前暴露**。

### 5.10 没有规划"用户卸载 bridge / 卸载 Recall Sticker"的清理路径

**问题**:
- 卸载 bridge → Recall Sticker chrome.storage `obsidianVaultPath` / `lastSyncTime` 残留,但无害
- 卸载 Recall Sticker → 旧数据在 chrome.storage 残留,新装 tianshu-introductions(如果有)会被误读
- 用户换电脑 / vault 路径改了 → chrome.storage 里的 vault path 是死的

**需要决策**:tianshu-integrations 提供 `tianshu-bridge cleanup` 命令?还是不管?

**我的建议**:Phase 1 不管(Out of Scope),但 ARCH §3 / §5 应该明确写"卸载后果:chrome.storage 残留键需要用户手动 chrome://settings/clear 浏览数据"。

---

## 6. 总结(给 owner 的 3 条建议)

1. **不要相信 PM 文档的字面 port**。focus-quiz page-extractor.js 用了 `window.Readability`,Deep Reader 用 npm 包 — **不能直接 port**,只能 port fallback 思路。类似地,Recall Sticker manifest 必须先改才能 fetch。

2. **风险前移比"按部就班"更重要**。Week 1 跳过 M2.1 看似省事,但把 prompt 不稳 / 协议冲突 / chrome MV3 host_permissions 这 3 个 P0 风险全推到 Week 2-3,**debug 矩阵爆炸**。建议 Week 1 D4 加 4-6h mock LLM + manifest 改动 + 协议测试。

3. **manifest.json / 端口 / vault 路径 这种"配置层"的事故是 P0**。但 PM 文档全部把它们当 P3 风险。用户是 PM,跑命令是高摩擦,**任何需要他手动处理的边界情况都是 P0**。这条原则应该在 BDD 阶段就列入 acceptance criteria。

---

## 7. 引用与双链

源文件证据(file:line):
- `/Users/mahaoxuan/Documents/trae_projects/focus-quiz/focus-quiz-optimized/lib/page-extractor.js:9-99`
- `/Users/mahaoxuan/Documents/trae_projects/focus-quiz/focus-quiz-optimized/sidepanel-logic.js:182-250`
- `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/manifest.json:4-11`
- `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/content.js:30-58, 480-523, 734-768`
- `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/sidepanel.js:46-48, 162-179`
- `/Users/mahaoxuan/Documents/trae_projects/api/deep-reader/src/lib/content-extractor.ts:3, 9-36`
- `/Users/mahaoxuan/Documents/trae_projects/api/deep-reader/src/lib/minimax.ts:12, 71-107`
- `/Users/mahaoxuan/Documents/trae_projects/api/deep-reader/src/content/components/ReaderPanel.ts:64-78, 198-201`
- `/Users/mahaoxuan/Documents/trae_projects/api/deep-reader/src/background/service-worker.ts:26-41`
- `/Users/mahaoxuan/Documents/trae_projects/api/deep-reader/manifest.json:25-33`
- `/Users/mahaoxuan/Documents/trae_projects/api/Mini-Agent/mini_agent/llm/openai_client.py:7-11, 28-46`
- `/Users/mahaoxuan/Documents/trae_projects/api/Mini-Agent/mini_agent/cli.py:25-35`

PM 文档:
- `~/Developer/tianshu-integrations/PROJECT_CHARTER.md`
- `~/Developer/tianshu-integrations/docs/BRAINSTORM.md`
- `~/Developer/tianshu-integrations/docs/PRD.md`
- `~/Developer/tianshu-integrations/docs/ARCHITECTURE.md`
- `~/Developer/tianshu-integrations/docs/ROADMAP.md`

Vault 样本:
- `/Users/mahaoxuan/Desktop/知识库/知识库/02 Wiki 维基/写作/阮一峰风格7条铁律.md`
- `/Users/mahaoxuan/Desktop/知识库/知识库/02 Wiki 维基/视觉/design-style-guide.md`
- `/Users/mahaoxuan/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md`