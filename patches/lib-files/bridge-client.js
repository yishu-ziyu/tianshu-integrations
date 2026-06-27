// lib/bridge-client.js
// Sync Recall Sticker cards to tianshu-integrations bridge.
// Falls back to local .md download via chrome.downloads if bridge is unreachable.

import { cardsToMarkdown } from './obsidian-exporter.js';
import { collectAllStickers } from './storage-collector.js';

const BRIDGE_URL = 'http://127.0.0.1:7733';
const DEFAULT_TIMEOUT_MS = 30000;

/**
 * Sync cards to bridge via POST /sync/recall-sticker.
 * @param {Array<Object>} cards
 * @param {{vaultPath: string, apiKey?: string, timeout?: number, minimaxApiKey?: string}} options
 * @returns {Promise<{success: boolean, mode: 'online' | 'offline_fallback', response?: any, offlinePath?: string, error?: string}>}
 */
export async function syncToBridge(cards, options) {
  const { vaultPath, apiKey, timeout = DEFAULT_TIMEOUT_MS, minimaxApiKey } = options;

  if (!vaultPath) {
    return { success: false, error: 'vault path not configured' };
  }

  // Ensure all cards have IDs (curator will generate if missing)
  const cardsWithIds = cards.map((c) => ({
    ...c,
    id: c.id || String(c.timestamp) + '_' + (c.text || '').slice(0, 10).replace(/\W+/g, '_'),
  }));

  // Try online sync
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    const response = await fetch(`${BRIDGE_URL}/sync/recall-sticker`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trigger: 'manual',
        cards: cardsWithIds,
        obsidianVaultPath: vaultPath,
        minimaxApiKey: minimaxApiKey || apiKey,  // bridge accepts either
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.status === 503) {
      throw new Error('bridge not ready');
    }
    if (!response.ok) {
      throw new Error(`bridge error: HTTP ${response.status}`);
    }
    const data = await response.json();
    return {
      success: true,
      mode: 'online',
      response: data,
    };
  } catch (err) {
    // Offline fallback: generate .md locally + trigger chrome.downloads
    console.warn('[bridge-client] online sync failed, falling back to offline:', err.message);
    return await offlineFallback(cardsWithIds, vaultPath, err.message);
  }
}

async function offlineFallback(cards, vaultPath, errorMessage) {
  try {
    const markdown = cardsToMarkdown(cards, vaultPath);
    const date = new Date().toISOString().slice(0, 10);
    const filename = `recall-stickers-${date}.md`;
    // Use Blob URL instead of data: URL (MV3 has data: URL restrictions)
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const downloadId = await chrome.downloads.download({
      url,
      filename,
      saveAs: true,
    });
    // Revoke the Blob URL after a delay to ensure download started
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return {
      success: true,
      mode: 'offline_fallback',
      offlinePath: filename,
      downloadId,
      error: errorMessage,
    };
  } catch (dlErr) {
    return {
      success: false,
      mode: 'offline_fallback',
      error: `offline fallback failed: ${dlErr.message}; original error: ${errorMessage}`,
    };
  }
}

/**
 * Collect all stickers from chrome.storage and sync to bridge.
 * Convenience wrapper combining collectAllStickers + syncToBridge.
 * @param {{vaultPath: string, apiKey?: string, timeout?: number}} options
 * @returns {Promise<{success, mode, response?, offlinePath?, error?, collectedCount}>}
 */
export async function collectAndSync(options) {
  const cards = await collectAllStickers();
  const result = await syncToBridge(cards, options);
  return { ...result, collectedCount: cards.length };
}

/**
 * Check bridge health before attempting sync.
 * @returns {Promise<{ok: boolean, data?: any, error?: string}>}
 */
export async function checkBridgeHealth() {
  try {
    const r = await fetch(`${BRIDGE_URL}/health`);
    if (!r.ok) return { ok: false, error: `HTTP ${r.status}` };
    return { ok: true, data: await r.json() };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}