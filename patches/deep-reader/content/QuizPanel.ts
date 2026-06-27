// src/content/QuizPanel.ts - Shadow DOM 测验 UI (Week 3 T-21)
//
// Renders questions one at a time, captures answers, persists mistakes to
// chrome.storage.local via MistakeStore, supports Anki CSV export.

import { Question, MistakeRecord } from '../lib/quiz-types';
import { ExtractedContent } from '../lib/types';

export interface QuizPanelOptions {
  questions: Question[];
  content: ExtractedContent;
  container: HTMLElement;
}

const QUIZ_CSS = `
:host { all: initial; }
.quiz-wrap { font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13px; color: #1f2937; padding: 8px 0; }
.quiz-progress { color: #6b7280; font-size: 11px; margin-bottom: 6px; }
.quiz-type { display: inline-block; background: #3b82f6; color: white; font-size: 10px; padding: 1px 6px; border-radius: 3px; margin-bottom: 8px; }
.quiz-question { font-size: 13px; font-weight: 600; margin: 8px 0; line-height: 1.4; }
.quiz-options { display: flex; flex-direction: column; gap: 4px; }
.quiz-option { padding: 6px 10px; background: #f9fafb; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; text-align: left; font-size: 12px; font-family: inherit; }
.quiz-option:hover { background: #f3f4f6; }
.quiz-option.correct { background: #d1fae5; border-color: #059669; }
.quiz-option.wrong { background: #fee2e2; border-color: #dc2626; }
.quiz-feedback { margin-top: 8px; padding: 8px; background: #fef3c7; border-radius: 4px; font-size: 12px; line-height: 1.4; }
.quiz-feedback .correct { color: #059669; font-weight: 600; }
.quiz-feedback .wrong { color: #dc2626; font-weight: 600; }
.quiz-actions { margin-top: 8px; display: flex; gap: 6px; }
.quiz-btn { padding: 5px 10px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-family: inherit; }
.quiz-btn:hover { background: #2563eb; }
.quiz-btn:disabled { background: #9ca3af; cursor: not-allowed; }
.quiz-done { text-align: center; color: #059669; font-weight: 600; padding: 16px 0; }
.quiz-error { color: #dc2626; padding: 8px; }
`;

export class QuizPanel {
  private questions: Question[];
  private content: ExtractedContent;
  private container: HTMLElement;
  private shadow: ShadowRoot;
  private currentIdx = 0;
  private answers: Array<number | string | null> = [];
  private startedAt = 0;
  private mistakes: MistakeRecord[] = [];

  constructor(options: QuizPanelOptions) {
    this.questions = options.questions;
    this.content = options.content;
    this.container = options.container;
  }

  mount() {
    this.container.innerHTML = '';
    this.shadow = this.container.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = QUIZ_CSS;
    this.shadow.appendChild(style);
    const wrap = document.createElement('div');
    wrap.className = 'quiz-wrap';
    this.shadow.appendChild(wrap);
    this.startedAt = Date.now();
    this.renderCurrent(wrap);
  }

  private renderCurrent(host: HTMLElement) {
    const q = this.questions[this.currentIdx];
    if (!q) {
      this.renderDone(host);
      return;
    }
    host.innerHTML = `
      <div class="quiz-progress">题目 ${this.currentIdx + 1} / ${this.questions.length}</div>
      <span class="quiz-type">${this.typeLabel(q.type)}</span>
      <h3 class="quiz-question">${this.escapeHtml(q.question)}</h3>
      <div class="quiz-options" id="quiz-options">
        ${q.options.map((opt, i) => `
          <button class="quiz-option" data-idx="${i}">${this.escapeHtml(opt)}</button>
        `).join('')}
      </div>
      <div class="quiz-feedback" id="quiz-feedback" style="display:none"></div>
      <div class="quiz-actions">
        <button class="quiz-btn" id="quiz-next" style="display:none">${this.currentIdx === this.questions.length - 1 ? '完成' : '下一题'}</button>
        <button class="quiz-btn" id="quiz-export" style="display:none">导出 Anki</button>
      </div>
    `;
    host.querySelectorAll('.quiz-option').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt((e.currentTarget as HTMLElement).dataset.idx || '0', 10);
        this.handleAnswer(host, idx);
      });
    });
    (host.querySelector('#quiz-next') as HTMLButtonElement).addEventListener('click', () => {
      this.currentIdx++;
      this.renderCurrent(host);
    });
    (host.querySelector('#quiz-export') as HTMLButtonElement).addEventListener('click', () => this.exportAnki());
  }

  private async handleAnswer(host: HTMLElement, choiceIdx: number) {
    const q = this.questions[this.currentIdx];
    if (!q) return;
    const isCorrect = q.answerMode === 'multiple_choice' ? choiceIdx === q.correct : false;
    const latency = Date.now() - this.startedAt;
    this.answers.push(choiceIdx);

    // Show feedback
    const optionBtns = host.querySelectorAll('.quiz-option');
    optionBtns.forEach((btn, i) => {
      (btn as HTMLButtonElement).disabled = true;
      if (i === q.correct) btn.classList.add('correct');
      if (i === choiceIdx && !isCorrect) btn.classList.add('wrong');
    });
    const fb = host.querySelector('#quiz-feedback') as HTMLElement;
    fb.style.display = 'block';
    fb.innerHTML = `<p class="${isCorrect ? 'correct' : 'wrong'}">${isCorrect ? '✓ 正确' : '✗ 错误'}</p><p>${this.escapeHtml(q.explanation)}</p>`;

    // Persist mistake
    if (!isCorrect) {
      const record: MistakeRecord = {
        id: crypto.randomUUID(),
        question: q,
        userChoice: choiceIdx,
        isCorrect: false,
        latencyMs: latency,
        sourceUrl: this.content.url,
        sourceTitle: this.content.title,
        sourceUrlHash: await this.hashUrl(this.content.url),
        timestamp: Date.now(),
      };
      this.mistakes.push(record);
      // Dynamic import to avoid loading MistakeStore until needed
      const { MistakeStore } = await import('../lib/mistake-store');
      const store = new MistakeStore();
      await store.save(record);
    }

    // Show next button (or export on last)
    const nextBtn = host.querySelector('#quiz-next') as HTMLButtonElement;
    nextBtn.style.display = 'inline-block';
    if (this.currentIdx === this.questions.length - 1) {
      nextBtn.textContent = '完成';
      const exportBtn = host.querySelector('#quiz-export') as HTMLButtonElement;
      exportBtn.style.display = 'inline-block';
    }
  }

  private renderDone(host: HTMLElement) {
    const correctCount = this.answers.filter((a, i) => {
      const q = this.questions[i];
      return q && a === q.correct;
    }).length;
    const total = this.questions.length;
    host.innerHTML = `
      <div class="quiz-done">🎉 测验完成!</div>
      <p style="text-align:center; color:#6b7280; font-size:12px;">${correctCount} / ${total} 正确</p>
      <div class="quiz-actions" style="justify-content:center;">
        <button class="quiz-btn" id="quiz-export-done">导出 Anki CSV</button>
      </div>
    `;
    host.querySelector('#quiz-export-done')?.addEventListener('click', () => this.exportAnki());
  }

  private async exportAnki() {
    try {
      const { formatMistakesAsAnkiCsv } = await import('../lib/anki-export');
      // Include both new mistakes + any persisted ones for this URL
      const { MistakeStore } = await import('../lib/mistake-store');
      const store = new MistakeStore();
      const persisted = await store.list(await this.hashUrl(this.content.url));
      const allMistakes = [...this.mistakes, ...persisted];
      const csv = formatMistakesAsAnkiCsv(allMistakes);
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mistakes-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('[QuizPanel] exportAnki failed:', err);
    }
  }

  private async hashUrl(url: string): Promise<string> {
    const data = new TextEncoder().encode(url);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private typeLabel(t: string): string {
    return ({ trap: '概念边界', counterfactual: '因果反事实', transfer: '场景迁移' } as Record<string, string>)[t] || t;
  }
}
