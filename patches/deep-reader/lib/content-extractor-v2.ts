// src/lib/content-extractor-v2.ts - 3-tier content extraction (Week 3 T-17)
//
// Port of focus-quiz/focus-quiz-optimized/lib/page-extractor.js to TypeScript.
// Adds engine field to identify which fallback path was used.

import { Readability } from '@mozilla/readability';
import TurndownService from 'turndown';

export interface ExtractedContentV2 {
  title: string;
  author?: string;
  content: string;        // Markdown
  url: string;
  engine: 'readability-turndown' | 'readability-innertext' | 'dom-innertext';
}

const MAX_CHARS = 12000;
const MIN_TEXT = 120;

const TURNDOWN_OPTIONS = {
  headingStyle: 'atx' as const,
  hr: '---',
  bulletListMarker: '-' as const,
  codeBlockStyle: 'fenced' as const,
};

const FALLBACK_SELECTORS_TO_REMOVE = [
  'script', 'style', 'noscript', 'svg', 'canvas', 'iframe',
  'nav', 'footer', 'header', 'aside', 'form',
  'button', 'input', 'textarea', 'select',
  '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
  '.nav', '.navbar', '.sidebar', '.footer', '.header', '.menu', '.comments', '.comment',
];

export class ContentExtractorV2 {
  /**
   * Extract article content from current page using 3-tier fallback:
   * 1. Readability + Turndown (best, returns Markdown)
   * 2. Readability + innerText (good, returns plain text)
   * 3. DOM candidates innerText (last resort, returns plain text)
   */
  static extract(): ExtractedContentV2 | null {
    // 1. Readability + Turndown
    const readability = this._tryReadability();
    if (readability) {
      const md = this._toMarkdown(readability.content);
      if (md && md.length >= MIN_TEXT) {
        return {
          title: readability.title,
          content: md.slice(0, MAX_CHARS),
          url: window.location.href,
          engine: 'readability-turndown',
        };
      }

      // 2. Readability + innerText (Turndown failed but Readability succeeded)
      const text = this._htmlToText(readability.content);
      if (text && text.length >= MIN_TEXT) {
        return {
          title: readability.title,
          content: text.slice(0, MAX_CHARS),
          url: window.location.href,
          engine: 'readability-innertext',
        };
      }
    }

    // 3. DOM candidates fallback
    const bestText = this._domCandidatesText();
    if (bestText && bestText.length >= MIN_TEXT) {
      return {
        title: document.title || 'Untitled',
        content: bestText.slice(0, MAX_CHARS),
        url: window.location.href,
        engine: 'dom-innertext',
      };
    }

    return null;
  }

  private static _tryReadability(): { title: string; content: string } | null {
    try {
      const docClone = document.cloneNode(true) as Document;
      const article = new Readability(docClone).parse();
      if (article?.content) {
        return {
          title: article.title || document.title || 'Untitled',
          content: article.content,
        };
      }
    } catch (err) {
      console.warn('[content-extractor-v2] Readability failed:', err);
    }
    return null;
  }

  private static _toMarkdown(html: string): string {
    try {
      const turndown = new TurndownService(TURNDOWN_OPTIONS);
      const md = turndown.turndown(html);
      // Clean up extra blank lines
      return md.replace(/\n{3,}/g, '\n\n').trim();
    } catch (err) {
      console.warn('[content-extractor-v2] Turndown failed:', err);
      return '';
    }
  }

  private static _htmlToText(html: string): string {
    const div = document.createElement('div');
    div.innerHTML = html;
    // Remove noise elements
    FALLBACK_SELECTORS_TO_REMOVE.forEach((sel) => {
      div.querySelectorAll(sel).forEach((el) => el.remove());
    });
    return (div.innerText || div.textContent || '').replace(/\s+/g, ' ').trim();
  }

  private static _domCandidatesText(): string {
    const candidates = document.querySelectorAll(
      'article, main, [role="main"], .article, .post, .content, .entry-content'
    );
    let bestText = '';
    for (const el of Array.from(candidates)) {
      const text = (el as HTMLElement).innerText.replace(/\s+/g, ' ').trim();
      if (text.length > bestText.length) bestText = text;
    }
    if (bestText.length >= MIN_TEXT) return bestText;
    // Last resort: body
    return (document.body.innerText || '').slice(0, MAX_CHARS);
  }
}
