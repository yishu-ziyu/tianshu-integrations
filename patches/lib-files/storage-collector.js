// lib/storage-collector.js
// Collect all Recall Sticker cards from chrome.storage.local.
// Used by bridge-client.syncToBridge() to send batches.
//
// Per Week 1 review, sidepanel.js uses isStickerCollection(key, value) which
// treats any array-typed chrome.storage key as a sticker collection.
// tianshu-integrations chrome.storage key blacklisting ensures cross-extension
// data is not mis-read as stickers.

const STORAGE_KEY_BLACKLIST = new Set([
  'tags', 'obsidianVaultPath', 'lastSyncTime', 'mistake_log_v1',
]);

function isStickerCollection(storageKey, value) {
  return !STORAGE_KEY_BLACKLIST.has(storageKey) && Array.isArray(value);
}

/**
 * Collect all stickers from chrome.storage.local.
 * Returns flat list of {id, text, prefix, suffix, context, sourceUrl, tags, timestamp}
 * @returns {Promise<Array<Object>>}
 */
export function collectAllStickers() {
  return new Promise((resolve) => {
    chrome.storage.local.get(null, (result) => {
      const stickers = [];
      for (const [key, value] of Object.entries(result)) {
        if (!isStickerCollection(key, value)) continue;
        for (const s of value) {
          stickers.push({
            id: String(s.timestamp) + '_' + (s.text || '').slice(0, 10).replace(/\W+/g, '_'),
            text: s.text || '',
            prefix: s.prefix || '',
            suffix: s.suffix || '',
            context: s.context || '',
            sourceUrl: s.sourceUrl || '',
            tags: [],  // Recall Sticker doesn't have tags in storage
            timestamp: s.timestamp,
          });
        }
      }
      resolve(stickers);
    });
  });
}