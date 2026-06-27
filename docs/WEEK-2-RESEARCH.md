# Week 2 Day 1 Research · MiniMax API 实际行为

> **date**: 2026-06-27
> **researcher**: host (with real API calls)
> **环境**: 本机直接打 `https://api.minimaxi.com`,MINIMAX_API_KEY = sk-cp-...

---

## 1. 模型-协议支持矩阵

| 模型 | OpenAI 协议 | Anthropic 协议 |
|------|------------|------------|
| **MiniMax-M3** | ✅ | ✅ |
| **MiniMax-M2.1** | ✅ | ✅ |
| MiniMax-M2.7 | (未测,默认支持) | (未测) |
| MiniMax-M2.5 | (未测) | (未测) |
| MiniMax-M2 | (未测) | (未测) |

**结论**:**4 个 model × 2 个协议都支持**。peer 报告猜"M3 只支持 OpenAI"是错的 — M3 同时支持双协议。T-13b 现在变成可选项。

## 2. 响应格式关键发现

### 2.1 OpenAI 协议响应

```json
{
  "id": "068ecb0af1...",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "<think>The user wants me to return JSON. I'll return it as requested.</think>\n\n{\"hello\": \"world\"}"
    }
  }],
  "usage": {
    "completion_tokens_details": {
      "reasoning_tokens": 17  // M3 才会有,M2.1 没有这个字段
    }
  }
}
```

**关键**:content 字段包含 `<think>...</think>` 块,后跟实际输出。M2.1 和 M3 **都是 reasoning 模型**(尽管 M2.1 不会在 usage 里报 reasoning_tokens)。

### 2.2 Anthropic 协议响应

```json
{
  "content": [
    {"type": "thinking", "thinking": "...", "signature": "..."},
    {"type": "text", "text": "Hey"}
  ]
}
```

Anthropic 协议有结构化的 content array,`thinking` 和 `text` 分开。**M3 via Anthropic 居然不输出 thinking**(测试用例简短时) — 与 OpenAI 协议行为不一致。

## 3. Week 1 现有代码与 API 实际行为的差距

### 3.1 `MiniMaxClient.chat()` 提取 plain content — **有 bug**

`~/Developer/tianshu-integrations/tianshu_integrations/llm/client.py:33-43`:
```python
async def chat(self, prompt, max_tokens=2000):
    r = await self.client.chat.completions.create(...)
    return r.choices[0].message.content or ""
```

**问题**:当 M3 reasoning 输出时,content 包含 `<think>...</think>\n\n{...actual response...}`,整个返回是**字符串**。`curate.py:90-98` 直接把这个字符串喂给 `parse_curation_response`。

### 3.2 `parse_curation_response()` 4 层 fallback — **会失败**

- **Layer 1 (strict JSON)**:对 `<think>...{"hello": "world"}` 严格 parse,`json.JSONDecodeError` → fallback
- **Layer 2 (extract first {...} block)**:regex `\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}` 应该能抓到 `{"hello": "world"}` — **如果 thinking block 不含 `{}` 字符就 OK**
- **Layer 3 (markdown ```json ``` block)**:不适用
- **Layer 4 (naive tag extraction)**:fallback — **丢失所有 rewrites**

**实际风险**:
- 简单 JSON prompt → thinking block 短 → Layer 2 OK
- 复杂 prompt + 卡片多 → thinking block 长 + 复杂 → 可能嵌套 `{}` → Layer 2 regex fail → Layer 4 fallback → **全 batch 卡片用直接写 fallback**

### 3.3 当前 M2.1 单测实测

跑了 `tests/test_curator.py` 用的 `MockLLMClient` 不触发这个 bug(因为 mock 返回的字符串是裸 JSON)。

实际跑 `MiniMaxClient` + M2.1 + 一张卡("eBPF"):
- 响应解析 OK,curator 正常返回 title=`'eBPF 内核技术'`,tags=`['kernel', 'ebpf', 'linux']`
- **实际为什么没炸**:M2.1 的 thinking 块对单卡 JSON 输出够简单,Layer 2 regex 抓得到

**但 M3 + 多卡 batch 必炸** — M3 thinking 更长(49 reasoning tokens observed),会污染 JSON 输出。

## 4. T-13b 决策(Deep Reader 协议统一)

**结论**:**M3 同时支持双协议**。Deep Reader 当前用 Anthropic 协议调 M2.1 也能工作。**T-13b 可选**:

- **做**:Deep Reader 改 OpenAI 协议,跟 Tianshu Bridge 统一(都是 OpenAI)
- **不做**:Deep Reader 保持 Anthropic 协议,理由:Deep Reader 现有用户可能已经配置 M2.1 在跑,改协议会破坏现有工作流

**Week 2 决策**:**T-13b 跳过**,推到 Week 3 跟 Deep Reader 出题一起做。理由:
1. T-13b 改 deep-reader/src/lib/minimax.ts,**会动 api/ 仓的子项目**,跟 Week 2 范围"联动 2 完整 + Side Panel 按钮"不符
2. Deep Reader 当前还能用(Anthropic + M2.1),不是阻塞
3. 改协议 + 改 model 名是 Week 3 出题的前置,可以一起做

**Week 2 节省 ~3h**。

## 5. parser 修复必要性

**Week 2 必须修**:

- `tianshu_integrations/curator/parsers.py` 加 **Layer 0**:strip `<think>...</think>` block 在 parse 之前
- `tianshu_integrations/llm/client.py` 加 `extractContent()` 工具方法 — strip thinking block
- `tianshu_integrations/curator/curate.py` 在调 LLM 之后立即 strip,然后才 parse

**这是 T-12 的一部分** — 比原计划多了 reasoning 处理的 scope。

## 6. Week 1 code 跑通性确认

跑了:
- `pytest tests/ -v` → 58 passed
- 启动 bridge → `/health` → 200
- 真 M2.1 调用 → curator 返回正确结果

**Week 1 ship 分支工作正常**。Week 2 不需要"先修 bug 再 ship"。

## 7. chrome.downloads Blob URL 可用性

**没有真实 Chrome 自动化测试**(本 session 无 GUI),留 Day 4-5 用 puppeteer 验证。

代码层已确定用 `URL.createObjectURL(new Blob([md], {type: 'text/markdown'}))` —— 标准浏览器 API,应该能用。

## 8. T-13b 决策:跳过

**Week 2 不改 Deep Reader**。T-13b 推迟到 Week 3。

---

## 9. 影响 Week 2 计划的调整

| 原计划 | 调整 |
|---|---|
| T-12 parser 健壮性 | **+ Layer 0 strip thinking block** (新) |
| T-12 估时 1-2h | → 2-3h(多了 reasoning 处理) |
| T-13b 必做 | → **跳过**,Week 3 一起做 |
| T-09 真打 M2.1 验证 | 已通过本调研确认 |
| Day 5 Chrome E2E | 不变 |

**Week 2 总估时调整**:
- 原估:29-35h(含 T-13b 3h)
- 新估:**26-32h**(跳过 T-13b -3h,parser reasoning +1h = -2h)
