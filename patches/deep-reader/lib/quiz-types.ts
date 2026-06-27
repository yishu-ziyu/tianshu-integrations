// src/lib/quiz-types.ts - 测验 schema (Week 3 T-18)
//
// Question + MistakeRecord schemas for Deep Reader quiz feature.
// Mirrors focus-quiz's normalizeP1Question output (sidepanel-logic.js:182-221)
// for backwards compatibility.

export type QuestionType = 'trap' | 'counterfactual' | 'transfer';

export type AnswerMode = 'multiple_choice' | 'open';

export interface Question {
  type: QuestionType;
  answerMode: AnswerMode;
  question: string;
  options: string[];              // empty if answerMode='open'
  correct: number | null;          // index into options if MC; null if open
  explanation: string;
  expectedAnswer: string;          // open 模式用
  rubric: string;                  // open 模式用
  evidenceQuote: string;
  evidenceLocator: string;
  sourceHint: string;
}

export interface MistakeRecord {
  id: string;
  question: Question;
  userChoice: number | string | null;
  isCorrect: boolean;
  latencyMs: number;
  sourceUrl: string;
  sourceTitle: string;
  sourceUrlHash: string;           // sha256(sourceUrl).slice(0, 16) — LRU key
  timestamp: number;
}

// chrome.storage.local key
export const STORAGE_KEY = 'mistake_log_v1';

// LRU cap: 50 per sourceUrlHash
export const LRU_CAP = 50;
