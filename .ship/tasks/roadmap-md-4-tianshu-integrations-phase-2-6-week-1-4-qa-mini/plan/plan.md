# Plan · Tianshu Integrations 实现计划

> **task_id**: `roadmap-md-4-tianshu-integrations-phase-2-6-week-1-4-qa-mini`
> **date**: 2026-06-27
> **范围**:Week 1-4 共 30 个 T(peer diff 后微调到 35 个 T 包含新增),123h
> **基于**:spec.md + diff-report.md

---

## 0. 计划结构

按 4 周时间线组织,**每个 T 都有 BDD 行为 + TDD 测试先于实现 + 完成标准**。week 完成 = 端到端可演示。

**核心原则**:
- **风险前移**:P0 风险(manifest 改 / LLM 协议 / mock curator)在 Week 1 解决
- **per-step verifiable**:每个 T 完成后能跑测试 / smoke
- **错误路径先行**:Week 1 就测 offline fallback / vault 路径错

---

## 1. Week 1 · 联动 2 MVP + 风险前移 (35h)

### Day 1 (周一)

#### T-04b · Recall Sticker manifest 加权限 [2h] [P0]

**BDD 行为**:
- Given:用户加载 Recall Sticker
- When:尝试 `fetch('http://127.0.0.1:7733/health')`
- Then:响应成功,不报 `net::ERR_BLOCKED_BY_CLIENT`

**文件**:`Recall-Sticker/manifest.json`

**改动**:
```diff
  "permissions": [
    "activeTab",
    "storage",
    "sidePanel",
    "tabs"
+   "downloads"
  ],
+ "host_permissions": [
+   "http://127.0.0.1:7733/*"
+ ]
```

**验证**:
- `cat Recall-Sticker/manifest.json | python3 -c "import json,sys; m=json.load(sys.stdin); assert 'host_permissions' in m; assert 'http://127.0.0.1:7733/*' in m['host_permissions']; assert 'downloads' in m['permissions']"`
- Chrome 重载扩展,DevTools console 跑 `fetch('http://127.0.0.1:7733/health').then(r => console.log(r.status))` 期望输出 200 / 503(bridge 没起是 503)

---

#### T-04c · sidepanel.js 加 STORAGE_KEY_BLACKLIST [1h] [P0]

**BDD 行为**:
- Given:Recall Sticker sidepanel 打开
- And:chrome.storage 里有 `mistake_log_v1: [{...}]`(Deep Reader 错题本,array-typed)
- And:`lastSyncTime: 1234567890`(number)
- And:`obsidianVaultPath: "/path/to/vault"`(string)
- When:user 点 refresh
- Then:贴纸列表**不**包含 `mistake_log_v1` 的内容
- And:`tags` 列表正常显示

**文件**:`Recall-Sticker/sidepanel.js`

**改动**:
```js
// 在第 47 行 isStickerCollection 加 BLACKLIST
const STORAGE_KEY_BLACKLIST = new Set([
  'tags', 'obsidianVaultPath', 'lastSyncTime', 'mistake_log_v1',
  // 未来 tianshu-integrations 可能加的 key
]);

function isStickerCollection(storageKey, value) {
  return !STORAGE_KEY_BLACKLIST.has(storageKey) && Array.isArray(value);
}
```

**验证**:
- 手动:chrome.storage.local.set({mistake_log_v1: [{q:'test'}]}),refresh,确认不显示
- 自动化(Phase 3 加):`tests/test-sidepanel-storage.js` mock chrome.storage

---

#### T-01 · 项目骨架 + pyproject.toml [2h] [P0]

**BDD 行为**:
- Given:开发者在 `~/Developer/tianshu-integrations`
- When:跑 `pip install -e .`
- Then:`tianshu-bridge` 命令可用
- And:`tianshu_integrations` Python 包可 import

**文件**:
- `~/Developer/tianshu-integrations/pyproject.toml` (新)
- `~/Developer/tianshu-integrations/bridge/__init__.py` (新)
- `~/Developer/tianshu-integrations/curator/__init__.py` (新)
- `~/Developer/tianshu-integrations/obsidian/__init__.py` (新)
- `~/Developer/tianshu-integrations/llm/__init__.py` (新)

**pyproject.toml 关键字段**:
```toml
[project]
name = "tianshu-integrations"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "openai>=1.57.4",  # 用 OpenAI 协议
    "pyyaml>=6.0.0",
    "python-frontmatter>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.21", "httpx>=0.27"]

[project.scripts]
tianshu-bridge = "tianshu_integrations.bridge.cli:main"
```

**验证**:
- `cd ~/Developer/tianshu-integrations && pip install -e .`
- `tianshu-bridge --help` 输出 usage
- `python3 -c "import tianshu_integrations.bridge"` 无错

---

#### T-02 · bridge FastAPI app + /health endpoint [4h] [P0]

**BDD 行为**(TDD 先写测试):
- Given:bridge 启动在 127.0.0.1:7733
- When:GET /health
- Then:200,返回 `{status: 'ok', version, vaultWritable, minimaxConfigured, uptimeSec}`

**TDD 测试**:`tests/test_server.py`
```python
import pytest
from fastapi.testclient import TestClient
from tianshu_integrations.bridge.server import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    return TestClient(app)

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["vaultWritable"] is True
    assert data["minimaxConfigured"] is True
    assert "uptimeSec" in data

def test_health_no_minimax_key(client, monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    r = client.get("/health")
    data = r.json()
    assert data["minimaxConfigured"] is False
```

**实现文件**:`bridge/server.py`
```python
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
START_TIME = time.time()
VERSION = "0.1.0"


@app.get("/health")
def health():
    vault = os.environ.get("OBSIDIAN_VAULT", "")
    return {
        "status": "ok",
        "version": VERSION,
        "vaultWritable": bool(vault) and os.access(vault, os.W_OK),
        "minimaxConfigured": bool(os.environ.get("MINIMAX_API_KEY")),
        "currentVault": vault,
        "uptimeSec": int(time.time() - START_TIME),
    }
```

**验证**:
- `pytest tests/test_server.py -v` 全过
- `curl localhost:7733/health` 返回 200 + JSON

---

### Day 2 (周二)

#### T-03 · bridge CLI 入口 [2h] [P0]

**BDD 行为**:
- Given:`MINIMAX_API_KEY` env 没设
- When:跑 `tianshu-bridge --port 7733 --vault /tmp/vault`
- Then:warning 打印 "MINIMAX_API_KEY 未设置" 但**继续启动**
- And:如果 vault 路径不存在,exit 1 并报错
- And:如果 vault 路径存在但不可写,exit 1 并报错

**TDD 测试**:`tests/test_cli.py`
```python
def test_cli_no_vault_exits(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["tianshu-bridge", "--vault", "/nonexistent"])
    with pytest.raises(SystemExit) as e:
        from tianshu_integrations.bridge.cli import main
        main()
    assert e.value.code == 1
    assert "vault 路径不存在" in capsys.readouterr().err

def test_cli_default_vault(monkeypatch, tmp_path):
    # 没传 --vault, 默认 ~/Desktop/知识库/知识库/
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["tianshu-bridge", "--port", "0"])
    # mock uvicorn.run
    ...
```

**实现文件**:`bridge/cli.py`
```python
import argparse
import os
import sys
import uvicorn

DEFAULT_VAULT = os.path.expanduser("~/Desktop/知识库/知识库")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7733)
    parser.add_argument("--vault", type=os.path.abspath, default=None)
    args = parser.parse_args()

    vault = args.vault or os.environ.get("OBSIDIAN_VAULT") or DEFAULT_VAULT

    if not os.path.isdir(vault):
        print(f"ERROR: vault 路径不存在: {vault}", file=sys.stderr)
        sys.exit(1)
    if not os.access(vault, os.W_OK):
        print(f"ERROR: vault 路径无写权限: {vault}", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("MINIMAX_API_KEY"):
        print("WARN: MINIMAX_API_KEY 未设置,curator 将失败", file=sys.stderr)

    os.environ["OBSIDIAN_VAULT"] = vault
    from tianshu_integrations.bridge.server import app
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
```

**验证**:
- `pytest tests/test_cli.py -v` 全过
- `tianshu-bridge --vault ~/Desktop/知识库` 启动,`curl /health` 返回 200

---

#### T-04 · Pydantic schemas [3h] [P0]

**BDD 行为**:
- Given:JSON 含 `cards: [{text, prefix, suffix, context, sourceUrl, timestamp}]`
- When:Pydantic 校验为 `SyncRequest`
- Then:字段名 + 类型 + 必填全部按 spec §3.1

**TDD 测试**:`tests/test_schemas.py`
```python
def test_rawcard_minimal():
    from tianshu_integrations.bridge.schemas import RawCard
    c = RawCard.model_validate({"text": "test", "sourceUrl": "https://x.com", "timestamp": 123})
    assert c.text == "test"
    assert c.prefix == ""
    assert c.tags == []

def test_syncrequest_valid():
    from tianshu_integrations.bridge.schemas import SyncRequest, RawCard
    req = SyncRequest.model_validate({
        "trigger": "manual",
        "cards": [{"text": "x", "sourceUrl": "u", "timestamp": 1}],
        "obsidianVaultPath": "/tmp/vault",
    })
    assert len(req.cards) == 1
```

**实现文件**:`bridge/schemas.py`
```python
from typing import Literal
from pydantic import BaseModel, Field


class RawCard(BaseModel):
    text: str
    prefix: str = ""
    suffix: str = ""
    context: str = ""
    sourceUrl: str
    tags: list[str] = []
    timestamp: int
    id: str | None = None  # 由 curator 生成


class SyncRequest(BaseModel):
    trigger: Literal["manual", "auto_on_save"]
    cards: list[RawCard]
    obsidianVaultPath: str
    m2xModel: str = "MiniMax-M3"
    minimaxApiKey: str | None = None


class CuratedCard(BaseModel):
    cardId: str
    title: str
    body: str
    tags: list[str]
    wikiLinks: list[str]
    mergedWith: str | None = None


class SkippedCard(BaseModel):
    cardId: str
    reason: str


class CardError(BaseModel):
    cardId: str
    message: str


class SyncResponse(BaseModel):
    success: bool
    curated: list[CuratedCard] = []
    skipped: list[SkippedCard] = []
    errors: list[CardError] = []
    durationMs: int = 0
    obsidianFilesWritten: list[str] = []
```

**验证**:`pytest tests/test_schemas.py -v` 全过

---

### Day 3 (周三)

#### T-05 · POST /sync/recall-sticker endpoint (无 M2.1) [4h] [P0]

**BDD 行为**:
- Given:bridge 启动,vault 路径 OK
- When:POST /sync/recall-sticker 带 `cards: [RawCard x 3]`, `obsidianVaultPath`
- Then:200,返回 `SyncResponse{success: true, curated: 3 个直写 .md 的卡}`
- And:`obsidian_files_written: ["Inbox/2026-06-27-recall.md"]`
- And:实际文件写到 vault/Inbox/2026-06-27-recall.md

**TDD 测试**:`tests/test_server.py` (扩展)
```python
def test_sync_writes_markdown(client, tmp_path):
    r = client.post("/sync/recall-sticker", json={
        "trigger": "manual",
        "cards": [
            {"text": "eBPF", "prefix": "类似", "suffix": "机制", "sourceUrl": "https://x.com", "timestamp": 1},
            {"text": "service mesh", "context": "{{c1::service mesh}} 是微服务通信层", "sourceUrl": "https://x.com", "timestamp": 2},
        ],
        "obsidianVaultPath": str(tmp_path),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["curated"]) == 2
    file = tmp_path / "Inbox" / "2026-06-27-recall.md"
    assert file.exists()
    content = file.read_text()
    assert "eBPF" in content
    assert "service mesh" in content
```

**实现文件**:扩展 `bridge/server.py` + 新建 `obsidian/writer.py`

`obsidian/writer.py`:
```python
from datetime import datetime
from pathlib import Path


def render_card_section(card) -> str:
    # context 兜底: 如果空,用 prefix + text + suffix 拼
    body = card.context or f"{card.prefix} **{card.text}** {card.suffix}"
    # 清理 sourceUrl 追踪参数
    clean_url = card.sourceUrl
    import re
    clean_url = re.sub(r'[?&](utm_\w+|ref)=[^&]*', '', clean_url)
    md = f"## {card.text}\n\n"
    md += f"> {body}\n\n"
    md += f"来源: {clean_url}\n\n"
    return md


def write_batch(curated: list, vault_path: str) -> list[str]:
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = Path(vault_path) / "Inbox" / f"{today}-recall.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        existing = file_path.read_text(encoding="utf-8")
    else:
        all_tags = sorted({t for c in curated for t in c.tags} | {"recall-sticker"})
        existing = f"---\ndate: {today}\ntags: [{', '.join(all_tags)}]\nsource: recall-sticker-sidepanel\n---\n\n# Recall Sticker · {today}\n\n"

    appended = existing + "\n---\n\n".join(render_card_section(c) for c in curated)

    # atomic write: tmp + rename
    tmp = file_path.with_suffix(file_path.suffix + ".tmp")
    tmp.write_text(appended, encoding="utf-8")
    tmp.rename(file_path)

    return [str(file_path.relative_to(vault_path))]
```

**验证**:
- `pytest tests/test_server.py::test_sync_writes_markdown -v` 全过
- 实际启动 bridge + `curl` 测试:文件确实写到 Inbox

---

### Day 4 (周四)

#### T-05b · curator 空骨架 + JSON parser + mock LLM [4h] [P0]

**BDD 行为**:
- Given:curator.curate(cards) 调 mock LLM client
- When:mock LLM 返回 JSON 数组 `[{tags: [...], body: "..."}]`
- Then:curator 解析为 CuratedCard[]
- When:mock LLM 返回非 JSON(故意测 fallback)
- Then:curator 走 fallback parser,至少返回空 CuratedCard[] 不抛异常

**TDD 测试**:`tests/test_curator.py`
```python
def test_curate_with_valid_json_response():
    from tianshu_integrations.curator.curate import curate
    from tianshu_integrations.llm.client import MockLLMClient

    mock = MockLLMClient(response='{"tags": ["k8s"], "rewrites": [{"cardId": "1", "title": "x", "body": "y", "wikiLinks": []}]}')
    cards = [RawCard(text="x", sourceUrl="u", timestamp=1, id="1")]
    result = curate(cards, llm_client=mock)
    assert len(result) == 1
    assert result[0].tags == ["k8s"]


def test_curate_fallback_on_bad_json():
    from tianshu_integrations.curator.curate import curate
    from tianshu_integrations.llm.client import MockLLMClient

    mock = MockLLMClient(response="not json at all, but has #k8s #networking")
    cards = [RawCard(text="x", sourceUrl="u", timestamp=1, id="1")]
    result = curate(cards, llm_client=mock)
    # fallback: naive tag extraction
    assert isinstance(result, list)


def test_curate_per_card_isolation():
    """per-card 容错: 1 张卡失败不阻塞其他"""
    mock = MockLLMClient(responses=[
        '{"tags": ["ok"], "rewrites": [...]}',
        "INVALID_JSON_THAT_FAILS_ALL_PARSERS",
        '{"tags": ["ok2"], "rewrites": [...]}',
    ])
    cards = [
        RawCard(text="a", sourceUrl="u", timestamp=1, id="1"),
        RawCard(text="b", sourceUrl="u", timestamp=2, id="2"),  # 失败
        RawCard(text="c", sourceUrl="u", timestamp=3, id="3"),
    ]
    curated, errors = curate(cards, llm_client=mock)
    assert len(curated) == 2
    assert len(errors) == 1
    assert errors[0].cardId == "2"
```

**实现文件**:
- `curator/curate.py` (主入口)
- `curator/parsers.py` (JSON 多层 fallback)
- `llm/client.py` (MiniMax OpenAI client + MockLLMClient)

`curator/parsers.py`:
```python
import json
import re
from typing import Any


def parse_curation_response(raw: str) -> dict:
    """M2.1 返回可能不稳,逐层降级。"""
    # 1. 严格 JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 提取第一个 {...} 块
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # 3. ```json ... ``` 块
    m = re.search(r'```json\s*(.+?)\s*```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 4. 单字段降级: naive tag 提取
    return {"tags": _extract_tags_naive(raw), "rewrites": []}


def _extract_tags_naive(text: str) -> list[str]:
    """从自由文本中找 #hashtag"""
    return re.findall(r'#(\w+)', text)[:5]
```

`curator/curate.py`:
```python
from tianshu_integrations.bridge.schemas import RawCard, CuratedCard, CardError
from tianshu_integrations.curator.parsers import parse_curation_response


PROMPT_TEMPLATE = """你是知识整理助手。给定以下 recall-sticker 卡片:
{cards}

对每张卡:
1. 打 1-3 个 tag
2. 改写为 Obsidian Markdown
3. 建议双向链接

返回 JSON: {{"tags": [...], "rewrites": [{{"cardId": "...", "title": "...", "body": "...", "wikiLinks": ["[[...]]"]}}]}}"""


def sanitize_context(card: RawCard) -> RawCard:
    """把 Anki Cloze {{c1::text}} 转成 [text],避免 M2.1 prompt 注入"""
    import re
    if card.context:
        card.context = re.sub(r'\{\{c\d+::(.*?)\}\}', r'[\1]', card.context)
    return card


def curate(cards: list[RawCard], llm_client) -> tuple[list[CuratedCard], list[CardError]]:
    curated = []
    errors = []
    sanitized = [sanitize_context(c) for c in cards]
    cards_text = "\n".join(f"[{c.id or c.timestamp}] {c.text} | ctx: {c.context}" for c in sanitized)

    try:
        raw = llm_client.chat(PROMPT_TEMPLATE.format(cards=cards_text))
        parsed = parse_curation_response(raw)
        rewrites = {r["cardId"]: r for r in parsed.get("rewrites", [])}
        for c in sanitized:
            cid = c.id or str(c.timestamp)
            if cid in rewrites:
                r = rewrites[cid]
                curated.append(CuratedCard(
                    cardId=cid, title=r.get("title", c.text),
                    body=r.get("body", c.context or f"{c.prefix} {c.text} {c.suffix}"),
                    tags=parsed.get("tags", [])[:3],
                    wikiLinks=r.get("wikiLinks", []),
                ))
            else:
                # 静默跳过,curator 没输出对应卡
                curated.append(CuratedCard(
                    cardId=cid, title=c.text,
                    body=c.context or f"{c.prefix} {c.text} {c.suffix}",
                    tags=[], wikiLinks=[],
                ))
    except Exception as e:
        # 整批失败: 把所有卡降级为直写
        for c in sanitized:
            errors.append(CardError(cardId=c.id or str(c.timestamp), message=str(e)))
    return curated, errors
```

`llm/client.py`:
```python
import os
from openai import AsyncOpenAI
from typing import Any


class MiniMaxClient:
    """OpenAI 协议(/v1/chat/completions) — 与 deep-reader minimax.ts 统一"""
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.minimaxi.com/v1", model: str = "MiniMax-M3"):
        self.client = AsyncOpenAI(
            api_key=api_key or os.environ["MINIMAX_API_KEY"],
            base_url=base_url,
        )
        self.model = model

    async def chat(self, prompt: str) -> str:
        r = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return r.choices[0].message.content


class MockLLMClient:
    """测试用,接受预设 response 或 response 列表(per-call)"""
    def __init__(self, response: str | list[str] = ""):
        self.responses = [response] if isinstance(response, str) else response
        self.call_count = 0

    async def chat(self, prompt: str) -> str:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]
```

**验证**:
- `pytest tests/test_curator.py -v` 全过(3 个测试覆盖 valid / fallback / per-card 隔离)
- 同时验证了 D-22(per-card 容错) + D-08(context 预处理)

---

### Day 5 (周五)

#### T-06 · 集成 endpoint 调 curator [3h] [P0]

**BDD 行为**:
- Given:bridge 启动,MINIMAX_API_KEY 已设
- When:POST /sync/recall-sticker 带 cards
- Then:走完整 pipeline = schemas → curator → writer → response

**TDD 测试**:`tests/test_server.py::test_sync_full_pipeline`
```python
def test_sync_full_pipeline(client, tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    from tianshu_integrations.llm.client import MockLLMClient
    from tianshu_integrations.bridge.server import app
    app.dependency_overrides[MiniMaxClient] = lambda: MockLLMClient(
        response='{"tags": ["k8s"], "rewrites": [{"cardId": "1", "title": "eBPF", "body": "内核技术", "wikiLinks": []}]}'
    )
    r = client.post("/sync/recall-sticker", json={...})
    assert r.json()["success"] is True
    # 验证 .md 含 M2.1 整理后的 tags
    content = (tmp_path / "Inbox" / "2026-06-27-recall.md").read_text()
    assert "#k8s" in content
```

**实现**:扩展 `bridge/server.py` 的 `/sync/recall-sticker` 调 curator + writer

**验证**:`pytest -v` 全过,文件实际生成

---

#### T-07 · storage-collector.js (Recall Sticker 端) [2h] [P0]

**BDD 行为**:
- Given:chrome.storage 里有 3 个 url-key,每个 2 张卡
- When:调 `collectAllStickers()`
- Then:返回 6 张卡片的 flat list,每张含完整 sourceUrl

**实现文件**:`Recall-Sticker/lib/storage-collector.js`
```js
export function collectAllStickers() {
  return new Promise((resolve) => {
    chrome.storage.local.get(null, (result) => {
      const BLACKLIST = new Set(['tags', 'obsidianVaultPath', 'lastSyncTime', 'mistake_log_v1']);
      const stickers = [];
      for (const [key, value] of Object.entries(result)) {
        if (BLACKLIST.has(key)) continue;
        if (!Array.isArray(value)) continue;
        for (const s of value) {
          stickers.push({
            id: String(s.timestamp) + '_' + s.text.slice(0, 10),
            text: s.text,
            prefix: s.prefix || '',
            suffix: s.suffix || '',
            context: s.context || '',
            sourceUrl: s.sourceUrl || '',
            tags: [],  // Recall Sticker 当前不打 tag
            timestamp: s.timestamp,
          });
        }
      }
      resolve(stickers);
    });
  });
}
```

**验证**:手动 Chrome DevTools console 跑 `collectAllStickers().then(console.log)`

---

#### T-08 · bridge-client.js (Recall Sticker 端) [3h] [P0]

**BDD 行为**:
- Given:bridge 启动,recall-sticker 卡片已收集
- When:调 `syncToBridge(cards, {vaultPath: '...'})`
- Then:POST /sync/recall-sticker 成功,返回 success
- When:bridge 没起,fetch 抛 TypeError
- Then:降级到 `chrome.downloads.download` .md,返回 `{mode: 'offline_fallback'}`

**实现文件**:`Recall-Sticker/lib/bridge-client.js`
```js
export async function syncToBridge(cards, options) {
  const { vaultPath, apiKey, timeout = 30000 } = options;
  try {
    const r = await fetch('http://127.0.0.1:7733/sync/recall-sticker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trigger: 'manual',
        cards,
        obsidianVaultPath: vaultPath,
        minimaxApiKey: apiKey,
      }),
      signal: AbortSignal.timeout(timeout),
    });
    if (r.status === 503) throw new Error('bridge not ready');
    if (!r.ok) throw new Error(`bridge error ${r.status}`);
    const data = await r.json();
    return { success: true, mode: 'online', response: data };
  } catch (err) {
    // offline fallback
    const { cardsToMarkdown } = await import('./obsidian-exporter.js');
    const md = cardsToMarkdown(cards, vaultPath);
    const filename = `recall-stickers-${new Date().toISOString().slice(0, 10)}.md`;
    const dataUrl = 'data:text/markdown;base64,' + btoa(unescape(encodeURIComponent(md)));
    const downloadId = await chrome.downloads.download({
      url: dataUrl,
      filename,
      saveAs: true,
    });
    return { success: true, mode: 'offline_fallback', downloadId, error: err.message };
  }
}

export async function checkBridgeHealth() {
  try {
    const r = await fetch('http://127.0.0.1:7733/health');
    if (!r.ok) return { ok: false, error: `HTTP ${r.status}` };
    return { ok: true, data: await r.json() };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
```

**验证**:
- bridge 在线:smoke test,console 看到 success
- bridge 离线:kill bridge,触发 .md 下载

---

#### M2 验收 · Week 1 完成标准

✅ `tianshu-bridge` 启动,`curl /health` 200
✅ Recall Sticker 加完 host_permissions + downloads 权限
✅ sidepanel.js 加 STORAGE_KEY_BLACKLIST
✅ POST /sync/recall-sticker 直写 .md 跑通(无 M2.1)
✅ mock curator 跑通 + per-card 容错
✅ storage-collector + bridge-client 实现
✅ Obsidian Inbox 出现 .md 文件

**总估时**:35h(实际比原 23h 多 12h 用于风险前移)

---

## 2. Week 2 · 联动 2 完整 + 智能整理 (36h)

### Day 1 (周一)

#### T-09 · MiniMax OpenAI client (实际) [4h] [P0]

**BDD 行为**:
- Given:MiniMax API key 已设
- When:调 `client.chat("Hello")`
- Then:返回 MiniMax 响应(实际打 API,不 mock)

**TDD 测试**:`tests/test_llm_client.py::test_real_minimax` — 跳过如果没有 key,否则真打
```python
@pytest.mark.skipif(not os.environ.get("INTEGRATION_TEST"), reason="needs real API key")
async def test_real_minimax():
    client = MiniMaxClient()
    r = await client.chat("用一句话回答: 1+1=?")
    assert len(r) > 0
```

**实现**:已经在 T-05b 写完,这里只补 `__init__.py` 导出 + 单元测试覆盖错误路径(401, 429, 500)

---

#### T-13b · Deep Reader minimax.ts 协议统一 + M3 [3h] [P0]

**BDD 行为**:
- Given:Deep Reader 加载到 Chrome
- When:用户点 AI 助手发问
- Then:走 OpenAI 协议(/v1/chat/completions),model = `MiniMax-M3`

**文件**:`api/deep-reader/src/lib/minimax.ts` 改

**改动**:
```diff
- apiHost: import.meta.env.VITE_MINIMAX_API_HOST || 'https://api.minimaxi.com/anthropic',
+ apiHost: import.meta.env.VITE_MINIMAX_API_HOST || 'https://api.minimaxi.com/v1',

// callAPI 改:
- const response = await fetch(`${activeConfig.apiHost}/v1/messages`, {
+ const response = await fetch(`${activeConfig.apiHost}/chat/completions`, {
    method: 'POST',
    headers: { ... 'Authorization': `Bearer ${activeConfig.apiKey}` },
    body: JSON.stringify({
-     model: 'MiniMax-M2.1',
+     model: 'MiniMax-M3',
      max_tokens: maxTokens,
-     messages: [{ role: 'user', content: prompt }],
+     messages: [{ role: 'user', content: prompt }],
    }),
  });

- // parse
- const firstBlock = data.content[0];
- return firstBlock.type === 'text' ? firstBlock.text : '';
+ // OpenAI 协议 parse
+ return data.choices[0].message.content || '';
```

**验证**:
- `npm run build` 通过
- 加载到 Chrome,AI 助手能用

---

### Day 2-3 (周二-周三)

#### T-10 · Curator 实际 LLM 集成 [8h] [P0]

**BDD 行为**:
- Given:10 张 sample 卡片
- When:`curate(cards, llm_client=MiniMaxClient())`
- Then:返回 10 个 CuratedCard,每个含 M2.1 打的 tag

**实现**:扩 T-05b curator 加 prompt 调优 + 测试集
- `curator/prompts.py` 提 prompt 模板
- 加评测集 `tests/fixtures/sample-10-cards.json` + `expected-tags.json`
- 跑评测,看 tag 准确率

**验证**:
- `pytest tests/test_curator.py -v` 全过
- 评测集准确率 ≥ 70%(10 张卡里至少 7 张 tag 合理)

---

#### T-11 · Prompt 模板与评测集 [4h] [P0]

**实现**:`curator/prompts.py`
```python
CURATE_PROMPT = """你是知识整理助手。

输入:从网页上随手贴的"我想记住"的卡片,每张含:
- text(关键词)
- prefix/suffix(上下文)
- context(完整句)
- sourceUrl(来源 URL)

任务:对每张卡返回:
1. title:简短标题(≤15字)
2. body:改写为 Obsidian Markdown 格式(≤100字)
3. tags:1-3 个 tag(英文或中文,无 #)
4. wikiLinks:[] 双向链接建议(Phase 1 留空)

要求:
- tag 应该语义化(不是 text 本身)
- body 改写保持原意,但更清晰
- 如果多张卡主题相同,合并到同一组 tags

返回 JSON:
{
  "tags": ["tag1", "tag2", ...],  // 本批所有 unique tag
  "rewrites": [
    {"cardId": "id1", "title": "...", "body": "...", "wikiLinks": []},
    ...
  ]
}

卡片:
{cards_text}
"""
```

**评测集**:`tests/fixtures/sample-10-cards.json` — 10 张精心构造的卡,人工标 expected tag

---

### Day 4-5 (周四-周五)

#### T-12 · JSON parser 健壮性 [3h] [P0]

**TDD 测试**:`tests/test_parsers.py`
- 12 种边界:严格 JSON / 嵌套 {} / markdown 包裹 / 多余 ``` / 截断 JSON / 单字段降级 / unicode / emoji / 极端长 / 空对象 / 数组 / null
- 每种 parser 路径都要 1 个测试

---

#### T-13 · ObsidianWriter 增强 [4h] [P0]

**BDD 行为**:
- Given:curated cards 含 tags 和 wikiLinks
- When:`write_batch(curated, vault)`
- Then:.md 含 YAML frontmatter,每张卡 section 渲染 tags + wikiLinks

**TDD 测试**:`tests/test_writer.py`
```python
def test_writer_with_tags_and_links(tmp_path):
    curated = [
        CuratedCard(cardId="1", title="eBPF", body="内核技术", tags=["linux", "kernel"], wikiLinks=[["[eBPF]]"]]),
    ]
    files = write_batch(curated, str(tmp_path))
    content = (tmp_path / "Inbox" / f"{today}-recall.md").read_text()
    assert "---" in content
    assert "tags: [linux, kernel]" in content
    assert "# linux" in content
    assert "[[eBPF]]" in content
```

---

#### T-14 · obsidian-exporter.js (本地 .md 生成) [3h] [P0]

**BDD 行为**:
- Given:cards 数组
- When:`cardsToMarkdown(cards, vaultPath)`
- Then:返回 markdown 字符串,跟 bridge 端格式**完全一致**

**实现文件**:`Recall-Sticker/lib/obsidian-exporter.js`
- 直接 import 不了 Python 的 writer,**手写一份**保持格式一致
- 文件头 frontmatter + 每张卡 ## section + tags + wikiLinks

**验证**:`tests/test-obsidian-exporter.js`(Phase 3 用 vitest 跑)

---

#### T-15 · 离线 fallback 完整测试 [3h] [P0]

**TDD 测试**:`tests/test-bridge-client.js`(vitest)
```js
test('offline_fallback when bridge not running', async () => {
  global.fetch = vi.fn(() => Promise.reject(new TypeError('Failed to fetch')));
  // mock chrome.downloads.download
  const result = await syncToBridge(cards, {vaultPath: '/tmp'});
  expect(result.mode).toBe('offline_fallback');
});
```

---

#### T-16 · Side Panel 加按钮 [4h] [P0]

**BDD 行为**:
- Given:用户打开 Side Panel
- When:看到 "🧠 同步到 Obsidian" 按钮
- And:点按钮 → 调 syncToBridge
- Then:显示 "正在同步... 已同步 X / Y"
- And:完成后显示 "已同步 5 张卡片 → /Inbox/2026-06-27-recall.md"

**文件**:`Recall-Sticker/sidepanel.html` + `sidepanel.js`

**改动**:
- HTML:加按钮 + vault path input + 状态 div
- JS:绑 click → 调 syncToBridge → 更新状态

---

#### M4 验收 · Week 2 完成标准

✅ POST /sync/recall-sticker 走完整 curator pipeline
✅ M2.1 tag 准确率 ≥ 70%(10 张评测集)
✅ Side Panel "🧠 同步" 按钮工作
✅ bridge 不可达时 .md 自动下载
✅ atomic write 不留半文件
✅ 错误路径覆盖(401/429/500/vault 路径错)

**总估时**:36h

---

## 3. Week 3 · 联动 1 实现 (32h)

### Day 1-2 (周一-周二)

#### T-17 · ContentExtractorV2 [6h] [P0]

**BDD 行为**:
- Given:任意网页
- When:`ContentExtractorV2.extract()`
- Then:返回 `ExtractedContentV2{title, content, url, engine}`
- And:`engine` 字段标识用了哪条路径(`readability-turndown` / `readability-innertext` / `dom-innertext`)

**TDD 测试**:`src/lib/content-extractor-v2.test.ts`
```ts
test('extract with readability', () => {
  // mock document with simple article
  const result = ContentExtractorV2.extract();
  expect(result.engine).toMatch(/readability/);
  expect(result.content.length).toBeGreaterThan(100);
});

test('fallback to dom innertext when readability fails', () => {
  // mock @mozilla/readability throw
  // 验证仍能返回 content
});
```

**实现**:`src/lib/content-extractor-v2.ts`
- 用现有 `@mozilla/readability`(npm)
- 三级 fallback:Readability+Turndown → Readability+innerText → candidates DOM innerText(port focus-quiz 思路)
- 加 `engine` 字段标识

---

#### T-18 · quiz-types.ts [3h] [P0]

**实现**:按 spec §3.3 写 + vitest 测试

---

#### T-19 · QuizGenerator [8h] [P0]

**BDD 行为**:
- Given:extracted content 2000 字
- When:`generate(content, {count: 3, focus: ['trap', 'counterfactual']})`
- Then:返回 3 个 Question,每个含 type/question/options/correct/explanation/evidenceQuote

**TDD 测试**:`src/lib/quiz-generator.test.ts`
```ts
test('generate returns N questions', async () => {
  const gen = new QuizGenerator(minimaxClient);
  const qs = await gen.generate(mockContent, {count: 3});
  expect(qs.length).toBe(3);
  expect(qs[0].type).toMatch(/trap|counterfactual|transfer/);
});

test('handles non-JSON M2.1 response', async () => {
  // mock minimax 返回非 JSON
  // 验证 QuizGenerator 走 fallback,返回 [] 或 throw with friendly error
});
```

**实现**:`src/lib/quiz-generator.ts`
- prompt builder
- call MiniMaxClient (走 OpenAI 协议 from T-13b)
- JSON parse + fallback

---

### Day 3-4 (周三-周四)

#### T-20 · ReaderPanel 加按钮 [2h] [P0]

**改动**:`src/content/components/ReaderPanel.ts:64-78` 头部加按钮

---

#### T-21 · QuizPanel 组件 [8h] [P0]

**BDD 行为**:
- Given:QuizPanel 打开
- When:显示题目 + 4 个选项
- And:用户点选项 → 立即显示 explanation + evidenceQuote
- And:自动保存 MistakeRecord(如果答错)
- Then:做完所有题后显示统计 + 错题 list

**实现**:`src/content/QuizPanel.ts`
- Shadow DOM 隔离
- 题/选项/答题/反馈 4 状态
- 错题立即存 MistakeStore

---

#### T-22 · MistakeStore + LRU [6h] [P0]

**BDD 行为**:
- Given:同一篇文章答错 60 道题
- When:`save(record)` 第 60 次
- Then:总数保持 ≤50(sourceUrl hash 维度),最早的被淘汰

**TDD 测试**:`src/lib/mistake-store.test.ts`
```ts
test('lru cap at 50 per sourceUrl', async () => {
  for (let i = 0; i < 60; i++) {
    await store.save({...mockRecord, timestamp: i});
  }
  const list = await store.list('hash1');
  expect(list.length).toBe(50);
  expect(list[0].timestamp).toBe(10);  // 最早的被淘汰
});
```

---

#### T-23 · Anki 导出 [3h] [P0]

**BDD 行为**:
- Given:mistake log
- When:`formatMistakesAsAnkiCsv(log)`
- Then:返回 Anki Cloze CSV,字段 `Front\tBack\tSource\tEvidence\tTags`

**实现**:port `focus-quiz/sidepanel-logic.js:228-250`

---

#### M6 验收 · Week 3 完成标准

✅ Deep Reader "📝 开始测验" 工作
✅ 3 道题 < 8s 出题
✅ 答错自动进 mistake_log_v1
✅ chrome.storage LRU 工作
✅ Anki CSV 导出格式正确

**总估时**:32h

---

## 4. Week 4 · E2E + QA + 收尾 (32h)

### Day 1 (周一)

#### T-24 · 联动 2 E2E [4h] [P0]

**BDD 行为**:
- Given:用户用 Recall Sticker 在 5 个不同网页贴 5 张卡
- And:bridge 启动,vault 路径 OK
- When:用户开 Side Panel → 点"🧠 同步到 Obsidian"
- Then:Obsidian Inbox 出现 1 个 .md 文件,含 5 张卡的整理结果
- And:每张卡有 M2.1 打的 tag + 改写的 body
- And:frontmatter 含 date/tags/source

**验证**:
- 手动 Chrome 端到端跑
- `obsidian-cli open ~/Desktop/知识库/知识库/Inbox/2026-06-27-recall.md` 验证文件可读

---

#### T-25 · 联动 1 E2E [4h] [P0]

**BDD 行为**:
- Given:用户打开一篇 3000 字博客
- And:Deep Reader 加载
- When:用户按 Alt+D → 点 "📝 开始测验"
- Then:8s 内出现 3 道题
- And:答错 → 错题本存了
- And:导出 Anki CSV → 导入 Anki 显示 Cloze 正确

**验证**:手动 Chrome 端到端

---

#### T-26 · 录屏 + 用户验收 [4h] [P0]

**录屏**:
- 联动 2 完整流程(2min)
- 联动 1 完整流程(2min)
- 离线 fallback 演示(1min)

---

### Day 2 (周二)

#### T-27 · 错误路径覆盖 [6h] [P0]

**测试**:
- vault 路径不存在 → endpoint 400
- M2.1 timeout(>30s) → 504,per-card 容错
- Readability 全失败(无 article 元素) → 仍能 fallback 到 innerText
- chrome.storage 满 10MB → MistakeStore LRU 淘汰
- bridge 端口被占 → 启动 fail
- bridge M2.1 key 缺 → 启动 warn + /sync 返回 502
- SPA 站点(reactjs.org)→ Readability 失败 → fallback

---

#### T-30 · SPA E2E [4h] [P0]

**场景**:在 reactjs.org 跑联动 1
- Readability 失败 → 三级 fallback
- 联动 1 出题仍能跑

---

### Day 3-4 (周三-周四)

#### T-28 · 性能基线 [4h] [P0]

**测**:
- 出题 P95 < 8s(测 20 次)
- 同步 20 卡 P95 < 30s(测 5 次)
- bridge 内存 < 200MB(运行 1h 后)

---

#### T-29 · README + INSTALL [4h] [P0]

**README.md** 含:
- 项目说明
- 5 分钟快速开始(装 bridge + 改两个 manifest + 跑)
- 联动 1 怎么用
- 联动 2 怎么用
- 故障排查

**INSTALL.md** 含:
- 依赖安装步骤
- 环境变量配置
- 首次启动 checklist

---

#### T-30b · 飞书 + Obsidian 同步 [2h] [P0]

**飞书**:
- 更新 `recvnGVDhdkmil` 记录状态:已完成 → 关闭

**Obsidian**:
- 更新 `03 Projects/Tianshu Integrations/index.md` 加 Phase 2-6 进度

---

#### M8 验收 · Week 4 完成标准

✅ 联动 1+2 端到端跑通
✅ 录屏 + 用户验收
✅ 4 类错误路径覆盖(vault/M2.1/Readability/storage)
✅ 性能基线达标
✅ README + INSTALL 完整
✅ 飞书 + Obsidian 同步

**总估时**:32h

---

## 5. 总估时汇总

| Week | T 数 | 估时 |
|---|---|---|
| 1 | 8 + 3 新增 | 35h |
| 2 | 8 + 1 新增 | 36h |
| 3 | 7 + 估时调整 | 32h |
| 4 | 7 + 1 新增 | 32h |
| **总计** | **35** | **135h ≈ 17 个工作日** |

相比原 113h,多 22h 用于风险前移 + 几个 peer 发现的隐藏 P0。

---

## 6. Hard Cut 验收(整体)

| 项 | 验证 |
|---|---|
| **联动 2 E2E** | 5 张卡 → Obsidian .md < 60s |
| **联动 1 E2E** | 3000 字文章 → 3 题 < 8s |
| **离线 fallback** | kill bridge → .md 下载 |
| **Anki 导出** | .csv 导入 Anki Cloze 正确 |
| **错误路径** | 4 类覆盖 |
| **性能** | 出题 P95 < 8s, 同步 20 卡 P95 < 30s |
| **文档** | README + INSTALL + 5 份 PM doc 更新到飞书/Obsidian |

---

## 7. 引用

- [[Spec|./spec.md]]
- [[Diff Report|./diff-report.md]]
- [[Project Charter|~/Developer/tianshu-integrations/PROJECT_CHARTER.md]]
- [[Roadmap|~/Developer/tianshu-integrations/docs/ROADMAP.md]]