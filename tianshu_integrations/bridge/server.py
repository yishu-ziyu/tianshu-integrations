"""FastAPI bridge server for Tianshu Integrations.

Endpoints:
- GET /health: health check (vault writable, M2.1 configured, uptime)
- POST /sync/recall-sticker: sync cards from Recall Sticker to Obsidian
- POST /trigger/curate: re-curate already-synced cards (Phase 2)

Week 1 MVP: /health + /sync/recall-sticker (no M2.1 yet, direct write).
"""

import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from tianshu_integrations.bridge.schemas import SyncRequest, SyncResponse
from tianshu_integrations.curator.curate import curate
from tianshu_integrations.llm.client import MiniMaxClient, MockLLMClient
from tianshu_integrations.obsidian.writer import write_batch

VERSION = "0.1.0"
START_TIME = time.time()

app = FastAPI(title="Tianshu Bridge", version=VERSION)


@app.get("/health")
def health() -> dict:
    """Health check endpoint. Returns 200 always (so callers know bridge is up).

    Body indicates whether vault is writable and M2.1 is configured.
    """
    vault = os.environ.get("OBSIDIAN_VAULT", "")
    vault_exists = bool(vault) and Path(vault).is_dir()
    vault_writable = vault_exists and os.access(vault, os.W_OK)
    minimax_configured = bool(os.environ.get("MINIMAX_API_KEY"))

    return {
        "status": "ok",
        "version": VERSION,
        "vaultWritable": vault_writable,
        "minimaxConfigured": minimax_configured,
        "currentVault": vault,
        "uptimeSec": int(time.time() - START_TIME),
    }


@app.post("/sync/recall-sticker", response_model=SyncResponse)
async def sync_recall_sticker(req: SyncRequest) -> SyncResponse:
    """Sync a batch of cards from Recall Sticker to Obsidian Vault.

    Flow:
    1. Validate obsidianVaultPath exists and writable
    2. Sanitize card context (strip Anki Cloze markers)
    3. Curate via M2.1 (or MockLLMClient if no key)
    4. Write curated cards to vault/Inbox/YYYY-MM-DD-recall.md
    5. Return SyncResponse with curated/skipped/errors
    """
    started = time.time()

    # 1. Vault validation
    vault = req.obsidianVaultPath
    # Ensure requested vault is the same as (or under) the configured vault.
    # This prevents a client from tricking the bridge into writing to
    # arbitrary paths (e.g., /etc/ or another user's home).
    env_vault = os.environ.get("OBSIDIAN_VAULT", "")
    if env_vault:
        try:
            requested = Path(vault).resolve()
            allowed = Path(env_vault).resolve()
            if requested != allowed and not str(requested).startswith(str(allowed) + os.sep):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": f"vault path {vault} is not the configured OBSIDIAN_VAULT ({env_vault})",
                    },
                )
        except (OSError, ValueError):
            # Path resolution failed (e.g., invalid path syntax) — reject
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"invalid vault path: {vault}"},
            )
    if not Path(vault).is_dir():
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"vault path does not exist: {vault}"},
        )
    if not os.access(vault, os.W_OK):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"vault path not writable: {vault}"},
        )

    # 2-4. Curate + Write
    # Generate cardId from timestamp if missing
    for card in req.cards:
        if not card.id:
            card.id = str(card.timestamp)

    # Use mock if no API key (for offline / week 1 testing)
    if os.environ.get("MINIMAX_API_KEY") and not req.minimaxApiKey == "__MOCK__":
        try:
            llm_client = MiniMaxClient(api_key=req.minimaxApiKey)
        except Exception:
            llm_client = MockLLMClient()
    else:
        llm_client = MockLLMClient()

    try:
        # Week 2: curate() now takes vault_path for Phase B wiki link scan
        curated, errors = await curate(req.cards, llm_client=llm_client, vault_path=vault)
        written_files = write_batch(curated, vault)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"internal error: {e}"},
        )

    duration_ms = int((time.time() - started) * 1000)
    return SyncResponse(
        success=True,
        curated=curated,
        errors=errors,
        durationMs=duration_ms,
        obsidianFilesWritten=written_files,
    )


@app.post("/trigger/curate", response_model=SyncResponse)
async def trigger_curate() -> dict:
    """Re-curate already-synced cards. Phase 2 placeholder."""
    raise HTTPException(status_code=501, detail="not implemented yet (Phase 2)")