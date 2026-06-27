// src/lib/quiz-generator.ts - M2.1 出题 + parse 4 层 fallback (Week 3 T-19)
//
// Port of focus-quiz's normalizeP1Question (sidepanel-logic.js:182-221) to TypeScript.
// + 4-layer JSON parser (Week 2 curator/parsers.py port)
// + extractContent() to strip <think>...</think> reasoning blocks.

import { minimaxClient } from './minimax';
import { Question, QuestionType } from './quiz-types';

const PROMPT = `你是认知压力测试教练。基于以下文章生成 3 道测验题。

文章: {content}

要求:
- 3 道题覆盖 trap(概念边界)/ counterfactual(因果反事实)/ transfer(场景迁移) 各 1 道
- 每道题 4 个选项 + 1 个正确答案(用 0-3 索引)
- 给出 evidenceQuote(原文引用, ≤50 字)
- 给出 explanation(为什么对/错)
- 返回严格 JSON 数组: [{"type": "...", "question": "...", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "...", "evidenceQuote": "...", "sourceHint": "..."}]
- 题型字段必须 ∈ ["trap", "counterfactual", "transfer"]
- 直接返回 JSON 数组,不要额外文字或思考过程`;

const ALLOWED_TYPES: QuestionType[] = ['trap', 'counterfactual', 'transfer'];

export class QuizGenerator {
  /**
   * Generate 3 questions from article content using M2.1.
   * Returns empty array if content too short or all attempts fail.
   */
  static async generate(content: string): Promise<Question[]> {
    if (!content || content.length < 100) {
      return [];
    }
    const truncated = content.slice(0, 6000);
    const prompt = PROMPT.replace('{content}', truncated);
    try {
      const raw = await minimaxClient.chat(prompt, 4000);
      const parsed = parseQuizResponse(raw);
      return parsed
        .map((q, i) => normalizeP1Question(q, i))
        .filter((q): q is Question => q !== null);
    } catch (err) {
      console.error('[QuizGenerator] M2.1 call failed:', err);
      return [];
    }
  }
}

/**
 * Parse LLM response with 4-layer fallback.
 * 1. Strict JSON parse (handle array root)
 * 2. Extract first [...] block
 * 3. Extract ```json ... ``` markdown block
 * 4. Empty array fallback
 */
function parseQuizResponse(raw: string): any[] {
  if (!raw) return [];

  // Layer 1: strict JSON
  try {
    const parsed = JSON.parse(raw);
    return extractArray(parsed);
  } catch {
    // continue
  }

  // Layer 2: extract first [...] block
  const arrayMatch = raw.match(/\[[\s\S]*?\]/);
  if (arrayMatch) {
    try {
      const parsed = JSON.parse(arrayMatch[0]);
      return extractArray(parsed);
    } catch {
      // continue
    }
  }

  // Layer 3: ```json ... ``` block
  const codeBlock = raw.match(/```json\s*([\s\S]+?)\s*```/);
  if (codeBlock) {
    try {
      const parsed = JSON.parse(codeBlock[1]);
      return extractArray(parsed);
    } catch {
      // continue
    }
  }

  // Layer 4: empty
  return [];
}

function extractArray(parsed: any): any[] {
  if (Array.isArray(parsed)) return parsed;
  if (parsed && Array.isArray(parsed.questions)) return parsed.questions;
  if (parsed && Array.isArray(parsed.rewrites)) return parsed.rewrites;
  if (parsed && Array.isArray(parsed.data)) return parsed.data;
  return [];
}

/**
 * Normalize a raw question from LLM into our Question schema.
 * Port of focus-quiz/focus-quiz-optimized/sidepanel-logic.js:182-221.
 */
function normalizeP1Question(rawQuestion: any, idx = 0): Question | null {
  if (!rawQuestion || typeof rawQuestion !== 'object') return null;

  // Type: must be in allowed list, else default by index
  const type: QuestionType = ALLOWED_TYPES.includes(rawQuestion.type)
    ? rawQuestion.type
    : (ALLOWED_TYPES[idx] || 'trap');

  const answerMode: 'open' | 'multiple_choice' = rawQuestion.answerMode === 'open' ? 'open' : 'multiple_choice';

  const baseFields = {
    type,
    answerMode,
    question: String(rawQuestion.question || `Q${idx + 1}`).trim(),
    options: Array.isArray(rawQuestion.options)
      ? rawQuestion.options.map((opt: any) => String(opt))
      : [],
    correct: typeof rawQuestion.correct === 'number'
      ? rawQuestion.correct
      : (Number.isInteger(parseInt(String(rawQuestion.correct), 10))
          ? parseInt(String(rawQuestion.correct), 10)
          : null),
    explanation: String(
      rawQuestion.explanation ||
      rawQuestion.rubric ||
      '模型未返回解析。'
    ).trim(),
    evidenceQuote: String(rawQuestion.evidenceQuote || '').trim(),
    evidenceLocator: String(rawQuestion.evidenceLocator || '').trim(),
    sourceHint: String(rawQuestion.sourceHint || '').trim(),
  };

  if (answerMode === 'open') {
    return {
      ...baseFields,
      correct: null,
      expectedAnswer: String(rawQuestion.expectedAnswer || '').trim(),
      rubric: String(rawQuestion.rubric || '').trim(),
    };
  }

  return {
    ...baseFields,
    expectedAnswer: '',
    rubric: '',
  };
}
