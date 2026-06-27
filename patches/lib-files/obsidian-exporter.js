// lib/obsidian-exporter.js
// Generate Obsidian-flavored Markdown from Recall Sticker cards.
// Format is byte-compatible with bridge's obsidian/writer.py output so users
// see the same .md whether they sync online or use the offline fallback.

const FRONTMATTER_DELIM = '---';

function sanitizeSourceUrl(url) {
  if (!url) return '';
  // Strip utm_* and ref tracking params, clean up leftover ?/&
  let cleaned = url.replace(/[?&](utm_\w+|ref)=[^&]*/g, '');
  cleaned = cleaned.replace(/&&+/g, '&');
  if (!cleaned.includes('?') && cleaned.includes('&')) {
    cleaned = cleaned.replace('&', '?', 1);
  }
  cleaned = cleaned.replace(/[?&]$/, '');
  return cleaned;
}

function renderFrontmatter(fm) {
  const lines = [FRONTMATTER_DELIM];
  for (const [key, value] of Object.entries(fm)) {
    if (Array.isArray(value)) {
      lines.push(`${key}: [${value.join(', ')}]`);
    } else {
      lines.push(`${key}: ${value}`);
    }
  }
  lines.push(FRONTMATTER_DELIM);
  return lines.join('\n') + '\n\n';
}

function mergeFrontmatterTags(existingFm, newTags) {
  const existingTags = Array.isArray(existingFm.tags) ? existingFm.tags : [];
  const seen = new Set(existingTags);
  const merged = [...existingTags];
  for (const tag of newTags) {
    if (tag && !seen.has(tag)) {
      merged.push(tag);
      seen.add(tag);
    }
  }
  return { ...existingFm, tags: merged };
}

function renderCardSection(card) {
  let md = `## ${card.title || card.text || 'Untitled'}\n\n`;
  const body = card.context || `${card.prefix || ''} **${card.text || ''}** ${card.suffix || ''}`.trim();
  md += `${body}\n\n`;
  if (card.wikiLinks && card.wikiLinks.length > 0) {
    md += `相关: ${card.wikiLinks.join(' ')}\n\n`;
  }
  if (card.sourceUrl) {
    md += `来源: ${sanitizeSourceUrl(card.sourceUrl)}\n\n`;
  }
  return md;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function readFileText(path) {
  // Read vault file as text. Returns null if file doesn't exist.
  // In Chrome MV3 side panel, no direct filesystem access — would need
  // OffscreenCanvas / File System Access API for production.
  // For bridge-online path, we don't need this; only needed for offline merge.
  return null;
}

/**
 * Generate Markdown for a batch of cards. Format matches bridge's writer.py.
 * @param {Array<Object>} cards - Sticker cards (raw or curated)
 * @param {string} vaultPath - Obsidian vault path (used for metadata, not in output)
 * @returns {string} Markdown text
 */
export function cardsToMarkdown(cards, vaultPath) {
  if (!cards || cards.length === 0) {
    return '';
  }
  const today = todayISO();
  // Collect all unique tags from cards
  const allTags = new Set(['recall-sticker']);
  for (const card of cards) {
    if (card.tags && Array.isArray(card.tags)) {
      for (const tag of card.tags) allTags.add(tag);
    }
  }
  // Build frontmatter
  const fm = {
    date: today,
    tags: [...allTags].sort(),
    source: 'recall-sticker-offline',
  };
  let markdown = renderFrontmatter(fm);
  markdown += `# Recall Sticker · ${today}\n\n`;
  // Render each card section
  for (let i = 0; i < cards.length; i++) {
    if (i > 0) markdown += '\n---\n\n';
    markdown += renderCardSection(cards[i]);
  }
  return markdown;
}