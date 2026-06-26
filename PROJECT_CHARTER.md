# Tianshu Integrations · 项目档案 (Project Charter)

> **代号**:Tianshu Integrations(天枢联动)
> **父项目**:天枢 (`~/Documents/trae_projects/api/`)
> **位置**:`~/Developer/tianshu-integrations/`
> **日期**:2026-06-27
> **状态**:Phase 0/1(PM 调研完成,代码未开始)

---

## 1. 一句话定位

把天枢(Mini-Agent + Deep Reader)与现有两个本地工具(focus-quiz + recall-sticker)打通,形成「网页降噪 → 阅读 → 测验 → 卡片沉淀 → Obsidian 第二大脑」的完整闭环。

## 2. 问题与机会

### 2.1 现有四件套的碎片化

| 项目 | 形态 | 当前能力 | 当前瓶颈 |
|---|---|---|---|
| **Deep Reader** | Chrome MV3 | Mozilla Readability 抽正文 + 苏格拉底 AI 导读 | 没有"读完后做点啥"的延伸 |
| **focus-quiz** | Chrome MV3 | 选区/全文 → LLM 出题 → 错题本 | 没有文章级深度阅读入口,错题数据散落 |
| **recall-sticker** | Chrome MV3 | 选中遮挡防遗忘 + 上下文回锚 + Anki 导出 | 卡片数据只能出 Anki,**无法直接进 Obsidian 第二大脑** |
| **Mini-Agent** | Python CLI + ACP | 本地自动驾驶 + MCP + Skills | **无法直接读取 Chrome storage.local** |
| **Obsidian Vault** | 本地 Markdown | 第二大脑主入口 | 录入纯靠手工,没自动化 |

### 2.2 三个最有价值的联动方向

1. **Deep Reader + focus-quiz**:读完一篇长文 → 直接出 3-5 道测验题 → 答错自动进错题本 → 可导出 Anki
2. **recall-sticker + Mini-Agent**:网页上随手贴的"我想记住"的词 → 主动同步到 Obsidian → M2.1 自动整理(打 tag / 合并 / 双向链接)
3. **跨扩展 chrome.storage 共享**:Deep Reader / focus-quiz / recall-sticker 错题本聚合到一个 `mistake_log_v1` 全局错题中心

### 2.3 为什么是"现在"

- 四个项目都已进入稳定期(最近 commit < 2 个月,无废弃迹象)
- focus-quiz 已实现 Readability + Turndown 抽取(99 行纯函数,可直接 port)
- recall-sticker 已实现 Anki Cloze 格式(可直接复用做 Obsidian 格式)
- Mini-Agent 已实现 M2.1 客户端(可直接借鉴接口)
- 唯一新增基建 = 一个本机 FastAPI 服务(< 100 行)

## 3. 干系人

| 角色 | 关注点 |
|---|---|
| **奕枢**(产品负责人) | 阅读效率、知识沉淀、第二大脑质量 |
| **M2.1**(LLM) | 整理质量、出题质量、响应延迟 |
| **Obsidian Vault** | Markdown 格式兼容性、双向链接、frontmatter 规范 |
| **Anki**(可选导出) | Cloze 格式兼容性、CSV 结构 |

## 4. 成功指标 (Phase 2 验收)

| 指标 | 目标 | 测量方式 |
|---|---|---|
| 联动 1 出题响应延迟 | < 8s(P95) | 用户计时 + Deep Reader console |
| 联动 1 出题质量(用户评分) | ≥ 4.0/5 | 阅读完答题后打分 |
| 联动 1 错题本保留率 | ≥ 90% 一周后回访 | chrome.storage 读出 + 估算 |
| 联动 2 同步成功率 | ≥ 95%(bridge 在线时) | bridge log |
| 联动 2 M2.1 整理质量 | ≥ 80% 卡片被打合理 tag | 人工 spot-check |
| 联动 2 Obsidian 写入成功 | 100%(vault 路径正确时) | Obsidian 实际打开文件 |
| 离线 fallback 触发率 | < 10% session | bridge log + Recall Sticker 状态 |

## 5. 范围与非目标

### In Scope
- 联动 1:Deep Reader + focus-quiz 模式(Readability + 出题 + 错题本 + Anki 导出)
- 联动 2:recall-sticker → bridge → Mini-Agent (curator) → Obsidian
- bridge 服务:本机 FastAPI,手动启动
- 离线 fallback:bridge 不可达时降级为本地 .md 下载
- chrome.storage 命名空间隔离,避免四件套互相覆盖

### Out of Scope (Phase 1)
- 多 vault 并存(Phase 1 只支持单 vault)
- LaunchAgent 开机自启(Phase 1 手动 `tianshu-bridge`)
- 多用户协作 / 云同步
- 跨设备同步
- iOS / Android 客户端
- 实时联机测验(只支持单人离线答题)
- focus-quiz 的 18 个 provider 抽象(只支持 MiniMax M2.1)

## 6. 风险与缓解

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | bridge 进程崩溃 | 中 | Recall Sticker 同步失败 | 自动降级 chrome.downloads |
| R2 | M2.1 返回格式不稳 | 高 | curator 解析失败 | JSON 多层 fallback:严格 parse → 提取 `{...}` → 单字段降级 |
| R3 | Obsidian vault 路径写错 | 中 | 文件写飞 | bridge 启动时校验路径可写,否则退出 1 |
| R4 | chrome.storage 10MB 上限 | 低 | 数据丢失 | 各自 LRU(mistake_log ≤50/source,贴纸按 URL 分桶) |
| R5 | focus-quiz 字段命名冲突 | 中 | 数据互覆盖 | 各自加版本号后缀,Deep Reader 用 `mistake_log_v1` |
| R6 | M2.1 联网不通 | 中 | 全功能降级 | bridge 启动时 ping api.minimaxi.com,失败警告但仍起 |
| R7 | Readability 失败(反爬强站) | 中 | 联动 1 失败 | 多级 fallback:Readability → DOM innerText → 报错 |
| R8 | 用户改 vault 结构 | 低 | frontmatter 不兼容 | curator 严格按现有 vault 规范生成,不动现有文件 |

## 7. 立项依赖

| 依赖 | 状态 | 说明 |
|---|---|---|
| 四个项目源码都在 | ✅ | focus-quiz / recall-sticker / Deep Reader / Mini-Agent 都可读 |
| Obsidian vault 存在 | ✅ | `/Users/mahaoxuan/Desktop/知识库/知识库/` 已确认 |
| MiniMax API key | ❓ | 需用户配置(环境变量 / bridge CLI arg) |
| 用户愿意手动启 bridge | ✅ | 用户已选"手动启服务" |
| 新建独立项目 | ✅ | 用户已确认,放 `~/Developer/tianshu-integrations/` |

## 8. 后续阶段预览

| 阶段 | 周 | 状态 | 主要产出 |
|---|---|---|---|
| Phase 0 观察 | Week 0 | ✅ 完成 | PROJECT_CHARTER(本文档) + 飞书 base + Obsidian 项目页 |
| Phase 1 PM | Week 0 | ✅ 完成 | BRAINSTORM + PRD + ARCHITECTURE + ROADMAP(本次) |
| Phase 2 设计 | Week 1 | 待启动 | 接口详细 spec + 测试用例 + 验收 checklist |
| Phase 3 实现 | Week 1-3 | 待启动 | bridge MVP + Recall Sticker 联动 + Deep Reader 联动 |
| Phase 4 E2E | Week 3-4 | 待启动 | 端到端 demo + 录屏 + 用户验收 |
| Phase 5 QA | Week 4 | 待启动 | 错误路径覆盖 + 离线 fallback 验证 + 性能基线 |
| Phase 6 收尾 | Week 4 | 待启动 | README + 安装文档 + 飞书/Wiki 同步 |

## 9. 引用与双链

- [[Deep Reader Code Wiki|/Users/mahaoxuan/Documents/trae_projects/api/docs/wiki/02-deep-reader.md]]
- [[Mini-Agent Code Wiki|/Users/mahaoxuan/Documents/trae_projects/api/docs/wiki/01-mini-agent.md]]
- [[Recall Sticker 源码|/Users/mahaoxuan/Documents/trae_projects/recall-sticker/]]
- [[focus-quiz 源码|/Users/mahaoxuan/Documents/trae_projects/focus-quiz/]]
- [[Obsidian 项目镜像页|/Users/mahaoxuan/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md]]
- [[Roadmap|/Users/mahaoxuan/Developer/tianshu-integrations/docs/ROADMAP.md]]
- [[Architecture|/Users/mahaoxuan/Developer/tianshu-integrations/docs/ARCHITECTURE.md]]
- [[PRD|/Users/mahaoxuan/Developer/tianshu-integrations/docs/PRD.md]]