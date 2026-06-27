# Tianshu Integrations · 端到端 Demo 录屏脚本

> **date**: 2026-06-28
> **scope**: Week 2-4 端到端流程演示
> **method**: 文字脚本 + 实测输出(本机无 OBS / QuickTime,文字描述代替真录屏)
> **complement**: 真录屏建议用 OBS(免费、跨平台、含窗口捕获)或 macOS QuickTime Player(原生 Screen Recording)

---

## 场景 1:用户创建 Recall Sticker 贴纸

**操作步骤**:
1. 打开 Chrome,浏览 https://example.com/ebpf
2. 用鼠标选中一段 1-2 句话的文本
3. Recall Sticker 浮动工具栏出现在选区上方
4. 点 "📌 添加贴纸" → 贴纸存到 chrome.storage.local,key = `https://example.com`
5. 点 Chrome 工具栏 Recall Sticker 图标 → Side Panel 打开
6. 看到刚创建的贴纸在列表里

**截图位置**:
- 选中文本后:浏览器右上方 Recall Sticker 浮动工具栏
- Side Panel: 贴纸列表 + 顶部 stats bar(显示 "1 stickers collected")

---

## 场景 2:用户配置 vault path + 同步

**前置**:用户已经创建 ≥1 个贴纸

**操作步骤**:
1. Side Panel 顶部 `#vault-path-input` 输入 `~/Desktop/知识库/知识库`(或自定义 vault 路径)
2. Chrome 自动保存到 chrome.storage.local(下次打开 Side Panel 自动恢复)
3. 点 "🧠 同步到 Obsidian" 按钮
4. Side Panel 状态显示:
   - "⏳ 正在同步..."(蓝色,3-30s)
   - "✅ 已同步 3 张卡片"(绿色)  /  "📥 已下载 recall-stickers-2026-06-28.md"(橙色,bridge 挂)
5. Obsidian vault/Inbox/2026-06-28-recall.md 自动出现

**截图位置**:
- Side Panel 顶部 input + 按钮 + 状态显示
- Obsidian 打开 vault/Inbox/2026-06-28-recall.md

---

## 场景 3:Obsidian .md 文件内容

**输出文件**:`vault/Inbox/2026-06-28-recall.md`

**结构**:
```markdown
---
date: 2026-06-28
tags: [cloud-platform, devops, kernel, networking, observability, recall-sticker, sidecar-pattern, 容器编排, 微服务]
source: recall-sticker-sidepanel
---

# Recall Sticker · 2026-06-28

## eBPF

kernel tech

相关: [[02 Wiki/linux-kernel]]

来源: https://example.com/ebpf


---

## Kubernetes

container orchestration

相关: [[02 Wiki/linux-kernel]]

来源: https://example.com/k8s
```

**关键字段**:
- Frontmatter: `date`, `tags`(union of all batch tags + "recall-sticker" meta), `source`
- 每张卡: `## title`, body, `相关: [[wiki-links]]`(Phase B 建议), `来源: <URL>`(Week 2 加的 traceability)
- Phase A: batch_tags 全出现在 frontmatter
- Phase B: 扫描 vault 已有的 .md 文件,建议 wiki 链接

---

## 场景 4:bridge 进程挂了的离线 fallback

**前置**:Recall Sticker Side Panel 已经配置 vault path

**操作步骤**:
1. 在终端 kill `tianshu-bridge` 进程
2. Recall Sticker Side Panel 点"🧠 同步到 Obsidian"
3. 状态显示:"📥 bridge 不可达,已下载 recall-stickers-2026-06-28.md,请手动拖入 Obsidian"
4. Chrome 弹出下载 dialog,文件名:`recall-stickers-2026-06-28.md`
5. 用户手动把下载的 .md 拖进 Obsidian vault/Inbox/

**Observed behavior**:Week 1-2 实现的 offline fallback,Recall Sticker 端 lib/bridge-client.js 用 chrome.downloads.download + Blob URL(MV3 兼容)

---

## 场景 5:Deep Reader 出题(Week 3)

**前置**:Deep Reader 装好 + Week 3 协议统一 patch 应用

**操作步骤**:
1. 在 Chrome 打开 https://example.com/ebpf-article(长文)
2. 按 `Alt+D` 触发 Deep Reader
3. 阅读面板弹出,纯净正文 + 进度条
4. 侧栏点击 "📝 开始测验" 按钮
5. Side Panel 状态:"出题中..."(蓝色,5-10s,Week 3 fix 后 ~5s)
6. QuizPanel Shadow DOM 渲染,显示题目 1/3 + 4 个选项
7. 用户点选项 → 立即显示 ✓/✗ + 解释
8. 重复 3 道题 → 显示"🎉 测验完成"
9. 点 "导出 Anki CSV" → 浏览器下载 mistakes-{timestamp}.csv
10. 答错的卡片在 chrome.storage.local.mistake_log_v1 自动保存(LRU 50/source)

**截图位置**:
- Deep Reader 阅读面板 + 进度条
- 侧栏"📝 阅读测验" section
- QuizPanel 答题过程(Shadow DOM 内)
- Anki CSV 下载 dialog

---

## 场景 6:错误路径(Week 4 覆盖)

### 6.1 M2.1 返回 truncated JSON

**Mock**:MiniMax 返回 `{"tags": ["a", "b"], "rewrites": [{"cardId":`(无闭合)
**预期**:parser 走 Layer 5,恢复 `["a", "b"]` tags

### 6.2 30 张卡片 → chrome.storage 接近 10MB

**Mock**:连续 sync 30 次,每次 1 张 ~200KB 错题
**预期**:MistakeStore LRU 强制清理,只保留最新 50 条

### 6.3 vault 路径 = /etc

**Mock**:Recall Sticker 端 vaultPath = "/etc"
**预期**:bridge 返回 400 "vault path /etc is not the configured OBSIDIAN_VAULT"

---

## 测试矩阵(Week 4 T-27 覆盖)

| 错误源 | 期望行为 | 验证 |
|---|---|---|
| bridge 没起 | Recall Sticker 降级 chrome.downloads | ✅ E2E 测过 |
| M2.1 timeout | 整批取消,errors[] 返回 | pytest 模拟 |
| vault 路径不存在 | 400 + 明确错误信息 | pytest E3 |
| vault 路径不可写 | 400 + 明确错误信息 | pytest E4 |
| vault = /etc | 400 + 安全拒绝 | pytest E5 |
| bridge 503 | 客户端降级 offline | pytest E6 |
| M2.1 非 JSON | curator 走 4-layer fallback | pytest E7 |
| M2.1 truncated | parser 恢复 tags | pytest E8 |
| Readability 失败 | ContentExtractorV2 走 dom-innertext | pytest E9 |
| chrome.storage 满 | LRU 强制清理 | pytest E10 |
| Anki Cloze 注入 | sanitize `{{c1::}}` | pytest E11 |
| M2.1 thinking | extractContent 剥离 ` ̶t̶h̶i̶n̶k̶...̶ ̶` | pytest E12 |

---

## 真录屏建议(Week 5 或用户手动)

如果用户想要真视频录屏:

### 工具

- **macOS 原生**:QuickTime Player → File → New Screen Recording
- **跨平台开源**:OBS Studio(https://obsproject.com/)
- **CLI-only**:ffmpeg + x11grab(Linux) / avfoundation(macOS)

### 建议场景顺序

1. Recall Sticker 装好 → 创建 3 张贴纸
2. Side Panel 配置 vault → 同步 → 等 5-10s
3. 打开 Obsidian → 看新 .md
4. 打开 Deep Reader 装好 → Alt+D 打开 → 出题 → 答 → 导出
5. 离线场景:kill bridge → 同步 → 下载 .md

### 帧率建议

- 24fps(电影感)— 适合 demo
- 60fps(流畅)— 适合技术展示

### 后期制作

- 加字幕(中文),每段画面加关键步骤注释
- 加 logo + 章节标题(chapter markers)
- 输出 mp4(2024 年 macOS Chrome 视频通常 h264 + aac)
- 文件大小建议 < 50MB(YouTube 限制是 128GB 但小文件传得快)