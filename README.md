# Tianshu Integrations · 联动 Recall Sticker / Deep Reader 与 Obsidian Vault

> **GitHub**: [yishu-ziyu/tianshu-integrations](https://github.com/yishu-ziyu/tianshu-integrations) (public)
> **本地开发**: `~/Developer/tianshu-integrations/` (单一开发源)
> **代号**: Tianshu Integrations(天枢联动)
> **父项目**: [Tianshu](~/Documents/trae_projects/api/) — Mini-Agent + Deep Reader
> **当前状态**: **Week 1 完成 · 联动 2 MVP 跑通 · 58 测试全过 · QA PASS**
> **日期**: 2026-06-27

---

## 📍 工作流(单源真相)

只有一个开发地方:`~/Developer/tianshu-integrations/`。改完代码 → `git commit` → `git push` 同步到 GitHub。

```bash
cd ~/Developer/tianshu-integrations

# 修改代码
git add -A
git commit -m "feat: ..."
git push  # 自动同步到 GitHub

# 跑测试
source .venv/bin/activate
pytest tests/ -v
```

> **不要**在其他地方再 clone 或新建仓库。所有的开发迭代都在这个目录。

---

## 项目定位

把天枢两个系统(Mini-Agent + Deep Reader)与既有本地工具 `focus-quiz`(网页认知压力测试)和 `recall-sticker`(网页贴纸抗遗忘)打通,形成:

**读完即测 · 贴纸即沉淀** 的本地化工作流,落盘到 Obsidian Vault。

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Chrome MV3 Extensions                              │
│                                                                     │
│  Deep Reader   ←──(Week 3)──→  QuizPanel(出题 + 错题本)         │
│  focus-quiz                       ↓                                │
│  recall-sticker  ──fetch──→  bridge @ 127.0.0.1:7733               │
│                                  ↓                                │
│                              M2.1 整理                             │
│                                  ↓                                │
│                          Obsidian Vault                            │
│                          ~/Desktop/知识库/知识库/Inbox/             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Week 1 完成 · 联动 2 MVP

联动 2(Recall Sticker → Obsidian)端到端可用:

- ✅ Recall Sticker Chrome 扩展可访问 bridge
- ✅ Bridge 接收卡片 + 调 M2.1(目前 mock,可切真模型)+ 写 .md 到 vault
- ✅ .md 含 YAML frontmatter + 每张卡的 ## section + 来源 URL
- ✅ 离线 fallback(bridge 挂时 chrome.downloads 下载 .md)
- ✅ Vault 路径安全校验
- ✅ 5 张卡同步 < 60s,20 卡同步 < 30s,500 卡 < 10ms 延迟
- ✅ 5 个并发同步无数据丢失(fcntl 文件锁)

联动 1(Deep Reader + focus-quiz 出题)在 **Week 3** 实现。

---

## 快速开始

### 0. 前置条件

- Python ≥ 3.10
- [uv](https://github.com/astral-sh/uv) 推荐(也可用 pip)
- Chrome 浏览器(用于 Recall Sticker 扩展)
- Obsidian(可选,用于浏览 Inbox/ 文件夹)

### 1. 安装 bridge

```bash
cd ~/Developer/tianshu-integrations
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 验证
tianshu-bridge --help
pytest tests/ -v
```

### 2. 配置环境变量

```bash
# 必须 - MiniMax API key(用户已提供: sk-cp-...)
export MINIMAX_API_KEY="sk-cp-gC-DLoYsHw4NqMP4zwyLi7Uk-Yyu_jWmlP3M6053rZl-w1qvE0FvS7Yyh844fabF9X5IXYj8JYwiGV6DNLibfHLCAloC_k1MSfYyqjxhWqwlyu8pQZzG6zQ"

# 可选 - 自定义 vault 路径(默认 ~/Desktop/知识库/知识库)
export OBSIDIAN_VAULT="$HOME/Documents/obsidian-vault"
```

### 3. 启动 bridge

```bash
tianshu-bridge --port 7733 --vault ~/Desktop/知识库

# 看到:
# Starting tianshu-bridge on 127.0.0.1:7733
#   Vault: /Users/mahaoxuan/Desktop/知识库/知识库
#   M2.1:  configured
# INFO: Uvicorn running on http://127.0.0.1:7733
```

### 4. 健康检查

```bash
curl http://127.0.0.1:7733/health | python3 -m json.tool

# {
#   "status": "ok",
#   "version": "0.1.0",
#   "vaultWritable": true,
#   "minimaxConfigured": true,
#   "currentVault": "/Users/.../知识库",
#   "uptimeSec": 5
# }
```

### 5. 应用 Recall Sticker patches

Recall Sticker 当前在 `~/Documents/trae_projects/recall-sticker/Recall-Sticker/`。bridge 需要的两处改动已打包为 patch:

```bash
# 注意:第一次运行会修改 Recall-Sticker 工作区文件
bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-patches.sh

# 看到:
# Applying Recall Sticker patches...
#   [ok]   manifest.json patched (host_permissions + downloads)
#   [ok]   sidepanel.js patched (STORAGE_KEY_BLACKLIST)
# Done! Reload Recall Sticker extension in chrome://extensions.
```

修改内容:
1. `manifest.json`: 加 `host_permissions: ["http://127.0.0.1:7733/*"]` + `permissions: ["downloads"]` (MV3 fetch 拦截)
2. `sidepanel.js`: 加 `STORAGE_KEY_BLACKLIST` 防止 chrome.storage 错把 Deep Reader 错题本当贴纸

### 6. Chrome 加载 Recall Sticker

`chrome://extensions` → 开启"开发者模式" → "加载已解压的扩展程序" → 选 `~/Documents/trae_projects/recall-sticker/Recall-Sticker/`

如果之前加载过,记得点 ↻ 重载。

### 7. 端到端测试

1. 打开任意网页 → 选中一段文本 → Recall Sticker 创建贴纸
2. 点扩展图标 → Side Panel → "🧠 同步到 Obsidian"(Week 2 才会有按钮,目前需要手动调 bridge API)
3. Obsidian → ~/Desktop/知识库/知识库/Inbox/ 应该出现 `2026-06-27-recall.md`

---

## API 参考

### `GET /health`

健康检查端点。

**Response 200:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "vaultWritable": true,
  "minimaxConfigured": true,
  "currentVault": "/Users/.../知识库",
  "uptimeSec": 42
}
```

### `POST /sync/recall-sticker`

同步一批 Recall Sticker 卡片到 Obsidian Vault。

**Request body:**
```json
{
  "trigger": "manual",
  "cards": [
    {
      "text": "eBPF",
      "prefix": "类似",
      "suffix": "机制",
      "context": "类似eBPF机制",
      "sourceUrl": "https://example.com/article",
      "tags": [],
      "timestamp": 1234567890
    }
  ],
  "obsidianVaultPath": "/Users/.../知识库"
}
```

**Response 200:**
```json
{
  "success": true,
  "curated": [
    {
      "cardId": "1234567890_eBPF",
      "title": "eBPF",
      "body": "kernel tech",
      "tags": ["linux"],
      "wikiLinks": [],
      "mergedWith": null,
      "sourceUrl": "https://example.com/article"
    }
  ],
  "skipped": [],
  "errors": [],
  "durationMs": 95,
  "obsidianFilesWritten": ["Inbox/2026-06-27-recall.md"]
}
```

**Error codes:**
| HTTP | 触发条件 |
|---|---|
| 200 | 成功 |
| 400 | vault 路径不存在 / 不可写 / 不匹配配置的 OBSIDIAN_VAULT |
| 422 | JSON 解析失败 / 必填字段缺失 |
| 500 | 内部错误(M2.1 完全失败 + 写入失败) |

---

## 开发

```bash
# 跑测试
pytest tests/ -v --tb=short

# 跑测试 + 覆盖率
pytest tests/ --cov=tianshu_integrations

# 起 bridge(开发模式)
TIANSHU_BRIDGE_SKIP_UVICORN=1 tianshu-bridge --port 7733 --vault ./test-vault

# 实际打 MiniMax API(需真实 key + 网络)
MINIMAX_API_KEY="sk-real-key" tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

---

## 项目结构

```
~/Developer/tianshu-integrations/
├── README.md                      # 本文件
├── PROJECT_CHARTER.md             # 立项档案
├── docs/
│   ├── BRAINSTORM.md               # 用户故事 + 边界
│   ├── PRD.md                     # 产品需求
│   ├── ARCHITECTURE.md            # 技术架构 + ADR
│   └── ROADMAP.md                 # 3-4 周路线图
├── tianshu_integrations/
│   ├── bridge/
│   │   ├── server.py              # FastAPI app + /health + /sync
│   │   ├── cli.py                 # tianshu-bridge console script
│   │   └── schemas.py             # Pydantic models
│   ├── curator/
│   │   ├── curate.py              # M2.1 调用 + per-card isolation
│   │   └── parsers.py             # JSON 多层 fallback
│   ├── llm/
│   │   └── client.py              # MiniMax OpenAI client + MockLLMClient
│   └── obsidian/
│       └── writer.py              # .md 写入 + atomic + fcntl lock
├── tests/                         # 58 个测试(43 单元 + 13 E2E + 2 回归)
├── patches/
│   ├── recall-sticker-manifest.patch
│   └── recall-sticker-sidepanel-blacklist.patch
├── scripts/
│   └── apply-recall-sticker-patches.sh
└── .ship/                         # yishuship 自动产物(spec/plan/QA/review 等)
```

---

## 下一步行动

| 优先级 | 任务 | 估计 |
|---|---|---|
| Week 2 D1 | Deep Reader minimax.ts 协议统一(Anthropic → OpenAI)+ 默认 model = `MiniMax-M3` | 3h |
| Week 2 D2-3 | curator 加真实 M2.1 prompt 调优 + 评测集 | 12h |
| Week 2 D4 | ObsidianWriter 增强(frontmatter 完整 + 双向链接) | 4h |
| Week 2 D5 | Recall Sticker Side Panel 加"🧠 同步"按钮 + vault path input | 4h |
| Week 3 | 联动 1:Deep Reader 出题(QuizPanel + MistakeStore + Anki 导出) | 32h |
| Week 4 | E2E demo + 录屏 + 错误路径覆盖 + 性能基线 + 文档齐 | 32h |

---

## 故障排查

| 现象 | 检查 |
|---|---|
| `tianshu-bridge` 命令未找到 | `uv pip install -e .` 或 `source .venv/bin/activate` |
| `/health` 返回 `minimaxConfigured: false` | 检查 `MINIMAX_API_KEY` env |
| `/health` 返回 `vaultWritable: false` | 检查 `OBSIDIAN_VAULT` 路径可写 |
| `/sync` 返回 `vault path ... is not the configured OBSIDIAN_VAULT` | 请求里的 vault 必须 = 启动 env 里的 vault |
| Recall Sticker fetch 失败 | 确认 manifest patch 已应用,Chrome 已重载 |
| Recall Sticker 把 Deep Reader 错题本显示成贴纸 | 确认 sidepanel.js patch 已应用 |
| .md 文件没出现 | 检查 `~/Desktop/知识库/知识库/Inbox/` 目录 |

---

---

## 🆕 Week 2 (shipped) — 真实 M2.1 + 智能整理

### Phase A + B 两阶段 curator

- **Phase A**: 1 次 M2.1 call 拿 batch_tags + per-card tags + merges
- **Phase B**: per-card 1 次 M2.1 call 拿 wiki links(扫 vault 已有的 .md)
- **per-card 容错**: 1 张卡失败不阻塞整批

### M2.1/M3 reasoning block handling

- Week 1 parser 假设 plain content — 实际 M2.1/M3 输出 ` ̶t̶h̶i̶n̶k̶...̶ ̶` 块
- **修复**: `extractContent()` 在 parse 前 strip

### Frontmatter merge on append

- Week 1 是新 sync 替换旧的 — 修复为 union(保留所有历史的 tag)

### Recall Sticker 端

- Side Panel 加 "🧠 同步到 Obsidian" 按钮 + vault path input
- 离线 fallback 用 Blob URL(非 data URL) + chrome.downloads

---

## 🆕 Week 3 (shipped) — 联动 1 完整

### Deep Reader 出题

- T-17 port focus-quiz 的 3 级 fallback(Readability + Turndown + DOM candidates)
- T-19 QuizGenerator: M2.1 buildPrompt + 4 层 JSON fallback + port normalizeP1Question
- **修复**: T-19 max_tokens 2000→4000(M2.1 思考用 2000 tokens 不够输出 JSON)

### 错题本 + Anki 导出

- T-22 MistakeStore + chrome.storage 持久化 + LRU 50/source
- T-23 Anki CSV 导出(port focus-quiz formatMistakesAsAnkiCsv)

### Deep Reader 协议统一 (T-13b)

- **改前**: Anthropic 协议 + M2.1
- **改后**: OpenAI 协议 + M3(与 Tianshu Bridge 一致)
- 加 `chat()` 通用方法 + `extractContent()` thinking strip

---

## 🆕 Week 4 (shipped) — 收尾

### 端到端 demo (T-24/T-25)

- `docs/RECORDING-WEEK-2-3-4.md` 6 场景文字脚本 + 截图位置
- 实测: 3 卡 → 21s → .md 含 Phase A tags + Phase B wiki links
- bridge 进程 kill → 客户端降级 chrome.downloads 离线下载

### 错误路径覆盖 (T-27, 12 scenarios)

- M2.1 non-JSON → 4-layer fallback
- M2.1 truncated JSON → Layer 5 recovery
- vault 路径错 / 不可写 / = /etc → 400
- bridge 503 → 客户端降级
- Readability 失败 → ContentExtractorV2 dom-innertext fallback
- Anki Cloze 注入 → sanitize
- M2.1 thinking → extractContent 剥离
- **修复**: Pydantic RawCard.text min_length=1 max_length=500(Week 1 P3 #4)

### 性能基线 (T-28)

| 操作 | 目标 | 实测 |
|------|------|------|
| 1 卡 mock | < 500ms | ~250ms |
| 5 卡 mock | < 1s | ~680ms |
| 100 卡 mock | < 10s | ~7.5s |
| 5 卡真 M2.1 | < 30s | ~21s |
| bridge 启动 | < 2s | ✓ |

详见 `docs/PERFORMANCE-WEEK-2-3-4.md`

---

## 引用

- [[Project Charter|PROJECT_CHARTER.md]]
- [[PRD|docs/PRD.md]]
- [[Architecture|docs/ARCHITECTURE.md]]
- [[Roadmap|docs/ROADMAP.md]]
- [[Wiki|/Users/mahaoxuan/Documents/trae_projects/api/docs/wiki/00-overview.md]]
- [[Obsidian 镜像页|/Users/mahaoxuan/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md]]
- 飞书记录: `recvnGVDhdkmil` (Yishu Growth base → 通用·小项目)
