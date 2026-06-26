# Spec · Tianshu Integrations 实现规格

> **task_id**: `roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini`
> **date**: 2026-06-27
> **作者**: host (yishuship design Phase 3)
> **基于**: Phase 0+1 PM 文档(Charter / Brainstorm / PRD / Architecture / Roadmap)

---

## 0. 文档定位

本文档是 yishuship Phase 3 的 host spec。它把 PRD/Architecture 翻译成**可实现的具体规格**,回答"具体怎么写代码"。Plan 阶段会把它转成可执行任务。

**上下游**:
- 上游 PRD/Architecture:定义"做什么"、"为什么"
- 本 spec:定义"用什么 API、哪些字段、什么数据流"
- 下游 plan.md:定义"按什么顺序、哪个文件、写多少行"

---

## 1. 范围

### 1.1 In Scope

| 联动 | 范围 |
|---|---|
| **联动 1** | Deep Reader 阅读面板内"📝 开始测验"按钮 → 出题 → 答题 → 错题本 → Anki 导出 |
| **联动 2** | Recall Sticker Side Panel"🧠 同步到 Obsidian"按钮 → bridge → M2.1 整理 → 写 .md |
| **bridge 服务** | FastAPI @ 127.0.0.1:7733,3 个 endpoint |
| **Obsidian 写入** | 锁定 `~/Desktop/知识库/知识库/Inbox/YYYY-MM-DD-recall.md` |

### 1.2 Out of Scope

- 多 vault / LaunchAgent 开机自启 / 跨设备同步(Phase 2 backlog)
- focus-quiz providers 18 provider 抽象(只支持 MiniMax)
- 联机多人测验 / iOS / Android
- 替换 Anki(只导出兼容)

---

## 2. 依赖与复用点核实

### 2.1 直接 port(零成本)

| 资产 | 源文件 | 用途 | 验证 |
|---|---|---|---|
| `focus-quiz-optimized/lib/page-extractor.js` | 99 行 IIFE | Deep Reader ContentExtractorV2 | ✅ 已读,IIFE → ESM 仅需去包装 |
| `recall-sticker` 卡片 schema | `Recall-Sticker/content.js:42-60` `saveSticker()` | bridge 接收格式 | ✅ `{text, prefix, suffix, context, timestamp, sourceUrl}` |
| focus-quiz Anki Cloze 格式 | `sidepanel-logic.js:228-250` `formatMistakesAsAnkiCsv` | Deep Reader 错题导出 | ⚠️ 需要再读 |
| focus-quiz 错题 schema | `sidepanel.js:155` `saveMistake` | Deep Reader MistakeRecord | ⚠️ 需要再读 |

### 2.2 借鉴接口(不直接 import)

| 资产 | 源文件 | 借鉴什么 |
|---|---|---|
| `Mini-Agent/llm/openai_client.py` | `OpenAIClient._make_api_request` | bridge 端 MiniMax client 的 request shape |
| `Mini-Agent/llm/base.py` | `LLMClientBase` | bridge 端 client 的接口设计 |
| `deep-reader/src/lib/minimax.ts` | `getActiveConfig()` 模式 | bridge 端"每次请求从 storage 读"模式(可省略,birdge 启动时校验) |

### 2.3 不复用

| 项 | 原因 |
|---|---|
| `focus-quiz/providers.js` 460+ 行 | 太重,bridge 只支持 MiniMax 单一 provider |
| `Mini-Agent/cli.py` 的 prompt_toolkit UI | bridge 是 HTTP 服务,不是 CLI |
| `deep-reader/ReaderPanel.ts` 的拖拽 / 主题切换 | 跟联动无关 |

---

## 3. 数据结构(精确)

### 3.1 RawCard (Recall Sticker → bridge)

**源**(recall-sticker/content.js:49-56):
```js
{
  text, prefix, suffix, context,
  timestamp: Date.now(),
  sourceUrl: window.location.href,
}
```

**bridge 端 Pydantic 接收**:
```python
class RawCard(BaseModel):
    text: str                              # 贴纸文本
    prefix: str = ""                       # 上下文前缀(各 80 字符)
    suffix: str = ""                       # 上下文后缀
    context: str = ""                      # 含 {{c1::text}} Anki Cloze 完整句
    sourceUrl: str                         # 完整 URL
    tags: list[str] = []                   # 扩展字段(目前 recall-sticker 没打 tag,留空)
    timestamp: int                         # ms
    id: str | None = None                  # 可选,recall-sticker 用 timestamp 字符串化当 id
```

**注**:`tags` 字段 recall-sticker 当前没用,但留接口,方便 Phase 2。

### 3.2 CuratedCard (bridge → Obsidian)

```python
class CuratedCard(BaseModel):
    cardId: str                            # 用 timestamp 字符串
    title: str                             # M2.1 提取的简短标题
    body: str                              # Markdown body
    tags: list[str]                        # M2.1 自动打的 tag
    wikiLinks: list[str]                   # ["[[card-name]]"]
    mergedWith: str | None = None          # 合并建议目标 ID
```

### 3.3 Question / MistakeRecord (Deep Reader)

**Question 借鉴 focus-quiz schema**:
```ts
type QuestionType = 'trap' | 'counterfactual' | 'transfer' | 'open';

interface Question {
  type: QuestionType;
  question: string;
  options?: string[];                    // multiple_choice 时必填,open 时省略
  correct: number | string;              // multiple_choice 是 index,open 是 string
  explanation: string;
  evidenceQuote: string;                // 原文证据片段
  evidenceLocator?: string;             // 段落 index
  sourceHint?: string;                  // 用户提示
}
```

**MistakeRecord**:
```ts
interface MistakeRecord {
  question: Question;
  userChoice: number | string;
  isCorrect: boolean;
  latencyMs: number;
  sourceUrl: string;
  sourceTitle: string;
  sourceUrlHash: string;                // sha256(sourceUrl).slice(0, 16)
  timestamp: number;
}
```

### 3.4 chrome.storage 命名空间

| Extension | Key | 用途 |
|---|---|---|
| focus-quiz | `mistakeLog` (camelCase,旧) | 不动 |
| Deep Reader | `mistake_log_v1` (snake_case,新) | 联动 1 错题本 |
| recall-sticker | `<url-origin-pathname>` | 不动,贴纸数据 |
| recall-sticker | `obsidianVaultPath` | 联动 2 vault 路径配置 |
| recall-sticker | `lastSyncTime` | 联动 2 同步状态 |

---

## 4. 接口契约(精确签名)

### 4.1 bridge HTTP API

**POST /sync/recall-sticker**
```python
# Request
{
    "trigger": "manual" | "auto_on_save",
    "cards": [RawCard, ...],
    "obsidianVaultPath": str,            # 必填
    "m2xModel": str = "MiniMax-M3",      # 默认 M3(用户用 Token Plan)
    "minimaxApiKey": str | None          # 留空从 env 读 MINIMAX_API_KEY
}

# Response 200
{
    "success": true,
    "curated": [CuratedCard, ...],
    "skipped": [{"cardId": str, "reason": str}, ...],
    "errors": [{"cardId": str, "message": str}, ...],
    "durationMs": int,
    "obsidianFilesWritten": [str, ...]   # vault-relative 路径
}

# Response 4xx/5xx
{"success": false, "error": str, "code": str}
```

**GET /health**
```python
{
    "status": "ok",
    "version": "0.1.0",
    "vaultWritable": bool,
    "minimaxConfigured": bool,
    "uptimeSec": int
}
```

**POST /trigger/curate** — 同 /sync/recall-sticker 格式,只 curate 不写 .md(预留,Phase 1 不实现)

### 4.2 Recall Sticker bridge-client

```js
// recall-sticker/Recall-Sticker/lib/bridge-client.js

/**
 * @param {Array<{text, prefix, suffix, context, sourceUrl, timestamp, tags?}>} cards
 * @param {{vaultPath: string, apiKey?: string, timeout?: number}} options
 * @returns {Promise<SyncResult>}
 * @typedef {Object} SyncResult
 * @property {boolean} success
 * @property {string=} error
 * @property {string} mode   'online' | 'offline_fallback'
 * @property {string=} offlinePath   // chrome.downloads 触发后的下载路径
 */
async function syncToBridge(cards, options) { ... }

async function checkBridgeHealth() { ... }   // 返回 HealthResult
```

### 4.3 Deep Reader 工具导出

```ts
// deep-reader/src/lib/quiz-types.ts
export type QuestionType = 'trap' | 'counterfactual' | 'transfer' | 'open';
export interface Question { ... }
export interface MistakeRecord { ... }

// deep-reader/src/lib/quiz-generator.ts
export class QuizGenerator {
  constructor(private minimaxClient: MiniMaxClient) {}
  async generate(
    content: ExtractedContentV2,
    options: { count?: number; focus?: QuestionType[] } = {}
  ): Promise<Question[]>;
}

// deep-reader/src/lib/mistake-store.ts
export class MistakeStore {
  async save(record: MistakeRecord): Promise<void>;
  async list(sourceUrlHash?: string): Promise<MistakeRecord[]>;
  async clear(sourceUrlHash?: string): Promise<void>;
}
```

### 4.4 Deep Reader ContentExtractorV2

```ts
// deep-reader/src/lib/content-extractor-v2.ts
export interface ExtractedContentV2 {
  title: string;
  content: string;        // Markdown
  url: string;
  truncated: boolean;
  engine: 'readability-turndown' | 'readability-innertext' | 'dom-innertext';
}

export class ContentExtractorV2 {
  static extract(): ExtractedContentV2;
}
```

实现策略:port focus-quiz 的 page-extractor.js 99 行,**直接 inline** 到 v2 里(避免 import UMD),用 `document.cloneNode(true)` + `new Readability(doc).parse()` + `new TurndownService().turndown()` 三级降级。

---

## 5. 数据流(详细)

### 5.1 联动 1 出题

```
[用户按 Alt+D]
  → content-script.ts
  → ContentExtractorV2.extract()
      ├─ 1. document.cloneNode(true)
      ├─ 2. new Readability(clone).parse() → article
      ├─ 3. new TurndownService().turndown(article.content)
      ├─ 4. fallback: tempDiv.innerText
      └─ 返回 ExtractedContentV2
  → ReaderPanel 渲染
  → [用户点 "📝 开始测验"]
  → QuizGenerator.generate(content, { count: 3, focus: ['trap', 'counterfactual'] })
      ├─ buildPrompt(content, focus)         // 借鉴 focus-quiz prompt 范式
      ├─ minimaxClient.callAPI(prompt)        // POST {apiHost}/v1/messages
      └─ parseQuestions(response)              // JSON → Question[]
  → QuizPanel 渲染 Shadow DOM
  → [用户点选项]
  → onAnswer(question, userChoice, latencyMs)
      ├─ if 错: MistakeStore.save({...})
      └─ 显示 explanation + evidenceQuote
  → [测验完成]
  → 显示统计 + 错题 list + "导出 Anki" 按钮
```

### 5.2 联动 2 同步

```
[用户在网页选中 → recall-sticker 创建贴纸]
  → StorageService.saveSticker(text, prefix, suffix, context)
  → chrome.storage.local[<url-key>].push({text, prefix, suffix, context, timestamp, sourceUrl})

[用户打开 Side Panel → 点 "🧠 同步到 Obsidian"]
  → collectAllStickers()                // 拉所有非 'tags' key 的数组,展平
  → if vaultPath 未配置:显示"请配置 vault 路径"
  → syncToBridge(cards, {vaultPath})
      ├─ try fetch('http://127.0.0.1:7733/sync/recall-sticker', {method:'POST', body, signal: AbortSignal.timeout(30000)})
      └─ catch (TypeError | 503):
          → cardsToMarkdown(cards)        // 跟 bridge 端格式一致的纯函数
          → chrome.downloads.download({url: 'data:text/markdown;base64,...', filename, saveAs: true})
          → 返回 {success: true, mode: 'offline_fallback', offlinePath}

[bridge /sync/recall-sticker]
  → Pydantic 校验 SyncRequest
  → 校验 obsidianVaultPath 存在 + 可写(二次校验)
  → Curator.curate(cards)
      ├─ Phase A: 批量打 tag + 合并(1 次 M2.1 call)
      │   ├─ 拼 prompt: 给所有卡的 {prefix, suffix, text, context, sourceUrl}
      │   ├─ 让 M2.1: ① 打 1-3 个 tag ② 标合并 ③ 改写为 Markdown
      │   └─ JSON 多层 fallback parse
      ├─ Phase B: per-card 补双向链接(Phase 1 简化为合并到 Phase A 输出)
      └─ 返回 CuratedCard[] + SkippedCard[] + CardError[]
  → ObsidianWriter.writeBatch(curated, vaultPath)
      ├─ 生成 YAML frontmatter (date, tags, source)
      ├─ 生成 Markdown body
      └─ 写 vaultPath/Inbox/YYYY-MM-DD-recall.md (追加到当日文件)
  → 返回 SyncResponse
```

---

## 6. 关键算法

### 6.1 JSON 多层 fallback parse (curator/parsers.py)

```python
def parse_curation_response(raw: str) -> dict:
    """curator 调 M2.1 返回可能不稳,逐层降级。"""
    # 1. 严格 JSON parse
    try: return json.loads(raw)
    except json.JSONDecodeError: pass

    # 2. 提取第一个 {...} 块
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except json.JSONDecodeError: pass

    # 3. 提取 ```json ... ``` 块
    m = re.search(r'```json\s*(.+?)\s*```', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass

    # 4. 单字段降级:把 raw 当作 tags 建议
    return {"tags": _extract_tags_naive(raw), "merged": [], "rewrites": []}
```

### 6.2 QuizGenerator prompt builder

```python
# 借鉴 focus-quiz 的 prompt 范式
def build_quiz_prompt(content: str, focus: list[str], count: int = 3) -> str:
    focus_str = ", ".join(focus) if focus else "trap, counterfactual, transfer"
    return f"""你是一位深度阅读教练。基于以下文章,出 {count} 道测验题。

题型(可选 {focus_str}):
- trap(陷阱题):基于文章细节的反向理解,容易选错
- counterfactual(反事实题):如果 X 改变,会怎样
- transfer(迁移题):X 在 Y 领域怎么应用
- open(开放题):无固定答案,要求引用原文

文章:
{content[:6000]}

返回 JSON 数组,每道题:
{{
  "type": "trap|counterfactual|transfer|open",
  "question": "题面",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],  // open 题型省略
  "correct": 0,  // multiple_choice 是 index,open 是字符串
  "explanation": "为什么对/错",
  "evidenceQuote": "原文证据片段(≤50字)"
}}"""
```

### 6.3 Obsidian .md 生成

```python
# bridge/obsidian/writer.py
def render_card_section(card: CuratedCard) -> str:
    md = f"## {card.title}\n\n"
    md += f"> {card.body}\n\n"
    if card.wikiLinks:
        md += f"相关: {' '.join(card.wikiLinks)}\n\n"
    if card.tags:
        md += f"标签: {' '.join(f'#{t}' for t in card.tags)}\n\n"
    return md

def render_frontmatter(date: str, tags: list[str]) -> str:
    return f"""---
date: {date}
tags: [{', '.join(tags)}]
source: recall-sticker-sidepanel
---

"""

def write_batch(cards: list[CuratedCard], vault_path: str) -> list[str]:
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = Path(vault_path) / "Inbox" / f"{today}-recall.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 追加到当日文件(不覆盖)
    if file_path.exists():
        existing = file_path.read_text(encoding="utf-8")
    else:
        all_tags = sorted({t for c in cards for t in c.tags} | {"recall-sticker"})
        existing = render_frontmatter(today, all_tags) + f"# Recall Sticker · {today}\n\n"

    appended = existing + "\n---\n\n".join(render_card_section(c) for c in cards)
    file_path.write_text(appended, encoding="utf-8")
    return [str(file_path.relative_to(vault_path))]
```

---

## 7. 错误处理(明确)

| 错误 | HTTP | bridge 行为 | Recall Sticker / Deep Reader 行为 |
|---|---|---|---|
| bridge 没起 | 503 / TypeError | — | 自动降级 chrome.downloads |
| vault 路径不存在 | 400 | 启动时校验 + endpoint 二次校验 | Side Panel 显示"路径错误" |
| vault 路径不可写 | 400 | 启动时 `os.access(path, os.W_OK)` | Side Panel 显示"无写权限" |
| M2.1 API key 缺失 | 502 | 启动时检查 env | Side Panel 显示"bridge 未配置 API key" |
| M2.1 返回非 JSON | 200 + per-card 失败 | 走 fallback parser,errors 字段返回该卡 | Side Panel 显示 "X 张失败,可重试" |
| M2.1 timeout > 30s | 504 | 整批取消,errors 返回所有卡 | Side Panel 显示"AI 响应超时" |
| Readability 失败 | — | — | QuizPanel 显示"页面太复杂,无法出题" |
| chrome.storage 超 10MB | — | — | MistakeStore 限 50/source,LRU 淘汰 |

---

## 8. 性能预算

| 指标 | 目标 | 测量 |
|---|---|---|
| 联动 1 出题 P95 | < 8s | console.timeEnd |
| 联动 2 单卡整理 P95 | < 3s | bridge log |
| 联动 2 批量同步(20 卡) P95 | < 30s | bridge log |
| bridge 启动 | < 2s | 进程启动 → /health 返回 200 |
| bridge 内存 | < 200MB | ps aux |

---

## 9. 测试策略

### 9.1 单元测试(bridge 端 pytest)

| 文件 | 覆盖 |
|---|---|
| `tests/test_server.py` | /health、/sync/recall-sticker endpoint、错误码 |
| `tests/test_curator.py` | curate()、JSON fallback parser、tag 提取 |
| `tests/test_writer.py` | write_batch、frontmatter 生成、追加到当日文件 |
| `tests/test_llm_client.py` | mock MiniMax API、retry、timeout |

### 9.2 单元测试(Deep Reader 端 vitest)

| 文件 | 覆盖 |
|---|---|
| `src/lib/content-extractor-v2.test.ts` | 三级降级、Readability 失败 |
| `src/lib/quiz-generator.test.ts` | prompt 构建、JSON parse、normalizeQuestion |
| `src/lib/mistake-store.test.ts` | save/list/clear、LRU |
| `src/lib/anki-export.test.ts` | CSV 格式 |

### 9.3 单元测试(Recall Sticker 端)

无构建系统,无测试框架 → Phase 4 加简单的 `tests/` + 手动 smoke。

### 9.4 E2E

- 联动 1:打开文章 → 测 → 导出 Anki
- 联动 2:贴 5 张卡 → 同步 → Obsidian 打开文件 → 内容正确

---

## 10. 配置与部署

### 10.1 bridge CLI

```bash
# 安装(开发模式)
cd ~/Developer/tianshu-integrations
pip install -e .

# 启动
tianshu-bridge --port 7733 --vault ~/Desktop/知识库

# 必填环境变量
export MINIMAX_API_KEY="sk-cp-..."   # 用户提供
export MINIMAX_BASE_URL="https://api.minimaxi.com/anthropic"  # 默认
export MINIMAX_MODEL="MiniMax-M3"    # 默认,用户用 Token Plan
```

### 10.2 bridge 启动校验

```python
# bridge/cli.py
def main():
    args = parse_args()
    if not os.path.isdir(args.vault):
        print(f"ERROR: vault 路径不存在: {args.vault}"); sys.exit(1)
    if not os.access(args.vault, os.W_OK):
        print(f"ERROR: vault 路径无写权限: {args.vault}"); sys.exit(1)
    if not os.environ.get("MINIMAX_API_KEY"):
        print("WARN: MINIMAX_API_KEY 未设置,curator 将失败")
    uvicorn.run(app, host="127.0.0.1", port=args.port)
```

### 10.3 Deep Reader 构建

```bash
cd /Users/mahaoxuan/Documents/trae_projects/api/deep-reader
npm install
npm run build
# 加载 dist/ 到 Chrome
```

### 10.4 Recall Sticker 加载

Chrome → `chrome://extensions` → 加载 `Recall-Sticker/` 目录(无需 build)

---

## 11. 文件清单(具体到路径)

### 11.1 新建(bridge 服务)— 9 个文件

```
~/Developer/tianshu-integrations/
├── pyproject.toml
├── bridge/
│   ├── __init__.py
│   ├── server.py
│   ├── cli.py
│   ├── schemas.py
│   └── errors.py
├── curator/
│   ├── __init__.py
│   ├── curate.py
│   ├── prompts.py
│   └── parsers.py
├── obsidian/
│   ├── __init__.py
│   ├── writer.py
│   ├── frontmatter.py
│   └── naming.py
├── llm/
│   ├── __init__.py
│   ├── client.py
│   └── retry.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_server.py
    ├── test_curator.py
    ├── test_writer.py
    ├── fixtures/
    │   ├── sample-cards.json
    │   ├── sample-llm-response.json
    │   └── sample-vault/
    └── README.md
```

### 11.2 新建/修改(Deep Reader)— 4 新 + 2 改

**新建**:
```
api/deep-reader/src/
├── lib/
│   ├── content-extractor-v2.ts        # port page-extractor.js + 加类型
│   ├── content-extractor-v2.test.ts
│   ├── quiz-types.ts
│   ├── quiz-generator.ts
│   ├── quiz-generator.test.ts
│   ├── mistake-store.ts
│   ├── mistake-store.test.ts
│   └── anki-export.ts
└── content/
    ├── QuizPanel.ts
    └── QuizPanel.test.ts
```

**修改**:
- `api/deep-reader/src/content/ReaderPanel.ts` — 加"📝 开始测验"按钮
- `api/deep-reader/src/lib/minimax.ts` — 不改(minimax client 已够用)

### 11.3 新建(Recall Sticker)— 4 新 + 1 改

**新建**:
```
recall-sticker/Recall-Sticker/lib/
├── storage-collector.js       # 60 行
├── bridge-client.js           # 80 行
└── obsidian-exporter.js       # 100 行
```

**修改**:
- `recall-sticker/Recall-Sticker/manifest.json` — 加 `host_permissions: ["http://127.0.0.1:7733/*"]`
- `recall-sticker/Recall-Sticker/sidepanel.html` — 加按钮 + vault path input
- `recall-sticker/Recall-Sticker/sidepanel.js` — 绑按钮事件 + 状态显示

---

## 12. 风险与开放问题(转给 plan 阶段)

### 12.1 已识别风险(继续追踪)

- **R1**:bridge 进程崩溃 → Recall Sticker 自动降级 chrome.downloads ✅
- **R2**:M2.1 返回格式不稳 → JSON 多层 fallback ✅
- **R3**:Obsidian vault 路径写错 → 启动时 + endpoint 二次校验 ✅
- **R4**:chrome.storage 10MB 上限 → MistakeStore LRU ≤50/source ✅
- **R5**:focus-quiz 字段冲突 → `mistake_log_v1` 命名空间隔离 ✅
- **R6**:M2.1 联网不通 → 启动时 ping api.minimaxi.com(warn 不 fail)
- **R7**:Readability 失败 → 三级 fallback ✅
- **R8**:用户改 vault 结构 → curator 严格按现有 vault 规范生成

### 12.2 新增风险(host 调查发现)

- **R9**:recall-sticker manifest 没有 `host_permissions`,**必须改 manifest** 才能 fetch 127.0.0.1
- **R10**:M2.1 实际是 **M3 模型**(不是 PRD 里写的 M2.1),需要用 `MiniMax-M3` model name
- **R11**:Deep Reader minimax.ts 默认 model = `MiniMax-M2.1`,跟用户当前用的 Token Plan M3 不一致 — bridge 端用 M3,Deep Reader 端需要改 minimax.ts 默认 model
- **R12**:recall-sticker 没打 tag,`tags` 字段一直是空 — curator 打的 tag 会丢失上下文,Phase 1 接受这个折衷
- **R13**:page-extractor.js IIFE → ESM port 时,如果在 deep-reader Vite 编译里直接 import,需要确保 `@mozilla/readability` 和 `turndown` 在 package.json 已装(已确认:都装好了)

### 12.3 开放问题(等 plan 阶段决策)

- Q1:Week 1 的 MVP bridge 要不要加 retry?答:**不加**,先跑通再优化
- Q2:M2.1 prompt 是用 OpenAI 协议还是 Anthropic 协议?答:**OpenAI 协议**(因为用户 key 来自 Token Plan,Token Plan 走 `/anthropic` 端点,bridge 默认用这个)
- Q3:obsidian 写入时如果当日文件已存在且很大,是否清空重建?答:**追加到末尾**(避免数据丢失)
- Q4:QuizPanel 用什么 UI 库?答:**纯手写 Shadow DOM + CSS**(不引 React 到 content script)
- Q5:Recall Sticker 端测试怎么办?答:**手写 smoke test** + 用户验收

---

## 13. 与 PRD/Architecture 的偏差

| 项 | PRD/Architecture | 本 spec | 原因 |
|---|---|---|---|
| M2.1 model | `MiniMax-M2.1` | `MiniMax-M3` | 用户用 Token Plan,实际可用 M3 |
| bridge 默认 model | `MiniMax-M2.1` | `MiniMax-M3` | 同上 |
| Deep Reader minimax.ts | 不改 | 改默认 model 为 M3 | 一致性 |
| manifest host_permissions | 未提 | 必须加 `http://127.0.0.1:7733/*` | 实测 recall-sticker 当前没有 |
| 双向链接 Phase 1 | "per-card M2.1 call" | 合并到 Phase A 单 prompt | token 节省,Phase 2 优化 |

---

## 14. Acceptance Criteria / 验收标准(Hard Cut)

| 项 | 必须达到 |
|---|---|
| **联动 2 E2E** | 用户贴 5 张卡 → 点按钮 → Obsidian Inbox 看到 .md 含 frontmatter + tags + 内容 < 60s |
| **联动 1 E2E** | 用户读 3000 字文章 → 点开始测验 → 3 题 < 8s → 答错 → 错题本有记录 |
| **离线 fallback** | 手动 kill bridge → Recall Sticker 点按钮 → 拿到 .md 下载 |
| **Anki 导出** | 导出 .csv → 导入 Anki → 卡片显示 Cloze 正确 |
| **错误路径** | vault 路径错 / M2.1 timeout / Readability 失败 / chrome.storage 满 4 类覆盖 |
| **性能** | 出题 P95 < 8s,同步 20 卡 P95 < 30s,bridge 内存 < 200MB |
| **文档** | README + INSTALL + 5 份 PM 文档已更新到 Obsidian/飞书 |

---

## 15. 引用

- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[Brainstorm|~/Developer/tianshu-integrations/docs/BRAINSTORM.md]]
- [[PRD|~/Developer/tianshu-integrations/docs/PRD.md]]
- [[Architecture|~/Developer/tianshu-integrations/docs/ARCHITECTURE.md]]
- [[Roadmap|~/Developer/tianshu-integrations/docs/ROADMAP.md]]
- [[Obsidian 镜像页|~/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md]]