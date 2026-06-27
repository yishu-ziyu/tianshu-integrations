# Tianshu Integrations · Install Guide

> **date**: 2026-06-28
> **scope**: Week 4 T-29 — step-by-step installation

---

## 1. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | ≥ 3.10 | `python3 --version` |
| Node.js | ≥ 18 | `node --version` |
| Chrome | ≥ 110 | `chrome://version` |
| Obsidian | ≥ 1.0 | Optional, for vault viewing |
| uv (recommended) | latest | `uv --version` |

---

## 2. Install bridge

```bash
# Clone the repo
git clone https://github.com/yishu-ziyu/tianshu-integrations.git
cd tianshu-integrations

# Create venv + install (uv recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Verify
tianshu-bridge --help
pytest tests/ -q
```

Expected: 98 passed, 4 skipped.

---

## 3. Configure environment

```bash
# Required - MiniMax API key (Token Plan)
export MINIMAX_API_KEY="sk-cp-..."  # from platform.minimaxi.com

# Optional - custom vault path (default: ~/Desktop/知识库/知识库)
export OBSIDIAN_VAULT="$HOME/Documents/obsidian-vault"
```

---

## 4. Start bridge

```bash
tianshu-bridge --port 7733 --vault ~/Desktop/知识库
```

Expected output:
```
Starting tianshu-bridge on 127.0.0.1:7733
  Vault: /Users/you/Desktop/知识库/知识库
  M2.1:  configured
INFO:     Uvicorn running on http://127.0.0.1:7733
```

---

## 5. Health check

```bash
curl http://127.0.0.1:7733/health | python3 -m json.tool
```

Expected:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "vaultWritable": true,
  "minimaxConfigured": true,
  "currentVault": "/Users/you/Desktop/知识库",
  "uptimeSec": 5
}
```

---

## 6. Apply Recall Sticker patches

Recall Sticker 仓库在 `~/Documents/trae_projects/recall-sticker/Recall-Sticker/`,需要 2 个 patches:

```bash
# Apply Week 1 patches (manifest host_permissions + sidepanel blacklist)
bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-patches.sh

# Apply Week 2 patches (sync button + 3 new lib/ files)
bash ~/Developer/tianshu-integrations/scripts/apply-recall-sticker-week2-patches.sh
```

Both scripts are **idempotent** — re-running skips already-applied parts.

---

## 7. Load Chrome extensions

### 7.1 Recall Sticker

`chrome://extensions` → 开启"开发者模式" → "加载已解压的扩展程序" → 选 `~/Documents/trae_projects/recall-sticker/Recall-Sticker/`

### 7.2 Deep Reader (optional, for Week 3 quiz)

Same process with `~/Documents/trae_projects/api/deep-reader/`. (Deep Reader has its own build: `cd deep-reader && npm install && npm run build`, then load `dist/`.)

---

## 8. End-to-end smoke test

```bash
# 1. Start bridge (in one terminal)
source ~/Developer/tianshu-integrations/.venv/bin/activate
tianshu-bridge --port 7733 --vault ~/Desktop/知识库

# 2. Send 1 test card via curl (in another terminal)
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
    "obsidianVaultPath": "/Users/you/Desktop/知识库"
  }'
```

Expected response:
```json
{
  "success": true,
  "curated": [{"cardId": "1", "title": "eBPF", "body": "kernel tech", "tags": [...], "wikiLinks": [], "mergedWith": null, "sourceUrl": "https://example.com"}],
  "skipped": [],
  "errors": [],
  "durationMs": 9000,
  "obsidianFilesWritten": ["Inbox/2026-06-28-recall.md"]
}
```

Verify file: `ls ~/Desktop/知识库/Inbox/` → should show `2026-06-28-recall.md`.

---

## 9. Deep Reader quiz test (Week 3)

1. In Chrome, navigate to any long article (e.g., Wikipedia, blog post)
2. Press `Alt+D` to trigger Deep Reader
3. Click "📝 开始测验" in the sidebar
4. Wait ~5-10 seconds for 3 questions to generate
5. Answer each question
6. Click "导出 Anki CSV" — browser downloads `mistakes-{timestamp}.csv`
7. Import the CSV into Anki to verify Cloze format works

---

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| `tianshu-bridge: command not found` | `source .venv/bin/activate` |
| `minimaxConfigured: false` | `echo $MINIMAX_API_KEY` |
| `vaultWritable: false` | `ls -la $OBSIDIAN_VAULT` (must be writable) |
| `/sync` returns 400 "not the configured" | vault path in request must == `OBSIDIAN_VAULT` env |
| Recall Sticker fetch fails | Confirm manifest patch applied, Chrome reloaded |
| Side Panel "is not a function" | Re-run week2 patches, reload extension |
| Deep Reader "is not a function" or 500 | `cd deep-reader && npm run build` |
| M2.1 timeout / non-JSON | Check API key, retry — parser has 4-layer fallback |
| chrome.storage quota | MistakeStore LRU caps at 50/source |

---

## 11. Next steps

- Try a real Recall Sticker session
- Use Deep Reader on a long article
- Check Obsidian vault/Inbox/ for output
- Export Anki CSV from quiz, import into Anki
- For advanced usage, see [docs/RECORDING-WEEK-2-3-4.md](./RECORDING-WEEK-2-3-4.md)

## 12. Uninstall

```bash
# Stop bridge: Ctrl+C in terminal, or
pkill -f "tianshu-bridge"

# Remove Chrome extensions: chrome://extensions → Remove

# Remove environment variables
unset MINIMAX_API_KEY OBSIDIAN_VAULT

# Optionally remove repo + venv
rm -rf ~/Developer/tianshu-integrations
```

Data stays in chrome.storage.local and Obsidian vault. To clear:
- Chrome: `chrome://settings/clearBrowserData` → "Cookies and other site data"
- Obsidian: delete files manually
EOF
