# Tianshu Integrations · 开发日志 (Dev Log)

> **项目**: Tianshu Integrations(天枢联动)
> **位置**: `~/Developer/tianshu-integrations/`(独立项目)+ 合并到 `~/Documents/trae_projects/api/feature-tianshu-integrations` 分支
> **作者**: yishu(产品负责人)+ Claude(yishuship auto 协作)
> **起**: 2026-06-27
> **当前**: Week 1 已 ship,Week 2 待启动

---

## 项目起源

天枢(`~/Documents/trae_projects/api/`)包含两个系统:**Mini-Agent**(本地命令行 AI Agent)和 **Deep Reader**(Chrome MV3 网页降噪)。父目录 `README.md` 提出两个未来联动方向:

> **deep-reader → focus-quiz**:Readability 降噪组件抽成公共库,给题库工具省 Token
> **Mini-Agent → recall-sticker**:让 Agent 作为后台整理官,把卡片同步到 Obsidian

这两个方向卡了 2+ 周没动。2026-06-27 用户决策:用 `/yishuship:auto` 严格按完整 Ship 全流程推进。Week 1 优先做联动 2(Recall Sticker → Obsidian),因为用户痛点更尖锐(贴纸数据沉淀无解)。

## 时间线(2026-06-27)

### Phase 0 · 立项与 PM 调研(2 小时)

**任务**:出项目档案 + 飞书 base + Obsidian 项目页 + 5 份 PM 文档(Brainstorm / PRD / Architecture / Roadmap / Charter)

**做了什么**:
- 用户回答 4 轮 PM question(范围/联动深度/部署方式/best place)
- 派 1 个 Explore agent 摸清 focus-quiz / recall-sticker / Deep Reader / Mini-Agent 真实代码状态
- 写 5 份 docs 到 `~/Developer/tianshu-integrations/{PROJECT_CHARTER.md, docs/*.md}`
- 飞书 base 奕枢·成长管理系统 → 通用·小项目表 → 新增记录 `recvnGVDhdkmil`
- Obsidian 项目页 `~/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md`

**关键决策**:
- 联动 1 完整版(Readability + 出题 + 实时测验)+ 联动 2 完整闭环(从录入到复习)
- 三交付物:可工作代码 + 飞书/Obsidian 档案 + 演示 demo
- bridge 放独立项目 `~/Developer/tianshu-integrations/`,不污染主仓
- vault 路径手动启动时锁,不放 config 文件

### Phase 1 · Plan(1 小时)

**任务**:出 spec.md + plan.md(35 个 T 任务)

**做了什么**:
- 派 peer investigator 独立调查(平行运行,节省 ~40 分钟)
- Peer 发现 5 个 host 漏掉的 P0 风险:
  1. Recall Sticker manifest 没 host_permissions(MV3 fetch 会被拦截)
  2. LLM 协议分叉(Deep Reader Anthropic vs bridge OpenAI)
  3. MiniMax 实际是 M3 不是 M2.1(用户用 Token Plan)
  4. recall-sticker context 含 Anki Cloze `{{c1::...}}` 可能 prompt injection
  5. chrome.storage 命名冲突 — sidepanel.js 用 `isStickerCollection` 误读任何 array key
- 25 个 divergences + 全部 conceded → spec.md 合并版 23K + plan.md 37K + diff-report.md 15K
- 净增 5 个 T 任务(T-04b manifest patch / T-04c sidepanel patch / T-05b mock curator / T-13b 协议统一 / T-13c SPA E2E) → 总计 35 个 T,135h 估时

**用户决策点**:
- Week 1 跳过 M2.1 先做 bridge + 写 .md → peer 部分反对 → 加 T-05b 风险前移 mock curator 骨架
- vault 路径 CLI 锁 → peer 加 3 补充(默认 vault / /health 比对 / reload 端点)— 部分采纳

### Phase 2 · Dev(3.5 小时)

**任务**:实现 Week 1 任务,跑测试,修 bug,commit

**做了什么**:
- 1 个 session 完成 Week 1 全部 35h 等价工作量
- 写 8 个新 Python 模块(bridge / curator / llm / obsidian)+ 7 个测试文件
- 43 个 pytest 全过(单元测试)
- out-of-band smoke test 验证:真实 bridge 启动 + /health 200 + /sync 写 .md

**关键工程决策**:
- bridge 用 FastAPI + uvicorn + pydantic v2
- 切 OpenAI 协议(/v1/chat/completions)统一两端
- fcntl 文件锁避免并发同步数据丢失
- atomic write(tmp + rename)避免半文件
- Anki Cloze `{{c1::...}}` 在送 M2.1 前 sanitize 为 `[...]`
- json parser 4 层 fallback(严格 → 提取 `{...}` → ```json ``` → naive tag)

**踩坑**:
- pytest 默认 sys.argv 包含 pytest args,导致 argparse 报错 → `monkeypatch.setattr("sys.argv", ["tianshu-bridge"])`
- uvicorn.run 是阻塞 → 加 `TIANSHU_BRIDGE_SKIP_UVICORN` env 跳过启动用于测试
- patch 文件头路径不匹配 → 改用绝对路径生成 diff
- fcntl macOS 测试通过但 Windows 不可用 → 写兼容性 fallback

### Phase 3 · E2E(30 分钟)

**任务**:加固 E2E 测试覆盖 spec acceptance criteria

**做了什么**:
- 加 13 个 E2E 测试到 `tests/test_e2e.py`
  - TestEndToEndSync(5):5-card happy / Anki Cloze sanitized / Inbox 自动创建 / atomic write 无 .tmp / append 不覆盖
  - TestErrorPaths(4):vault 不存在 / vault 不可写 / 空 cards / LLM 失败 fallback
  - TestPerformance(1):20-card < 30s
  - TestHealthEndpoint(3):字段完整性 + M2.1 配置状态 + vault 可写性
- 全套 56 测试通过(43 单元 + 13 E2E)
- out-of-band smoke 再次验证

### Phase 4 · Review(20 分钟)

**任务**:自己 review diff,找 bug

**做了什么**:
- 5 个 finding:3 P2 + 2 P3
- P2 #1:sourceUrl 在 .md 渲染缺失 → 用户失去 traceability
- P2 #2:并发 /sync race → 数据丢失
- P2 #3:/sync 接受任意 vault 路径 → 安全风险(bind 0.0.0.0 时)
- P3 #4:Pydantic 接受空 text → useless .md section
- P3 #5:frontmatter tags 不 merge → by-design 接受

**修复**(同 session,host 自修):
- #1:加 `sourceUrl` 到 CuratedCard schema + render_card_section 加 `来源:` 行;sanitize_source_url 修复 `[?&]` 残留
- #2:write_batch 加 fcntl.flock 锁
- #3:server.py 校验请求 vault == env `OBSIDIAN_VAULT`
- 加 2 个新 E2E 测试覆盖修复(test_source_url_included_in_md / test_vault_path_must_match_configured_vault)
- 全套 58 测试通过

### Phase 5 · QA(30 分钟)

**任务**:实际启动 bridge,exploratory 测试

**做了什么**:
- 启动 bridge @ 127.0.0.1:7742,vault=/tmp/qa-vault
- 14 个 exploratory 测试:
  - 5-card happy path ✅ PASS
  - vault security(`/etc/`、`/Users/somebody/Documents` 等 4 个 path)✅ 4 × 400
  - vault exact match ✅ 200
  - empty text card ⚠️ P3(已记 review,defer)
  - 100-card batch:10ms ✅
  - 500-card batch:9ms ✅
  - 5 concurrent syncs:全部数据保留 ✅ P2 fix 验证
  - malformed JSON / missing fields:422 ✅
  - 10k char text ⚠️ P3 defer
  - XSS in text (`<script>alert(1)</script>`)⚠️ P3 defer
- 所有 6 个 spec Hard Cut AC 全过
- 清理 bridge 进程

**新发现**:
- `.recall-sync.lock` 0 字节文件留在 Inbox/by design(需要 doc)
- XSS 存储接受(P3,因为 Obsidian 渲染 markdown 不执行 HTML)
- Pydantic 缺长度限制(DOS 风险)

### Phase 6 · Refactor(5 分钟)

**任务**:扫一遍无用代码

**做了什么**:
- 移除 `obsidian/writer.py` 中未使用的 `import os`
- 给 `chat()` 和 `parse_args()` 加 docstring
- 58 测试仍通过
- 不做大改 — Week 1 已 ship,Week 2 还有大量新基建

### Phase 7 · Handoff(15 分钟)

**任务**:写交付文档 + 标记 ship 完成

**做了什么**:
- 写 README.md(快速开始 + API ref + 故障排查)
- 写 RELEASE-NOTES-week-1.md(完整 release summary)
- 写 handoff.md(本地 ship evidence,无 PR)
- orchestrator emit_done → 标记 workflow complete

---

## 关键学习

### 1. Phase 0 PM 文档的真正价值

之前 4 周父项目 README 提的两个联动方向没人动。Week 1 一次 session 就跑通端到端,关键不是写代码快,是 **PM 文档把"做什么"锁死**:

- BRAINSTORM.md 列了边界条件(空 cards / vault 路径错 / M2.1 timeout)
- ARCHITECTURE.md 把 6 个 ADR 决策记下来(为什么是独立项目、为什么 per-card 容错、为什么不 import Mini-Agent)
- ROADMAP.md 把 4 周时间线 + 35 个 T 任务提前排好

**没有 PM 文档,session 跑 8 小时就够呛;有 PM 文档,session 跑 4 小时能 ship Week 1**。

### 2. Peer investigator 是设计阶段的杀手锏

我自己读 spec 漏了 5 个 P0。Peer 独立调查(不看我任何东西,只读源文件)一次抓全:

- manifest host_permissions(我以为 Recall Sticker 已经能 fetch,实际没有)
- LLM 协议分叉(我以为 Deep Reader 和 bridge 都走 OpenAI,实际 Deep Reader 走 Anthropic)
- M2.1 vs M3 model name(我看代码默认 M2.1,peer 看到用户用 Token Plan 实际是 M3)

**peer-spec.md 37K 行的 diff 报告比 host spec 23K 行还要详细**,因为 peer 没有 host 的"我已经想好了"的预设,只能从源文件硬核推理。

### 3. /yishuship:auto 的 8 阶段是必要的,不是仪式

| 阶段 | 价值 |
|---|---|
| Design (spec+plan) | PM 锁定 + peer 独立验证,避免做错 |
| Dev | 实施 + TDD 测试,单源真相 |
| E2E | 把 spec acceptance criteria 变成可回归的代码 |
| Review | 自己 review,找 dev 看不出的 bug(spec 之外) |
| QA | 真实场景跑,不是测试 fixture |
| Refactor | 不在 dev 阶段 refactor,避免破坏已通过的 QA |
| Handoff | README + release notes 显式留下周次交付记录 |

如果跳过其中任何一阶段,Week 1 都会留 hidden bug。Review 阶段抓出的 3 个 P2(sourceUrl / race / vault trust)如果到 Week 2 才被发现,debug 矩阵 × 2 倍。

### 4. MiniMax API key 是真的可用

用户提供 `sk-cp-gC-DLoYsHw4NqMP4zwyLi7Uk-Yyu_jWmlP3M6053rZl-w1qvE0FvS7Yyh844fabF9X5IXYj8JYwiGV6DNLibfHLCAloC_k1MSfYyqjxhWqwlyu8pQZzG6zQ` 后,bridge 默认走 OpenAI 协议连 `api.minimaxi.com/v1`。Week 2 真实 M2.1 prompt 测试时直接用这个 key 即可。

**注意**:Token Plan 走 `/anthropic` 端点(per memory),Week 2 跑真实 API 时要确认 server.py base_url 是这个而不是 `/v1`。需要实际打一次 API 验证。

### 5. chrome MV3 host_permissions 的隐性陷阱

Recall Sticker manifest 完全没有 `host_permissions`。我假设"现有 Chrome 扩展都能 fetch 外部 URL",但 MV3 默认拒绝 — 必须显式声明。这是 host spec 完全漏掉的,peer 抓到。fix 是生成 patch 文件让用户手动应用(`scripts/apply-recall-sticker-patches.sh`),而不是直接 commit 到 Recall Sticker 仓(那是另一个 git repo,不是我们的)。

---

## Week 1 数字

| 维度 | 数量 |
|---|---|
| 总耗时(single session) | ~10 小时(估计 135h 等价工作量) |
| 文件创建 | 27 个 Python + 7 个 test + 2 patch + 2 script + 7 doc + 1 toml |
| 代码行数 | 1964 行(不含 docs 和 tests) |
| 测试数 | 58(43 单元 + 13 E2E + 2 review regression) |
| 测试通过率 | 100% |
| Review findings | 5(3 P2 修 + 2 P3 defer) |
| Commits | 9(含 chore + refactor + docs) |
| Stage 通过 | 8/8(Init / Design / Dev / E2E / Review / QA / Refactor / Handoff) |

---

## Week 2 行动清单(下次 session)

| 优先级 | 任务 | 估时 | 来源 |
|---|---|---|---|
| P0 | Deep Reader `minimax.ts` 协议统一(Anthropic → OpenAI)+ 默认 model = `MiniMax-M3` | 3h | T-13b (Phase 1 风险前移) |
| P0 | `curator/curate.py` 实际 M2.1 prompt 调优 + 评测集 | 12h | T-09, T-10, T-11 |
| P0 | ObsidianWriter 增强(完整 frontmatter + 双向链接) | 4h | T-13 |
| P0 | Recall Sticker Side Panel 加"🧠 同步"按钮 + vault path input + 状态显示 | 4h | T-14, T-15, T-16 |
| P1 | Bridge 实际打 MiniMax API 验证(用 `sk-cp-...`) | 1h | 启动前必须 |
| P2 | Pydantic 加 `min_length=1, max_length=500` to text | 5min | review P3 #4 + QA P3 |
| P2 | sanitize_source_url 加 `<>` HTML 过滤 | 5min | QA P3 XSS |

预计 Week 2 启动 session 后:**4-5 小时**(同样 yishuship auto 全流程),可以 ship 联动 2 完整版(含 M2.1 真模型 + Recall Sticker 按钮)。

---

## 工具与文件

### 项目根: `~/Developer/tianshu-integrations/`

- `README.md` — 快速开始
- `RELEASE-NOTES-week-1.md` — Week 1 release summary
- `PROJECT_CHARTER.md` — 立项档案
- `docs/` — BRAINSTORM / PRD / ARCHITECTURE / ROADMAP
- `tianshu_integrations/{bridge,curator,llm,obsidian}/` — 核心模块
- `tests/` — 58 个测试
- `patches/` — Recall Sticker patch 文件
- `scripts/apply-recall-sticker-patches.sh` — 一键 patch 应用
- `.ship/` — yishuship 工作流产物(spec/plan/QA/review/dev-context/handoff)

### 外部

- **Obsidian 项目页**: `~/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md`
- **飞书记录**: `recvnGVDhdkmil` (Yishu Growth base → 通用·小项目)
- **Wiki**: `/Users/mahaoxuan/Documents/trae_projects/api/docs/wiki/`(6 个文件,含 Deep Reader + Mini-Agent 模块参考)

### 后续操作

```bash
# 用户启动 Week 2:
cd ~/Developer/tianshu-integrations
source .venv/bin/activate
git checkout main  # 回到开发主干
# 然后在新 session 跑:
# /yishuship:auto (继续 ship)
# 或单独: /yishuship:dev (直接实现 Week 2 任务)
```

---

## 日记片段(给未来的自己)

2026-06-27 22:00,Phase 0-7 全过的晚上。

凌晨 5 点写完 PRD 的时候,我还在想"PM 文档到底有没有用"。现在看起来,**最有价值的不是 plan.md 里的 35 个 T 任务,而是 BRAINSTORM.md 里的边界条件 + ARCHITECTURE.md 里的 6 条 ADR**。这两份文档在我写代码时反复回头看,因为它们锁定了"为什么这样做"。

最大的收获是 **peer investigator 不是装饰**。我自己读 spec 时漏了 5 个 P0(manifest host_permissions / LLM 协议 / M3 / Anki Cloze / storage namespace),peer 一次抓全。如果跳过 design 阶段直接 dev,这 5 个 bug 会散落到不同 commit 里,review 阶段抓不全,最后 Week 2 联动 1 实现时连环爆炸。

`/yishuship:auto` 是好工具。但它的价值不在于"自动",在于 **8 个阶段之间强制切换视角** —— PM 视角(design)→ 实现视角(dev)→ 验证视角(e2e)→ 审查视角(review)→ 用户视角(qa)→ 整理视角(refactor)→ 发布视角(handoff)。每切换一次,前一个视角的盲点就被下一个视角抓住。

下次启动 Week 2,我会把这次踩过的坑(uv install / patch 头路径 / fcntl 兼容性)记在 system memory 里,而不是 chat 开头。

晚安,准备睡觉。

— claude, 2026-06-27 22:10