// src/lib/minimax.ts - MiniMax API 客户端 (Week 3: OpenAI 协议 + M3)

import { AIResponse, ReadingGuide } from './types';

interface MiniMaxConfig {
  apiKey: string;
  apiHost: string;
}

const DEFAULT_CONFIG: MiniMaxConfig = {
  apiKey: import.meta.env.VITE_MINIMAX_API_KEY || '',
  apiHost: import.meta.env.VITE_MINIMAX_API_HOST || 'https://api.minimaxi.com/v1',
};

/**
 * Strip <think>...</think> reasoning blocks from LLM output.
 * Both MiniMax-M2.1 and MiniMax-M3 wrap their thinking in <think>...</think>
 * before the actual content. JSON parsers will fail if thinking contains
 * stray { or } characters. Call this on the raw response before parsing.
 */
function extractContent(text: string): string {
  if (!text) return '';
  return text.replace(/<think>.*?<\/think>\s*/gs, '').trim();
}

export class MiniMaxClient {
  private config: MiniMaxConfig;

  constructor(config: Partial<MiniMaxConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  async generateReadingGuides(content: string): Promise<ReadingGuide[]> {
    const prompt = this.buildGuidePrompt(content);
    const response = await this.callAPI(prompt, 2000);
    
    return this.parseGuides(response);
  }

  async discussWithAI(content: string, userQuestion: string): Promise<AIResponse> {
    const prompt = this.buildDiscussionPrompt(content, userQuestion);
    const response = await this.callAPI(prompt, 1500);
    
    return {
      id: crypto.randomUUID(),
      content: response,
      type: 'discussion',
      createdAt: Date.now(),
    };
  }


  /**
   * Generic chat method (Week 3 T-19). Returns the raw assistant content.
   * Use this for new features that need raw LLM response (e.g., QuizGenerator).
   * Returns empty string on failure (caller should handle).
   */
  async chat(prompt: string, maxTokens: number = 2000): Promise<string> {
    return await this.callAPI(prompt, maxTokens);
  }

  async summarizeContent(content: string): Promise<AIResponse> {
    const prompt = `请用 200 字以内总结以下文章的核心内容：

${content.slice(0, 6000)}`;

    const response = await this.callAPI(prompt, 500);
    
    return {
      id: crypto.randomUUID(),
      content: response,
      type: 'summary',
      createdAt: Date.now(),
    };
  }

  async explainConcept(content: string, concept: string): Promise<AIResponse> {
    const prompt = `请用简单易懂的方式解释以下段落中的"${concept}"概念：

${content.slice(0, 3000)}`;

    const response = await this.callAPI(prompt, 1000);
    
    return {
      id: crypto.randomUUID(),
      content: response,
      type: 'explanation',
      createdAt: Date.now(),
    };
  }

  private async callAPI(prompt: string, maxTokens: number): Promise<string> {
    try {
      const response = await fetch(`${this.config.apiHost}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify({
          model: 'MiniMax-M3',
          max_tokens: maxTokens,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        }),
      });

      if (!response.ok) {
        throw new Error(`API 请求失败: ${response.status}`);
      }

      const data = await response.json();
      return this.extractTextFromResponse(data);
    } catch (error) {
      console.error('MiniMax API 错误:', error);
      throw error;
    }
  }

  private extractTextFromResponse(data: Record<string, unknown>): string {
    // Week 3: OpenAI chat.completions format
    const choices = data.choices as Array<{ message?: { content?: string } }>;
    if (Array.isArray(choices) && choices.length > 0) {
      const content = choices[0]?.message?.content;
      if (content) {
        // Strip <think>...</think> reasoning blocks (M2.1/M3)
        return extractContent(content);
      }
    }
    return '';
  }

  private buildGuidePrompt(content: string): string {
    return `作为深度阅读助手，请根据以下文章内容生成 3 个引导问题，帮助读者进行批判性思考。

要求：
1. 每个问题应该促进读者深入思考文章的核心论点
2. 问题类型包括：理解型、分析型、评价型
3. 语言简洁、易懂，每个问题不超过 30 字
4. 只返回问题列表，不需要其他内容

文章内容：
${content.slice(0, 4000)}

请生成 3 个引导问题（每行一个）：`;
  }

  private buildDiscussionPrompt(content: string, question: string): string {
    return `你是用户的深度阅读伙伴。请用苏格拉底式对话帮助用户理解文章。

文章相关段落：
${content.slice(0, 2000)}

用户问题：${question}

请通过提问引导用户自己思考，不要直接给出答案。回答应该简短、启发性。`;
  }

  private parseGuides(text: string): ReadingGuide[] {
    const lines = text.split('\n').filter((line) => line.trim());
    const guides: ReadingGuide[] = [];

    lines.forEach((line, index) => {
      const question = line.replace(/^\d+\.\s*/, '').trim();
      if (question) {
        guides.push({
          id: crypto.randomUUID(),
          question,
          type: this.getGuideType(index),
          createdAt: Date.now(),
        });
      }
    });

    return guides.slice(0, 3);
  }

  private getGuideType(index: number): ReadingGuide['type'] {
    const types: ReadingGuide['type'][] = ['comprehension', 'analysis', 'evaluation'];
    return types[index % types.length];
  }
}

export const minimaxClient = new MiniMaxClient();
