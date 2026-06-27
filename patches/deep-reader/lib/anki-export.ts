// src/lib/anki-export.ts - Anki CSV 导出 (Week 3 T-23)
//
// Port of focus-quiz/focus-quiz-optimized/sidepanel-logic.js:228-250
// formatMistakesAsAnkiCsv to TypeScript.

import { MistakeRecord } from './quiz-types';

/**
 * Format mistake log as Anki-compatible CSV.
 * Header: Front,Back,Source,Evidence,Tags
 * Each row: question, back(user choice + correct + explanation), source, evidence, tag
 */
export function formatMistakesAsAnkiCsv(log: MistakeRecord[]): string {
  const lines = ['Front,Back,Source,Evidence,Tags'];
  for (const item of log || []) {
    const sourceTitle = cleanText(item.sourceTitle || '原文');
    const sourceUrl = cleanText(item.sourceUrl);
    const evidence = [item.question.evidenceQuote, item.question.evidenceLocator]
      .map(cleanText)
      .filter(Boolean)
      .join(' | ');
    const front = cleanText(item.question.question);
    const backParts = [
      item.question.correct !== null && item.question.options[item.question.correct]
        ? `正确答案：${cleanText(item.question.options[item.question.correct])}`
        : '',
      item.userChoice !== null && item.question.options[Number(item.userChoice)]
        ? `我的选择：${cleanText(item.question.options[Number(item.userChoice)])}`
        : '',
      item.question.explanation
        ? `思维断裂点：${cleanText(item.question.explanation)}`
        : '',
    ].filter(Boolean);
    const source = sourceUrl ? `${sourceTitle} ${sourceUrl}` : sourceTitle;
    lines.push([
      csvCell(front),
      csvCell(backParts.join('；')),
      csvCell(source),
      csvCell(evidence),
      csvCell('deep-reader'),
    ].join(','));
  }
  return lines.join('\n');
}

function cleanText(value: string): string {
  return String(value || '').replace(/\r?\n/g, ' ').replace(/\s+/g, ' ').trim();
}

function csvCell(value: string): string {
  return `"${(value || '').replace(/"/g, '""')}"`;
}
