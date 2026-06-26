# ARCHITECTURE · 技术架构

> **代号**:Tianshu Integrations
> **版本**:v0.1(2026-06-27)

---

## 1. 整体架构

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          浏览器 (Chrome MV3)                              │
│                                                                            │
│  ┌──────────────┐      ┌──────────────┐       ┌──────────────────────┐  │
│  │ Deep Reader  │      │ focus-quiz   │       │   recall-sticker     │  │
│  │  (TS, MV3)   │      │ (JS, MV3)    │       │    (JS, MV3)         │  │
│  │              │      │              │       │                      │  │
│  │ ReaderPanel  │      │ sidepanel.js │       │ sidepanel.html       │  │
│  │ + QuizPanel  │      │ 错题本 (旧)  │       │ + "同步到 Obsidian"   │  │
│  │ mistake_log_ │      │ mistakeLog   │       │ + vaultPath 配置     │  │
│  │   v1 (新)    │      │  (不改)      │       │ bridge-client.js     │  │
│  └──────┬───────┘      └──────────────┘       └──────────┬───────────┘  │
│         │                                                 │              │
└─────────┼─────────────────────────────────────────────────┼──────────────┘
          │ fetch (127.0.0.1)                               │ fetch
          │ (Phase 2 / 直接打 MiniMax)                      │ (核心)
          ▼                                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                ~/Developer/tianshu-integrations/                          │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  bridge/server.py  (FastAPI + uvicorn, 127.0.0.1:7733)              │  │
│  │                                                                     │  │
│  │  POST /sync/recall-sticker                                          │  │
│  │  POST /trigger/curate                                               │  │
│  │  GET  /health                                                       │  │
│  └────────────────┬────────────────────────────────────────────────────┘  │
│                   │                                                       │
│                   ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  curator/curate.py                                                  │  │
│  │                                                                     │  │
│  │  两阶段整理:                                                        │  │
│  │    Phase A: 批量打 tag + 合并语义重复 (1 次 M2.1 call)              │  │
│  │    Phase B: 单卡补双向链接 (per-card M2.1 call)                     │  │
│  └────────────────┬────────────────────────────────────────────────────┘  │
│                   │                                                       │
│                   ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  obsidian/writer.py                                                 │  │
│  │                                                                     │  │
│  │  生成 .md:                                                          │  │
│  │    ---                                                              │  │
│  │    date: 2026-06-27                                                 │  │
│  │    tags: [recall-sticker, k8s, networking]                          │  │
│  │    source: recall-sticker-sidepanel                                 │  │
│  │    ---                                                              │  │
│  │    # Recall Sticker · 2026-06-27                                    │  │
│  │    ## {{card-title}}                                                │  │
│  │    来源: {{sourceUrl}}                                              │  │
│  │    > {{prefix}} {{c1::text}} {{suffix}}                            │  │
│  │    相关: [[card-1]] [[card-2]]                                      │  │
│  └────────────────┬────────────────────────────────────────────────────┘  │
│                   │                                                       │
└───────────────────┼───────────────────────────────────────────────────────┘
                    │ 文件写入
                    ▼
       ┌────────────────────────────┐
       │  ~/Desktop/知识库/知识库/  │
       │     Inbox/                 │
       │       2026-06-27-recall.md │
       └────────────────────────────┘

                                  ▲
                                  │ HTTPS
                                  │
                       ┌──────────┴──────────┐
                       │   MiniMax M2.1 API  │
                       │  api.minimaxi.com   │
                       └─────────────────────┘
```

## 2. 模块布局

```
tianshu-integrations/
├── PROJECT_CHARTER.md                       # 立项档案
├── README.md                                # 安装与启动(Phase 3 写)
├── pyproject.toml                           # Python 包定义
├── bridge/
│   ├── __init__.py
│   ├── server.py                            # FastAPI app + 3 endpoints
│   ├── cli.py                               # `tianshu-bridge` console script
│   ├── schemas.py                           # Pydantic request/response
│   └── errors.py                            # 错误码 + 异常类
├── curator/
│   ├── __init__.py
│   ├── curate.py                            # 主入口:两阶段整理
│   ├── prompts.py                           # M2.1 prompt 模板
│   ├── parsers.py                           # JSON 多层 fallback 解析
│   └── batch.py                             # 批量处理(per-card 容错)
├── obsidian/
│   ├── __init__.py
│   ├── writer.py                            # 写 .md 到 vault
│   ├── frontmatter.py                       # YAML frontmatter 生成
│   └── naming.py                            # 文件命名 + 路径安全
├── llm/
│   ├── __init__.py
│   ├── client.py                            # MiniMax OpenAI 协议
│   └── retry.py                             # 简单 retry(借用 mini-agent 思想)
├── tests/
│   ├── test_server.py                       # FastAPI endpoint 单元
│   ├── test_curator.py                      # M2.1 整理逻辑(mock LLM)
│   ├── test_writer.py                       # Obsidian 写入
│   ├── fixtures/
│   │   ├── sample-cards.json                # 测试用贴纸
│   │   ├── sample-llm-response.json         # mock M2.1 返回
│   │   └── sample-vault/                    # 临时 vault 目录
│   └── conftest.py
└── docs/
    ├── BRAINSTORM.md
    ├── PRD.md
    ├── ARCHITECTURE.md (本文档)
    └── ROADMAP.md
```

## 3. 关键接口契约

### 3.1 Bridge HTTP API

```python
# bridge/schemas.py

class RawCard(BaseModel):
    id: str                              # recall-sticker 时间戳或 UUID
    text: str                            # 贴纸文本
    prefix: str = ""                     # 上下文前缀(各 80 字符)
    suffix: str = ""                     # 上下文后缀
    context: str                         # 含 {{c1::text}} Anki Cloze 的完整句
    sourceUrl: str
    tags: list[str] = []
    timestamp: int                       # ms


class SyncRequest(BaseModel):
    trigger: Literal["manual", "auto_on_save"]
    cards: list[RawCard]
    obsidianVaultPath: str               # 必填,bridge 启动时校验过
    m2xModel: str | None = "MiniMax-M2.1"
    minimaxApiKey: str | None = None     # 留空从 env 读


class CuratedCard(BaseModel):
    cardId: str
    title: str                           # M2.1 提取的简短标题
    body: str                            # Markdown body
    tags: list[str]
    wikiLinks: list[str]                 # ["[[card-name]]"]
    mergedWith: str | None = None        # 合并建议目标 ID


class SkippedCard(BaseModel):
    cardId: str
    reason: str


class CardError(BaseModel):
    cardId: str
    message: str


class SyncResponse(BaseModel):
    success: bool
    curated: list[CuratedCard]
    skipped: list[SkippedCard]
    errors: list[CardError]
    durationMs: int
    obsidianFilesWritten: list[str]      # vault-relative 路径
```

### 3.2 Bridge Endpoints

| Method | Path | 用途 | 请求 | 响应 |
|---|---|---|---|---|
| `POST` | `/sync/recall-sticker` | 同步一批贴纸 | `SyncRequest` | `SyncResponse` |
| `POST` | `/trigger/curate` | 二次整理已同步卡片 | `{"cardIds": [...]}` | `SyncResponse` |
| `GET` | `/health` | 健康检查 | — | `{"status":"ok","version":"0.1.0","vaultWritable":bool,"minimaxConfigured":bool,"uptimeSec":int}` |

### 3.3 错误码约定

| HTTP | 触发条件 | Recall Sticker 端行为 |
|---|---|---|
| 200 | 成功 | 显示"已同步 N 张卡片 → /path" |
| 400 | vaultPath 不存在或不可写 | 显示具体错误 + 提示检查 vault 路径 |
| 502 | MiniMax API 失败 | 显示 M2.1 错误 + 重试按钮 |
| 503 | bridge 进程没起 / 网络断 | **自动降级**到 chrome.downloads 下载 .md |
| 504 | M2.1 timeout(>30s) | 同 502 |

### 3.4 Recall Sticker bridge-client 接口

```js
// recall-sticker/Recall-Sticker/lib/bridge-client.js

/**
 * @typedef {Object} SyncOptions
 * @property {string} vaultPath - Obsidian vault 绝对路径
 * @property {string} [apiKey] - MiniMax key,留空从 env 读
 * @property {number} [timeout=30000] - 毫秒
 */

/**
 * @param {RawCard[]} cards
 * @param {SyncOptions} options
 * @returns {Promise<SyncResult>}
 */
async function syncToBridge(cards, options): Promise<SyncResult>;

/**
 * @returns {Promise<{ok: boolean, version?: string, error?: string}>}
 */
async function checkBridgeHealth(): Promise<HealthResult>;
```

### 3.5 Deep Reader QuizPanel 接口

```ts
// deep-reader/src/lib/quiz-generator.ts

export type QuestionType = 'trap' | 'counterfactual' | 'transfer' | 'open';

export interface Question {
  type: QuestionType;
  question: string;
  options?: string[];                  // multiple_choice 时必填
  correct: number | string;            // multiple_choice 是 index,open 是 string
  explanation: string;
  evidenceQuote: string;
  evidenceLocator?: string;            // paragraph index 等
  sourceHint?: string;                 // 给用户的提示
}

export interface MistakeRecord {
  question: Question;
  userChoice: number | string;
  isCorrect: boolean;
  latencyMs: number;
  sourceUrl: string;
  sourceTitle: string;
  sourceUrlHash: string;               // sha256(sourceUrl).slice(0, 16)
  timestamp: number;
}

export class QuizGenerator {
  async generate(
    content: ExtractedContentV2,
    options: { count?: number; focus?: QuestionType[] }
  ): Promise<Question[]>;
}

export class MistakeStore {
  async save(record: MistakeRecord): Promise<void>;
  async list(sourceUrlHash?: string): Promise<MistakeRecord[]>;
  async clear(sourceUrlHash?: string): Promise<void>;
}
```

## 4. 数据流详解

### 4.1 联动 1 · 出题

```
[用户打开文章页 → 点扩展图标]
   ↓
deep-reader/content-script.ts
   ├─ 1. ContentExtractorV2.extract()
   │    ├─ 优先 Mozilla Readability + Turndown (port 自 focus-quiz)
   │    └─ fallback: DOM innerText 抽取 (port 自 focus-quiz)
   ├─ 2. 返回 ExtractedContentV2 { title, content, url, engine }
   └─ 3. 渲染 ReaderPanel
       ↓
[用户点 "📝 开始测验" 按钮]
   ├─ QuizGenerator.generate(content, { count: 3, focus: ['trap','counterfactual'] })
   │    ├─ buildPrompt(content, focus)        // 照搬 focus-quiz 的 prompt 范式
   │    ├─ MiniMaxClient.callAPI(prompt)       // POST {apiHost}/v1/messages
   │    └─ parseJSON(response) → normalizeP1Question(rawQuestion, idx)
   └─ 返回 Question[]
       ↓
[QuizPanel 渲染]
   ├─ 显示题目 + 选项 (Shadow DOM 隔离)
   ├─ 用户点选项 → 记录 userChoice / correctIdx / latencyMs
   └─ 答错 → MistakeStore.save({...})
       ↓
[用户点 "完成" 或关闭 QuizPanel]
   ├─ 显示统计(对 X / 错 Y / 跳过 Z)
   ├─ 提供"导出 Anki"按钮 → MistakeStore.list() → formatMistakesAsAnkiCsv() → chrome.downloads
   └─ 关闭 QuizPanel → 阅读面板恢复到刚才 scroll 位置
```

### 4.2 联动 2 · 同步到 Obsidian

```
[用户在网页选中 → 创建贴纸]
   ↓
recall-sticker/content.js
   └─ StorageService.saveSticker(text, prefix, suffix, fullContext)
       // fullContext = getExportContext() = 整句含 {{c1::text}}
       ↓
[用户打开 Side Panel]
   └─ collectAllStickers() → flat list of {text, prefix, suffix, context, sourceUrl, tags, timestamp}
       ↓
[用户点 "🧠 同步到 Obsidian" 按钮]
   bridge-client.js:
   ├─ 检查 vaultPath 配置(从 chrome.storage.local 读)
   ├─ fetch('http://127.0.0.1:7733/sync/recall-sticker', {
   │      method: 'POST',
   │      body: JSON.stringify({ trigger: 'manual', cards, obsidianVaultPath, m2xModel })
   │      signal: AbortSignal.timeout(30000)
   │  })
   └─ 处理响应 / 错误
       ↓
bridge/server.py (/sync/recall-sticker endpoint):
   ├─ Pydantic 校验 SyncRequest
   ├─ 校验 obsidianVaultPath 存在且可写(可能二次校验)
   └─ Curator.curate(cards) 异步执行
       ↓
bridge/curator.py:
   ├─ Phase A: 批量打 tag + 合并语义重复
   │    ├─ 拼 prompt: 给所有卡 {prefix, suffix, text, context, sourceUrl}
   │    ├─ 让 M2.1: ① 打 1-3 个 tag ② 标记哪些卡语义重复 ③ 改写为 Markdown
   │    └─ 1 次 M2.1 call,得到 {tagged[], merged[]}
   ├─ Phase B: 单卡补双向链接(可选,Phase 1 简化为单 prompt 拼所有建议)
   │    └─ per-card 容错,失败不阻塞
   └─ 返回 CuratedCard[] + SkippedCard[] + CardError[]
       ↓
bridge/obsidian/writer.py:
   ├─ 为每张 CuratedCard 生成 Markdown body
   ├─ 生成 YAML frontmatter (date, tags, source)
   ├─ 写文件: vaultPath/Inbox/YYYY-MM-DD-recall.md (追加到当日文件)
   └─ 返回 obsidianFilesWritten[]
       ↓
server.py 返回 SyncResponse
   ↓
recall-sticker/sidepanel.js:
   ├─ 显示"已同步 N 张卡片 → /Inbox/2026-06-27-recall.md"
   ├─ 记录 lastSyncTime 到 chrome.storage.local
   └─ 错误时显示具体错误信息
       ↓
[Obsidian 打开 vault → Inbox 文件夹 → 用户 review]
```

### 4.3 离线 Fallback 分支

```
bridge-client.js syncToBridge()
   ├─ fetch 抛 TypeError (网络断) / 收到 503
   └─ catch:
       ├─ obsidian-exporter.cardsToMarkdown(cards)  // 与 bridge 端格式一致
       ├─ chrome.downloads.download({
       │      url: 'data:text/markdown;base64,' + btoa(md),
       │      filename: 'recall-stickers-2026-06-27.md',
       │      saveAs: true
       │  })
       └─ Side Panel 显示"bridge 不可达,已下载 .md,请手动拖入 Obsidian"
```

## 5. chrome.storage 命名空间隔离

| Extension | Key | 用途 | schema 版本 |
|---|---|---|---|
| focus-quiz | `mistakeLog` (camelCase,旧) | focus-quiz 自己的错题 | (不动) |
| Deep Reader | `mistake_log_v1` (snake_case,新) | 联动 1 错题 | v1 |
| recall-sticker | `<url-key>` (动态,chrome.storage 默认) | recall-sticker 贴纸 | (不动) |
| recall-sticker | `obsidianVaultPath` | 联动 2 vault 配置 | v1 |
| recall-sticker | `lastSyncTime` | 联动 2 同步状态 | v1 |

**故意保持差异**:Deep Reader 用 `mistake_log_v1`(snake_case + 版本号),focus-quiz 用 `mistakeLog`(camelCase);**不互相覆盖**,允许未来聚合(Phase 2)。

## 6. 关键设计决策 (ADR)

### ADR-001 · bridge 部署为独立项目

**Context**:bridge 服务需要一个 Python 进程跑 MiniMax API 调用,放哪里?

**Options**:
- A. 独立项目 `~/Developer/tianshu-integrations/`(已选)
- B. 塞进 Mini-Agent 主仓(`Mini-Agent/bridge/`)
- C. 塞进 recall-sticker 主仓

**Decision**:**A**

**Rationale**:
- bridge 职责单一(本机 HTTP 服务 + M2.1 整理),独立 git 仓便于版本管理
- 不污染 Mini-Agent 主仓(其核心是 CLI agent runtime)
- 不引入 Python 依赖到纯 JS 项目 recall-sticker
- 未来 focus-quiz / Deep Reader 也能复用同一个 bridge

**Consequences**:
- 多一个 git 仓,但可接受
- 用户需手动启服务,README 必须清楚说明

### ADR-002 · M2.1 失败 per-card 容错

**Context**:curator 调 M2.1 失败时怎么处理?

**Options**:
- A. 整批失败回滚
- B. per-card 容错,失败的不整理直接写原始 Markdown

**Decision**:**B**

**Rationale**:
- 用户已同步 50 张卡,1 张失败整批回滚体验差
- per-card 容错保证"成功部分一定落地",失败部分可后续手动整理

**Consequences**:
- 响应 schema 增加 `errors[]` 字段,Side Panel 需要分别显示成功/失败
- M2.1 单卡 prompt 比批量 prompt 更费 token,但更稳

### ADR-003 · vault 路径 CLI 启动时锁,不允许运行期切换

**Context**:vault 路径怎么配置?每次请求传?持久化?CLI 启动时锁?

**Options**:
- A. CLI 启动 `--vault`(已选)
- B. 持久化到配置文件
- C. 每次请求传

**Decision**:**A**

**Rationale**:
- 用户极可能同时维护多个 vault,Phase 1 只服务一个
- CLI 启动时校验路径可写,比每次请求校验更安全
- 不持久化避免配置漂移

**Consequences**:
- Phase 2 加 `POST /config` 动态切换(可选)
- Recall Sticker 端 vault path 配置不传给 bridge,只用作 UI 提示

### ADR-004 · 不直接 import Mini-Agent,只借鉴接口

**Context**:bridge 需不需要把 Mini-Agent 作为 Python library 直接 import?

**Options**:
- A. 独立实现简化版 LLM client(已选)
- B. 直接 import `mini_agent.llm`

**Decision**:**A**

**Rationale**:
- mini_agent 是 CLI runtime,带 agent loop / tool calling / retry / prompt_toolkit
- bridge 只需要一次 `chat.completions` 调用,引入全栈依赖拖入 100+ MB
- 借鉴 `LLMClientBase` 接口设计即可

**Consequences**:
- 需自己写简化版 MiniMax OpenAI client(~200 行)
- 不复用 Mini-Agent 的 retry / tool calling(bridge 场景不需要)

### ADR-005 · focus-quiz 的 providers.js 不 port

**Context**:focus-quiz 已有 18 个 LLM provider 抽象,要不要 port?

**Options**:
- A. 整个 port 到 Deep Reader
- B. 只支持 MiniMax M2.1(已选)

**Decision**:**B**

**Rationale**:
- focus-quiz 的 providers.js 460+ 行,18 个 provider + 4 种 API 协议
- Deep Reader 当前 MiniMaxClient 已经够用
- bridge 场景只调一个 provider,简洁为上

**Consequences**:
- Deep Reader / bridge 都不支持 OpenAI / Anthropic / Ollama 等其他 provider
- Phase 2 评估是否需要扩展

### ADR-006 · Obsidian 双向链接 Phase 1 不做 vault index

**Context**:curator 建议双向链接时,需不需要读 vault 已有卡片列表?

**Options**:
- A. 让 M2.1 自己建议(不知道 vault 里有什么)(已选)
- B. 启动时扫 vault 索引,喂给 M2.1
- C. 用 embedding 做相似度匹配

**Decision**:**A**(Phase 1),B/C 留给 Phase 2

**Rationale**:
- Phase 1 不引入新基建,vault index 是另一个项目
- M2.1 建议可能不准确,但用户可手动调整

**Consequences**:
- 双向链接准确率有限(估计 < 60%)
- Phase 2 加 vault index 后可提升到 80%+

## 7. 安全考虑

- **bridge 监听 127.0.0.1**(不暴露公网)
- **vault 路径校验**:bridge 启动时必须可写,否则退出 1
- **M2.1 API key**:支持 CLI arg / 环境变量 / 用户 secret 文件,不入 git
- **chrome.storage 数据**无加密(Chrome 自身管理),信任本地用户
- **不发起跨域请求**:bridge 只调 `api.minimaxi.com`,Recall Sticker 只调 `127.0.0.1:7733`

## 8. 性能预算

| 指标 | 目标 |
|---|---|
| 联动 1 出题 P95 延迟 | < 8s |
| 联动 2 单卡整理 P95 延迟 | < 3s |
| 联动 2 批量同步(20 卡) P95 | < 30s |
| bridge 启动时间 | < 2s |
| bridge 内存占用 | < 200 MB |

## 9. 引用

- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[Brainstorm|~/Developer/tianshu-integrations/docs/BRAINSTORM.md]]
- [[PRD|~/Developer/tianshu-integrations/docs/PRD.md]]
- [[Roadmap|~/Developer/tianshu-integrations/docs/ROADMAP.md]]