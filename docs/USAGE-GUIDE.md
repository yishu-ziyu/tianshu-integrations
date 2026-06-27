# Tianshu Integrations · 完整使用指南

> **适用版本**: Week 1-4 全部 ship
> **更新日期**: 2026-06-28
> **GitHub**: https://github.com/yishu-ziyu/tianshu-integrations

---

## 目录

1. [这个系统是干什么的](#1-这个系统是干什么的)
2. [你需要准备什么](#2-你需要准备什么)
3. [安装(一次性,约 15 分钟)](#3-安装一次性约-15-分钟)
4. [日常使用 · 联动 2:贴纸 → Obsidian](#4-日常使用--联动-2贴纸--obsidian)
5. [日常使用 · 联动 1:读完文章 → 测验](#5-日常使用--联动-1读完文章--测验)
6. [离线模式(bridge 没启动时)](#6-离线模式bridge-没启动时)
7. [导出错题到 Anki](#7-导出错题到-anki)
8. [故障排查](#8-故障排查)
9. [日常开关机流程](#9-日常开关机流程)
10. [进阶:自定义配置](#10-进阶自定义配置)

---

## 1. 这个系统是干什么的

Tianshu Integrations 把你日常用的 4 个工具连成一条线:

```
浏览网页 → 贴"我要记住"的贴纸 → 自动整理进 Obsidian
浏览网页 → 读完长文 → AI 出 3 道测验题 → 答错自动进错题本 → 导出 Anki
```

### 两个联动

| 联动 | 触发 | 流程 | 产出 |
|------|------|------|------|
| **联动 2**(贴纸沉淀) | Recall Sticker Side Panel 点"🧠 同步到 Obsidian" | 贴纸 → bridge → M2.1 打 tag + 合并 + 双向链接 → 写 .md | Obsidian Inbox/ 出现结构化笔记 |
| **联动 1**(读完即测) | Deep Reader 阅读面板点"📝 开始测验" | 文章 → M2.1 出 3 道题 → 答题 → 错题存 chrome.storage → 导出 Anki CSV | Anki 可导入的错题卡 |

### 核心概念

- **bridge**:你电脑上跑的一个小程序(Python),监听 127.0.0.1:7733,接收 Chrome 扩展的请求,调 MiniMax M2.1,写文件到 Obsidian vault
- **M2.1/M3**:MiniMax 的大语言模型,负责"智能整理"(打 tag、出题、建议双向链接)
- **vault**:你的 Obsidian 知识库文件夹,默认 `~/Desktop/知识库/知识库/`

---

## 2. 你需要准备什么

| 工具 | 说明 | 你有了吗? |
|------|------|----------|
| **Mac 电脑** | 本系统只在 Mac 上跑 | ✅ |
| **Chrome 浏览器** | 装两个扩展(Recall Sticker + Deep Reader) | ✅ |
| **Obsidian**(可选) | 看 vault 里的 .md 文件。不装也能用,只是看文件不方便 | ✅ |
| **MiniMax API Key** | 从 platform.minimaxi.com 获取的 `sk-cp-...` key | ✅(已提供) |
| **Python 3.10+** | bridge 服务用 | ✅ |
| **Node.js 18+** | Deep Reader 构建用(一次性) | ✅ |

---

## 3. 安装(一次性,约 15 分钟)

### 3.1 下载项目代码

```bash
cd ~/Developer
git clone https://github.com/yishu-ziyu/tianshu-integrations.git
cd tianshu-integrations
```

### 3.2 安装 bridge 服务

```bash
# 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv pip install -e ".[dev]"

# 验证安装
tianshu-bridge --help
```

看到帮助信息 = 安装成功。

### 3.3 配置 API Key

```bash
# 把这行加到 ~/.zshrc 里(持久化)
export MINIMAX_API_KEY="sk-cp-gC-DLoYsHw4NqMP4zwyLi7Uk-Yyu_jWmlP3M6053rZl-w1qvE0FvS7Yyh844fabF9X5IXYj8JYwiGV6DNLibfHLCAloC_k1MSfYyqjxhWqwlyu8pQZzG6zQ"

# 让配置立即生效
source ~/.zshrc
```

### 3.4 应用 Recall Sticker 补丁

Recall Sticker 扩展需要 2 个补丁才能跟 bridge 通信:

```bash
# Week 1 补丁(加网络权限 + 防数据串扰)
bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-patches.sh

# Week 2 补丁(加"同步到 Obsidian"按钮 + 3 个 lib 文件)
bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-week2-patches.sh
```

两个脚本都是**幂等的** — 重复运行会自动跳过已应用的部分。

### 3.5 Chrome 加载扩展

1. 打开 `chrome://extensions`
2. 右上角开启**"开发者模式"**
3. 点**"加载已解压的扩展程序"**

**加载 Recall Sticker**:
- 选择文件夹:`~/Documents/trae_projects/recall-sticker/Recall-Sticker/`

**加载 Deep Reader**(联动 1 需要):
- 先构建:`cd ~/Documents/trae_projects/api/deep-reader && npm install && npm run build`
- 选择文件夹:`~/Documents/trae_projects/api/deep-reader/dist/`

4. 两个扩展都加载后,Chrome 工具栏出现两个图标

### 3.6 验证安装

```bash
# 启动 bridge
source ~/Developer/tianshu-integrations/.venv/bin/activate
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

另开一个终端:
```bash
curl http://127.0.0.1:7733/health | python3 -m json.tool
```

看到这个 = 安装成功:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "vaultWritable": true,
  "minimaxConfigured": true,
  "currentVault": "/Users/mahaoxuan/Desktop/知识库",
  "uptimeSec": 5
}
```

按 `Ctrl+C` 关掉 bridge(后面再讲日常怎么启动)。

---

## 4. 日常使用 · 联动 2:贴纸 → Obsidian

### 场景:你在读一篇 K8s 文档,想把关键术语存进 Obsidian

#### 第 1 步:启动 bridge

每次用之前,先在终端启动 bridge:

```bash
source ~/Developer/tianshu-integrations/.venv/bin/activate
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

看到 `Uvicorn running on http://127.0.0.1:7733` = 启动成功。**这个终端不要关**(可以最小化)。

#### 第 2 步:在网页上创建贴纸

1. Chrome 打开你要读的网页(比如 https://kubernetes.io/docs/concepts/)
2. 用鼠标选中一段文字(比如 "Pod 是 Kubernetes 中最小的可部署计算单元")
3. Recall Sticker 浮动工具栏出现在选区上方
4. 点 **"📌 添加贴纸"** → 贴纸存到 chrome.storage

重复 2-4 步,创建多张贴纸。

#### 第 3 步:打开 Side Panel

1. 点 Chrome 工具栏的 **Recall Sticker 图标**
2. Side Panel 打开,看到:
   - 顶部:贴纸数量统计
   - **🧠 同步到 Obsidian** 按钮 + vault 路径输入框
   - 中间:贴纸列表
   - 底部:搜索 + 标签管理

#### 第 4 步:配置 vault 路径(第一次用需要)

1. 在 Side Panel 顶部的输入框里填:`~/Desktop/知识库/知识库`
2. 路径会自动保存到 chrome.storage,下次打开不用重填

#### 第 5 步:点"🧠 同步到 Obsidian"

1. 点按钮
2. 状态显示:**"⏳ 正在同步..."**(蓝色,等待 5-30 秒)
3. bridge 接收卡片 → 调 M2.1:
   - **Phase A**(批量):M2.1 给所有卡片打 tag + 标记可合并的
   - **Phase B**(逐张):M2.1 扫描 vault 已有笔记,建议双向链接
4. 状态变成:**"✅ 已同步 N 张卡片"**(绿色)

#### 第 6 步:在 Obsidian 查看结果

打开 Obsidian → 导航到 `Inbox/` 文件夹 → 看到 `2026-06-28-recall.md`

文件内容长这样:

```markdown
---
date: 2026-06-28
tags: [container-orchestration, kubernetes, pod, recall-sticker, 微服务]
source: recall-sticker-sidepanel
---

# Recall Sticker · 2026-06-28

## Pod

Kubernetes 中最小的可部署计算单元

相关: [[02 Wiki/kubernetes-basics]]

来源: https://kubernetes.io/docs/concepts/

---

## Service

...
```

**关键:**
- **frontmatter** 里的 tags 是 M2.1 自动打的(英文 + 中文混合)
- **相关: [[...]]** 是 M2.1 根据 vault 已有笔记建议的双向链接
- **来源: URL** 保留原始网页链接,方便回溯
- 如果同一天同步多次,新卡片会**追加**到同一个文件(不覆盖)
- 如果同一天同步多次,frontmatter 的 tags 会**合并**(不替换)

---

## 5. 日常使用 · 联动 1:读完文章 → 测验

### 场景:你读完一篇 eBPF 技术博客,想确认自己真的读懂了

#### 第 1 步:启动 bridge(如果已经启动了,跳过)

```bash
source ~/Developer/tianshu-integrations/.venv/bin/activate
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

#### 第 2 步:打开文章 + 触发 Deep Reader

1. Chrome 打开你要读的长文(比如 https://ebpf.io/what-is-ebpf/)
2. 按键盘 **`Alt+D`**(Mac 上是 `Option+D`)
3. Deep Reader 阅读面板弹出:
   - 正文被 Mozilla Readability 净化(去掉广告/导航/侧栏)
   - 顶部:标题 + 作者 + 阅读时长 + 字数
   - 右侧边栏:3 个 section(📝 阅读测验 / 阅读引导 / AI 助手)

#### 第 3 步:点"📝 开始测验"

1. 在右侧边栏找到 **"📝 阅读测验"** section
2. 点 **"📝 开始测验"** 按钮
3. 按钮文字变成 **"出题中..."**(等待 5-10 秒,M2.1 在出题)

#### 第 4 步:答题

3 道题依次出现,每道题包含:

```
题目 1/3
[概念边界]

Q: eBPF 程序能直接修改内核源码吗?

  ○ A. 是的,需要 root 权限
  ○ B. 否,通过 verifier 保证安全
  ○ C. 是的,在加载时
  ○ D. 否,完全不能
```

1. 点你认为是正确的选项
2. 立即显示反馈:
   - ✓ 正确 → 绿色高亮你选的选项
   - ✗ 错误 → 红色高亮你选的,绿色高亮正确答案
3. 显示 **explanation**(M2.1 给的解释)
4. 点 **"下一题"**

3 道题分别覆盖:
- **trap**(概念边界):测试你是否混淆了相似概念
- **counterfactual**(因果反事实):测试"如果 X 相反会怎样"
- **transfer**(场景迁移):测试"X 在 Y 领域怎么应用"

#### 第 5 步:查看结果

答完 3 道题后:

```
🎉 测验完成!
2 / 3 正确

[导出 Anki CSV]
```

**答错的题会自动存到** `chrome.storage.local.mistake_log_v1`,不会丢。

---

## 6. 离线模式(bridge 没启动时)

### 联动 2 的离线 fallback

如果你忘了启动 bridge,或者 bridge 崩了:

1. 你在 Recall Sticker Side Panel 点"🧠 同步到 Obsidian"
2. bridge-client.js 检测到 bridge 不可达
3. 状态显示:**"📥 bridge 不可达,已下载 recall-stickers-2026-06-28.md,请手动拖入 Obsidian"**
4. Chrome 弹出下载对话框,文件名 `recall-stickers-2026-06-28.md`
5. 你手动把这个 .md 文件拖进 Obsidian vault 的 `Inbox/` 文件夹

**离线模式跟在线模式的区别**:
- 离线:没有 M2.1 打 tag、没有双向链接建议,只是原始贴纸转 .md
- 在线:有 M2.1 智能整理(tag + 合并 + 双向链接)

### 联动 1 没有离线模式

Deep Reader 出题**必须**有 bridge(因为出题要调 M2.1)。bridge 没启动时,点"📝 开始测验"会显示错误。

---

## 7. 导出错题到 Anki

### 场景:你一周答了 20 道题,想把错题导入 Anki 复习

#### 第 1 步:在 QuizPanel 里导出

1. 在 Deep Reader 阅读面板,打开 Side Panel 的"📝 阅读测验" section
2. 如果有之前的测验结果,会显示"导出 Anki CSV"按钮
3. 点按钮 → 浏览器下载 `mistakes-{timestamp}.csv`

#### 第 2 步:导入 Anki

1. 打开 Anki 桌面版
2. 文件 → 导入
3. 选择下载的 .csv 文件
4. 字段映射:
   - Front → Front(正面)
   - Back → Back(背面)
   - Source → Source(来源)
   - Evidence → Evidence(证据)
   - Tags → Tags(标签)
5. 点"导入"

#### CSV 格式

```csv
Front,Back,Source,Evidence,Tags
"eBPF 程序能直接修改内核源码吗?","正确答案：否,通过 verifier 保证安全；我的选择：是的,需要 root 权限；思维断裂点：eBPF 通过 in-kernel verifier 保证安全,不修改内核源码。","eBPF intro https://ebpf.io/what-is-ebpf/","verified by the in-kernel verifier | p1","deep-reader"
```

每行一道错题,包含:题目、正确答案 + 你的选择 + 解释、来源、原文证据、标签。

---

## 8. 故障排查

### bridge 相关

| 症状 | 原因 | 解决 |
|------|------|------|
| `tianshu-bridge: command not found` | venv 没激活 | `source ~/Developer/tianshu-integrations/.venv/bin/activate` |
| `minimaxConfigured: false` | API key 没设 | `export MINIMAX_API_KEY="sk-cp-..."` |
| `vaultWritable: false` | vault 路径不可写 | `chmod 755 ~/Desktop/知识库/知识库` |
| bridge 启动报错 "vault 路径不存在" | 路径打错了 | 检查 `--vault` 参数,路径必须存在 |
| `/sync` 返回 400 "not the configured" | 请求里的 vault 跟启动时的不一致 | 两边用同一个路径 |
| bridge 端口被占 | 7733 被别的程序用了 | `tianshu-bridge --port 7734 --vault ...` 换端口 |

### Recall Sticker 相关

| 症状 | 原因 | 解决 |
|------|------|------|
| 点"同步"没反应 | manifest 补丁没应用 | 重跑 `apply-recall-sticker-patches.sh` + `apply-recall-sticker-week2-patches.sh` |
| "collectAndSync is not a function" | sidepanel.js 版本旧 | 重跑 week2 补丁 + Chrome 重载扩展 |
| Side Panel 没显示"🧠 同步"按钮 | Week 2 补丁没应用 | 重跑 `apply-recall-sticker-week2-patches.sh` + Chrome 重载 |
| 同步后 Obsidian 没出现文件 | vault 路径不对 | 检查 Side Panel 输入框的路径跟 bridge 启动参数一致 |
| fetch 报 `ERR_BLOCKED_BY_CLIENT` | manifest 没 host_permissions | 重跑 Week 1 补丁 |

### Deep Reader 相关

| 症状 | 原因 | 解决 |
|------|------|------|
| `Alt+D` 没反应 | Deep Reader 扩展没加载 | chrome://extensions 检查是否启用 |
| 阅读面板没弹出 | content script 没注入 | 刷新网页 + 重试 |
| 点"开始测验"一直转圈 | M2.1 响应慢 | 等 10-15 秒,或检查 bridge 是否在运行 |
| 出题返回空 | 文章太短(< 100 字) | 换一篇更长的文章 |
| QuizPanel 显示"出题失败" | M2.1 返回非 JSON | 重试一次,parser 有 4 层 fallback |
| AI 助手不工作 | Week 3 协议改动 | 确认 Deep Reader dist/ 是最新 build |

### Obsidian 相关

| 症状 | 原因 | 解决 |
|------|------|------|
| Inbox 文件夹不存在 | bridge 第一次写入时自动创建 | 手动 `mkdir -p ~/Desktop/知识库/知识库/Inbox` |
| 双向链接 `[[...]]` 是红色 | 目标笔记不存在 | 正常 — M2.1 建议的链接可能指向还没创建的笔记 |
| frontmatter tags 没更新 | Week 1 bug(已修) | 确认 bridge 是 Week 2+ 版本(frontmatter merge on append) |

---

## 9. 日常开关机流程

### 每次开始用

```bash
# 1. 启动 bridge(开一个终端,跑完不关)
source ~/Developer/tianshu-integrations/.venv/bin/activate
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

### 用的时候

1. Chrome 里正常浏览网页
2. 想存贴纸 → 选中文字 → Recall Sticker → Side Panel → "🧠 同步到 Obsidian"
3. 想做测验 → 打开长文 → `Alt+D` → "📝 开始测验"

### 每次用完

1. 回到 bridge 终端,按 **`Ctrl+C`** 关掉 bridge
2. Chrome 扩展不用关(下次 bridge 启动后自动连上)

### 可选:开机自动启动 bridge(Phase 2,还没实现)

目前需要手动启动。如果你嫌麻烦,可以写一个 alias:

```bash
# 加到 ~/.zshrc
alias start-bridge='source ~/Developer/tianshu-integrations/.venv/bin/activate && tianshu-bridge --port 7733 --vault ~/Desktop/知识库'
```

以后只需要在终端输入 `start-bridge` 即可。

---

## 10. 进阶:自定义配置

### 10.1 换一个 vault 路径

```bash
# 启动时指定
tianshu-bridge --port 7733 --vault /path/to/your/vault
```

Recall Sticker Side Panel 的 vault path 输入框也要改成同一个路径。

### 10.2 换端口

```bash
tianshu-bridge --port 7734 --vault ~/Desktop/知识库
```

注意:Recall Sticker 的 `lib/bridge-client.js` 里写死了 `http://127.0.0.1:7733`,换端口需要改这个文件。除非必要,不要换。

### 10.3 换 MiniMax 模型

默认用 `MiniMax-M3`。如果想用 M2.1(更便宜但稍慢):

```bash
# 在 bridge 启动前设环境变量
export MINIMAX_MODEL="MiniMax-M2.1"
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

### 10.4 查看错题本原始数据

Deep Reader 的错题存在 `chrome.storage.local.mistake_log_v1`。查看方法:

1. Chrome → 打开任何页面
2. F12 打开 DevTools
3. Application → Storage → Local → 找到 Deep Reader 扩展的 storage
4. 查看 `mistake_log_v1` key

数据结构:
```json
{
  "a1b2c3d4e5f6a7b8": [
    {
      "id": "uuid-...",
      "question": { "type": "trap", "question": "...", "options": [...], "correct": 1, ... },
      "userChoice": 0,
      "isCorrect": false,
      "latencyMs": 3500,
      "sourceUrl": "https://...",
      "sourceTitle": "...",
      "sourceUrlHash": "a1b2c3d4e5f6a7b8",
      "timestamp": 1719500000000
    }
  ]
}
```

每个 sourceUrl 最多保留 50 条(LRU 自动淘汰最旧的)。

### 10.5 手动测试 bridge

不打开 Chrome,直接用 curl 测试 bridge:

```bash
# 健康检查
curl http://127.0.0.1:7733/health

# 同步 1 张卡片
curl -X POST http://127.0.0.1:7733/sync/recall-sticker \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "manual",
    "cards": [{
      "text": "eBPF",
      "context": "kernel tech",
      "sourceUrl": "https://example.com",
      "timestamp": 1
    }],
    "obsidianVaultPath": "/Users/mahaoxuan/Desktop/知识库"
  }'
```

### 10.6 运行测试套件

```bash
cd ~/Developer/tianshu-integrations
source .venv/bin/activate
pytest tests/ -v

# 只跑错误路径测试
pytest tests/test_error_paths.py -v

# 只跑性能测试
pytest tests/test_performance.py -v

# 跑真实 M2.1 集成测试(消耗 API quota)
INTEGRATION_TEST=1 pytest tests/test_llm_client.py -v
```

---

## 附录:文件位置速查

| 文件 | 位置 |
|------|------|
| bridge 源码 | `~/Developer/tianshu-integrations/tianshu_integrations/` |
| bridge 配置 | `~/Developer/tianshu-integrations/pyproject.toml` |
| Recall Sticker 补丁 | `~/Developer/tianshu-integrations/patches/` |
| 补丁应用脚本 | `~/Developer/tianshu-integrations/scripts/` |
| Deep Reader 源码 | `~/Documents/trae_projects/api/deep-reader/src/` |
| Recall Sticker 源码 | `~/Documents/trae_projects/recall-sticker/Recall-Sticker/` |
| Obsidian vault | `~/Desktop/知识库/知识库/` |
| Obsidian Inbox | `~/Desktop/知识库/知识库/Inbox/` |
| 飞书记录 | 奕枢·成长管理系统 → 通用·小项目 → `recvnGVDhdkmil` |
| GitHub | https://github.com/yishu-ziyu/tianshu-integrations |
| Obsidian 项目页 | `~/Desktop/知识库/知识库/03 Projects/Tianshu Integrations/index.md` |
| 开发日志 | `~/Developer/tianshu-integrations/DEVLOG.md` |
| 安装指南 | `~/Developer/tianshu-integrations/INSTALL.md` |
| 性能基线 | `~/Developer/tianshu-integrations/docs/PERFORMANCE-WEEK-2-3-4.md` |
| 录屏脚本 | `~/Developer/tianshu-integrations/docs/RECORDING-WEEK-2-3-4.md` |
| Week 1-4 Release Notes | `~/Developer/tianshu-integrations/RELEASE-NOTES-week-{1,2,3,4}.md` |