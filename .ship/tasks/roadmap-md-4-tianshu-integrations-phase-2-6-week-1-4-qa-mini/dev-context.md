# Dev Context · Tianshu Integrations

## Test Command

```bash
# Python (bridge + curator + obsidian + llm)
cd ~/Developer/tianshu-integrations
pip install -e ".[dev]"
pytest tests/ -v --tb=short

# Bridge 启动 smoke test (T-02/03)
tianshu-bridge --port 7733 --vault /tmp/test-vault &
sleep 2
curl http://127.0.0.1:7733/health
kill %1 2>/dev/null

# Recall Sticker (无 build,直接改文件后 Chrome 重载)
# 手动验证:Chrome → chrome://extensions → Recall Sticker → 点 ↻
```

## Code Conduct

**Python**:
- 不可变性(CLAUDE.md Rule 2):dict → 返回新 dict,list → 返回新 list
- 错误处理:try/except 显式 + 用户友好消息
- 类型注解:函数签名必填,内部变量可选
- 命名:snake_case,类 PascalCase,常量 UPPER_SNAKE

**JavaScript (Recall Sticker)**:
- IIFE / Promise 风格保持兼容原项目
- chrome.storage API 用 callback 风格(原项目风格),**不引入** async/await 改写原项目代码
- 命名:现有项目是 camelCase,不强行改 snake

**TypeScript (Deep Reader)**:
- 不可变性(spread operator)
- Zod 或 TS interface 做 schema
- async/await + try/catch
- 不引入新依赖,沿用 @mozilla/readability / minimax client

## Pattern References

### Story T-04b · Recall Sticker manifest
- Reference: `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/manifest.json`
- Mirror: 现有 `permissions` 数组结构,加 `host_permissions` 数组
- Deviations: **不直接 commit 到 Recall-Sticker 仓**,生成 patch 文件 `patches/recall-sticker-manifest.patch` 供用户手动应用

### Story T-04c · sidepanel.js blacklist
- Reference: `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/sidepanel.js:46-48`
- Mirror: 现有 `isStickerCollection` 函数签名,加 BLACKLIST 检查
- Deviations: 同上,生成 patch 文件

### Story T-01 / T-02 / T-03 / T-04 / T-05 / T-05b / T-06 · bridge Python 代码
- Reference: 借鉴 `/Users/mahaoxuan/Documents/trae_projects/api/Mini-Agent/mini_agent/llm/openai_client.py`(openai SDK 用法 + retry 思路)
- Mirror: Pydantic v2 model style, FastAPI 路由风格
- Deviations: 不 import mini_agent 任何东西(避免依赖 prompt_toolkit)

### Story T-07 / T-08 · Recall Sticker JS 代码
- Reference: `/Users/mahaoxuan/Documents/trae_projects/recall-sticker/Recall-Sticker/sidepanel.js`
- Mirror: chrome.storage API + callback 风格 + export function
- Deviations: 新加文件 `lib/storage-collector.js` + `lib/bridge-client.js` + `lib/obsidian-exporter.js`,通过 `<script>` 标签在 sidepanel.html 引入

## Waves

Week 1 = 11 个任务,按依赖关系切 3 wave:

### Wave 1 (基础) — 顺序执行,因为文件不重叠但需要全部完成后才能 smoke
- **T-04b** · Recall Sticker manifest patch 文件生成(在 tianshu-integrations/patches/,**不直接改 Recall-Sticker 仓**)
- **T-04c** · sidepanel.js patch 文件生成(同上)
- **T-01** · 项目骨架 + pyproject.toml + console_script
- **T-02** · bridge FastAPI + /health endpoint + 测试
- **T-03** · bridge CLI 入口 + vault 校验 + 测试
- **T-04** · Pydantic schemas + 测试

**Wave 1 验收**: `pytest tests/test_server.py tests/test_cli.py tests/test_schemas.py -v` 全过

### Wave 2 (核心 sync 流程)
- **T-05** · POST /sync/recall-sticker endpoint (无 M2.1,直写 .md) + ObsidianWriter + 测试
- **T-05b** · Curator 空骨架 + JSON parser + MockLLMClient + 测试
- **T-06** · 集成 endpoint 调 curator + 测试

**Wave 2 验收**: pytest 全过 + 实际启动 bridge + curl 测试

### Wave 3 (Recall Sticker 端)
- **T-07** · storage-collector.js(patch 文件)
- **T-08** · bridge-client.js + obsidian-exporter.js(patch 文件)

**Wave 3 验收**: JS 语法检查(node -c)+ Recall Sticker 加载测试(用户在 Chrome 验证)

### Phase 3: Cross-Story Regression
- 全量 pytest
- 全量 node 语法检查
- 实际启动 bridge → /health 200
- Recall Sticker patch 应用(用户手动)+ Chrome 重载

## 关键工程决策

1. **不直接修改 Recall-Sticker 仓**:Recall-Sticker 是另一个独立项目,git 仓分离。**生成 patch 文件 `patches/`**,用户手动 apply。
2. **不直接修改 deep-reader 仓**:Week 1 只涉及 Recall Sticker + bridge,Deep Reader 改动在 Week 2 (T-13b / T-17+)。
3. **本 session 内实际 commit 范围**:`~/Developer/tianshu-integrations/` + `patches/`。
4. **End-to-End smoke**: bridge 启动 + curl /health + Recall Sticker patch 应用(用户在另一 session 验证)。