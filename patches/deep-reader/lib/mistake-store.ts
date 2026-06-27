// src/lib/mistake-store.ts - chrome.storage 错题本 + LRU (Week 3 T-22)

import { MistakeRecord, STORAGE_KEY, LRU_CAP } from './quiz-types';

export class MistakeStore {
  /**
   * Save a mistake. If sourceUrlHash has > LRU_CAP records, drop oldest.
   */
  async save(record: MistakeRecord): Promise<void> {
    const all = await this.getAll();
    const list = all[record.sourceUrlHash] || [];
    list.push(record);
    // LRU: keep only latest LRU_CAP
    if (list.length > LRU_CAP) {
      list.splice(0, list.length - LRU_CAP);
    }
    all[record.sourceUrlHash] = list;
    await chrome.storage.local.set({ [STORAGE_KEY]: all });
  }

  /**
   * List mistakes. If sourceUrlHash given, return only that source's.
   * Otherwise return all flattened.
   */
  async list(sourceUrlHash?: string): Promise<MistakeRecord[]> {
    const all = await this.getAll();
    if (sourceUrlHash) {
      return all[sourceUrlHash] || [];
    }
    return Object.values(all).flat();
  }

  /**
   * Clear mistakes. If sourceUrlHash given, only clear that source.
   */
  async clear(sourceUrlHash?: string): Promise<void> {
    if (!sourceUrlHash) {
      await chrome.storage.local.remove(STORAGE_KEY);
      return;
    }
    const all = await this.getAll();
    delete all[sourceUrlHash];
    await chrome.storage.local.set({ [STORAGE_KEY]: all });
  }

  /**
   * sha256 of URL, truncated to 16 hex chars (8 bytes).
   * Used as sourceUrlHash for LRU key.
   */
  async hashUrl(url: string): Promise<string> {
    const data = new TextEncoder().encode(url);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
  }

  private async getAll(): Promise<Record<string, MistakeRecord[]>> {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        resolve((result[STORAGE_KEY] as Record<string, MistakeRecord[]>) || {});
      });
    });
  }
}
