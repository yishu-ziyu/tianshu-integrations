// src/content/components/ReaderPanel.ts - 纯净阅读面板组件

import type { ExtractedContent, ReaderSettings, Highlight, Note } from '../../lib/types';

interface GuideItem {
  question: string;
  type: string;
}

export class ReaderPanel {
  private content: ExtractedContent;
  private settings: ReaderSettings;
  private container: HTMLElement;
  private isDestroyed: boolean = false;
  private highlights: Highlight[] = [];
  private notes: Note[] = [];

  constructor(options: { content: ExtractedContent; settings: ReaderSettings }) {
    this.content = options.content;
    this.settings = options.settings;
    this.container = document.createElement('div');
    this.container.id = 'deep-reader-panel';
    this.container.className = `theme-${this.settings.theme}`;
    void this.loadHighlightsAndNotes();
  }

  private async loadHighlightsAndNotes(): Promise<void> {
    try {
      const result = await chrome.storage.local.get(['highlights', 'notes']);
      this.highlights = (result.highlights as Highlight[]) || [];
      this.notes = (result.notes as Note[]) || [];
    } catch (error) {
      console.error('加载高亮和笔记失败:', error);
    }
  }

  mount(parent: HTMLElement): void {
    this.render();
    parent.appendChild(this.container);
    this.bindEvents();
  }

  destroy(): void {
    if (!this.isDestroyed) {
      this.container.remove();
      this.isDestroyed = true;
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="dr-overlay"></div>
      <div class="dr-panel">
        <div class="dr-header">
          <div class="dr-title-section">
            <h1 class="dr-title">${this.escapeHtml(this.content.title)}</h1>
            <div class="dr-meta">
              ${this.content.author ? `<span class="dr-author">${this.escapeHtml(this.content.author)}</span>` : ''}
              <span class="dr-reading-time">约 ${this.content.readingTime} 分钟</span>
              <span class="dr-word-count">${this.content.wordCount} 字</span>
            </div>
          </div>
          <div class="dr-actions">
            <button class="dr-btn dr-btn-icon" id="dr-toggle-ai" title="AI 助手">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
                <circle cx="8.5" cy="14.5" r="1.5"/>
                <circle cx="15.5" cy="14.5" r="1.5"/>
              </svg>
            </button>
            <button class="dr-btn dr-btn-icon" id="dr-settings" title="设置">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </button>
            <button class="dr-btn dr-btn-close" id="dr-close" title="关闭 (Alt+D)">×</button>
          </div>
        </div>
        
        <div class="dr-content-wrapper">
          <article class="dr-article" style="
            font-size: ${this.settings.fontSize}px;
            font-family: ${this.settings.fontFamily}, serif;
            line-height: ${this.settings.lineHeight};
          ">
            ${this.renderContent()}
          </article>
          
          <aside class="dr-sidebar" id="dr-sidebar">
            <div class="dr-sidebar-section dr-quiz-section">
              <h3 class="dr-sidebar-title">📝 阅读测验</h3>
              <p class="dr-empty-message">点击开始测验,生成 3 道认知压力测试题</p>
              <button class="dr-btn dr-btn-primary" id="dr-start-quiz">📝 开始测验</button>
              <div id="dr-quiz-panel"></div>
            </div>
            <div class="dr-sidebar-section">
              <h3 class="dr-sidebar-title">阅读引导</h3>
              <div class="dr-guides" id="dr-guides">
                <p class="dr-empty-message">点击生成引导问题</p>
              </div>
              <button class="dr-btn dr-btn-primary" id="dr-generate-guides">生成问题</button>
            </div>
            
            <div class="dr-sidebar-section dr-ai-section">
              <h3 class="dr-sidebar-title">AI 助手</h3>
              <div class="dr-chat-container" id="dr-chat-container">
                <div class="dr-chat-messages" id="dr-chat-messages"></div>
                <div class="dr-chat-input-wrapper">
                  <input type="text" class="dr-chat-input" id="dr-chat-input" placeholder="输入问题..." />
                  <button class="dr-btn dr-btn-send" id="dr-send">发送</button>
                </div>
              </div>
            </div>

            <div class="dr-sidebar-section">
              <h3 class="dr-sidebar-title">我的标注</h3>
              <div class="dr-notes-container" id="dr-notes-container">
                <p class="dr-empty-message">选中文字添加高亮或笔记</p>
              </div>
            </div>
          </aside>
        </div>
        
        <div class="dr-footer">
          <div class="dr-progress">
            <div class="dr-progress-bar" id="dr-progress"></div>
          </div>
          <span class="dr-progress-text" id="dr-progress-text">0%</span>
        </div>
      </div>
    `;
  }

  private renderContent(): string {
    const paragraphs = this.content.content.split('\n\n').filter(p => p.trim());
    return paragraphs
      .map((para, index) => `<p class="dr-paragraph" data-index="${index}">${this.escapeHtml(para.trim())}</p>`)
      .join('');
  }

  private bindEvents(): void {
    this.container.querySelector('#dr-close')?.addEventListener('click', () => this.destroy());
    
    this.container.querySelector('#dr-toggle-ai')?.addEventListener('click', () => this.toggleSidebar());
    
    this.container.querySelector('#dr-settings')?.addEventListener('click', () => this.openSettings());
    
    this.container.querySelector('#dr-generate-guides')?.addEventListener('click', () => this.generateGuides());

    // Week 3 T-20: start quiz button
    this.container.querySelector('#dr-start-quiz')?.addEventListener('click', () => this.startQuiz());
    
    const chatInput = this.container.querySelector('#dr-chat-input') as HTMLInputElement;
    const sendBtn = this.container.querySelector('#dr-send') as HTMLButtonElement;
    
    sendBtn?.addEventListener('click', () => this.sendMessage());
    chatInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage();
    });

    const article = this.container.querySelector('.dr-article') as HTMLElement;
    article?.addEventListener('mouseup', () => this.handleTextSelection());
    article?.addEventListener('keydown', (e) => this.handleKeyboardHighlight(e));

    const progressBar = this.container.querySelector('#dr-progress') as HTMLElement;
    const progressText = this.container.querySelector('#dr-progress-text') as HTMLElement;
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const paragraph = entry.target as HTMLElement;
            const index = parseInt(paragraph.dataset.index || '0', 10);
            const total = this.container.querySelectorAll('.dr-paragraph').length;
            const progress = Math.round(((index + 1) / total) * 100);
            progressBar.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;
          }
        });
      },
      { threshold: 0.5 }
    );

    this.container.querySelectorAll('.dr-paragraph').forEach((p) => observer.observe(p));

    document.body.style.overflow = 'hidden';
  }

  private toggleSidebar(): void {
    const sidebar = this.container.querySelector('#dr-sidebar') as HTMLElement;
    sidebar?.classList.toggle('dr-sidebar-collapsed');
  }

  private openSettings(): void {
    chrome.runtime.sendMessage({ action: 'openSettings' });
  }

  private async startQuiz(): Promise<void> {
    const quizBtn = this.container.querySelector('#dr-start-quiz') as HTMLButtonElement;
    const quizPanel = this.container.querySelector('#dr-quiz-panel') as HTMLElement;
    if (!quizBtn || !quizPanel) return;
    quizBtn.disabled = true;
    const originalText = quizBtn.textContent;
    quizBtn.textContent = '出题中...';
    try {
      const { QuizGenerator } = await import('../../lib/quiz-generator');
      const questions = await QuizGenerator.generate(this.content.content);
      if (questions.length === 0) {
        quizPanel.innerHTML = '<p class="dr-empty-message">出题失败,请重试</p>';
        return;
      }
      const { QuizPanel } = await import('../QuizPanel');
      new QuizPanel({
        questions,
        content: this.content,
        container: quizPanel,
      }).mount();
    } catch (err) {
      console.error('[ReaderPanel] startQuiz failed:', err);
      quizPanel.innerHTML = '<p class="dr-empty-message">错误: ' + (err instanceof Error ? err.message : 'unknown') + '</p>';
    } finally {
      quizBtn.disabled = false;
      quizBtn.textContent = originalText || '📝 开始测验';
    }
  }

  private async generateGuides(): Promise<void> {
    const guidesContainer = this.container.querySelector('#dr-guides') as HTMLElement;
    const generateBtn = this.container.querySelector('#dr-generate-guides') as HTMLButtonElement;
    
    generateBtn.disabled = true;
    generateBtn.textContent = '生成中...';
    
    try {
      const response = await chrome.runtime.sendMessage({
        action: 'generateGuides',
        content: this.content.content,
      }) as { success: boolean; guides?: GuideItem[] };
      
      if (response.success && response.guides) {
        this.renderGuides(response.guides, guidesContainer);
      }
    } catch (error) {
      console.error('生成引导问题失败:', error);
      guidesContainer.innerHTML = '<p class="dr-error">生成失败，请重试</p>';
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = '生成问题';
    }
  }

  private renderGuides(guides: GuideItem[], container: HTMLElement): void {
    container.innerHTML = guides
      .map(
        (guide, index) => `
        <div class="dr-guide-item" data-type="${guide.type}">
          <span class="dr-guide-number">${index + 1}</span>
          <span class="dr-guide-text">${this.escapeHtml(guide.question)}</span>
        </div>
      `
      )
      .join('');
  }

  private async sendMessage(): Promise<void> {
    const input = this.container.querySelector('#dr-chat-input') as HTMLInputElement;
    const messagesContainer = this.container.querySelector('#dr-chat-messages') as HTMLElement;
    const message = input.value.trim();
    
    if (!message) return;

    const userMessage = document.createElement('div');
    userMessage.className = 'dr-message dr-message-user';
    userMessage.textContent = message;
    messagesContainer.appendChild(userMessage);

    input.value = '';

    try {
      const response = await chrome.runtime.sendMessage({
        action: 'discussWithAI',
        content: this.content.content,
        question: message,
      }) as { success: boolean; response?: string };

      if (response.success && response.response) {
        const aiMessage = document.createElement('div');
        aiMessage.className = 'dr-message dr-message-ai';
        aiMessage.textContent = response.response;
        messagesContainer.appendChild(aiMessage);
      }
    } catch (error) {
      console.error('AI 对话失败:', error);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private handleTextSelection(): void {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
      return;
    }

    const selectedText = selection.toString().trim();
    if (selectedText.length < 3) {
      return;
    }

    this.showHighlightTooltip(selection, selectedText);
  }

  private handleKeyboardHighlight(event: KeyboardEvent): void {
    if (event.altKey && event.key === 'h') {
      event.preventDefault();
      const selection = window.getSelection();
      if (selection && !selection.isCollapsed) {
        this.addHighlight(selection.toString().trim());
      }
    }
  }

  private showHighlightTooltip(selection: Selection, text: string): void {
    const existingTooltip = this.container.querySelector('.dr-highlight-tooltip');
    if (existingTooltip) {
      existingTooltip.remove();
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    const tooltip = document.createElement('div');
    tooltip.className = 'dr-highlight-tooltip';
    tooltip.innerHTML = `
      <button class="dr-tooltip-btn" id="dr-highlight-btn">高亮</button>
      <button class="dr-tooltip-btn" id="dr-note-btn">添加笔记</button>
      <button class="dr-tooltip-btn" id="dr-cancel-btn">取消</button>
    `;

    tooltip.style.position = 'fixed';
    tooltip.style.left = `${rect.left + rect.width / 2 - 75}px`;
    tooltip.style.top = `${rect.top - 45}px`;
    tooltip.style.zIndex = '10000';

    this.container.appendChild(tooltip);

    tooltip.querySelector('#dr-highlight-btn')?.addEventListener('click', () => {
      this.addHighlight(text);
      tooltip.remove();
    });

    tooltip.querySelector('#dr-note-btn')?.addEventListener('click', () => {
      this.addNote(text);
      tooltip.remove();
    });

    tooltip.querySelector('#dr-cancel-btn')?.addEventListener('click', () => {
      tooltip.remove();
    });

    const closeTooltip = () => {
      tooltip.remove();
      document.removeEventListener('mousedown', outsideClickHandler);
    };

    const outsideClickHandler = (e: MouseEvent) => {
      if (!tooltip.contains(e.target as Node)) {
        closeTooltip();
      }
    };

    setTimeout(() => {
      document.addEventListener('mousedown', outsideClickHandler);
    }, 0);
  }

  private async addHighlight(text: string): Promise<void> {
    const highlight: Highlight = {
      id: crypto.randomUUID(),
      text,
      contentUrl: this.content.url,
      color: 'yellow',
      createdAt: Date.now(),
    };

    this.highlights.push(highlight);
    await this.saveHighlights();
    this.renderHighlights();
    this.showNotification('已添加高亮');
  }

  private async addNote(text: string): Promise<void> {
    const noteText = prompt('请输入笔记内容:');
    if (!noteText || noteText.trim() === '') {
      return;
    }

    const note: Note = {
      id: crypto.randomUUID(),
      text,
      note: noteText.trim(),
      contentUrl: this.content.url,
      createdAt: Date.now(),
    };

    this.notes.push(note);
    await this.saveNotes();
    this.renderNotes();
    this.showNotification('已添加笔记');
  }

  private async saveHighlights(): Promise<void> {
    try {
      await chrome.storage.local.set({ highlights: this.highlights });
    } catch (error) {
      console.error('保存高亮失败:', error);
    }
  }

  private async saveNotes(): Promise<void> {
    try {
      await chrome.storage.local.set({ notes: this.notes });
    } catch (error) {
      console.error('保存笔记失败:', error);
    }
  }

  private renderHighlights(): void {
    const container = this.container.querySelector('#dr-notes-container');
    if (!container) return;

    const allItems: Array<{ id: string; createdAt: number; text: string; note?: string }> = [
      ...this.notes.map((n) => ({ ...n, note: n.note })),
      ...this.highlights.map((h) => ({ ...h, note: undefined })),
    ].sort((a, b) => b.createdAt - a.createdAt);

    if (allItems.length === 0) {
      container.innerHTML = '<p class="dr-empty-message">选中文字添加高亮或笔记</p>';
      return;
    }

    container.innerHTML = allItems
      .slice(0, 20)
      .map((item) => {
        if (item.note) {
          return `
            <div class="dr-note-item" data-id="${item.id}">
              <div class="dr-note-text">"${this.escapeHtml(item.text.slice(0, 50))}${item.text.length > 50 ? '...' : ''}"</div>
              <div class="dr-note-content">${this.escapeHtml(item.note)}</div>
              <div class="dr-note-actions">
                <button class="dr-note-action" data-action="copy">复制</button>
                <button class="dr-note-action" data-action="delete">删除</button>
              </div>
            </div>
          `;
        }
        return `
          <div class="dr-highlight-item" data-id="${item.id}">
            <span class="dr-highlight-color" style="background-color: #fef08a;"></span>
            <span class="dr-highlight-text">"${this.escapeHtml(item.text.slice(0, 50))}${item.text.length > 50 ? '...' : ''}"</span>
            <button class="dr-note-action" data-action="delete">删除</button>
          </div>
        `;
      })
      .join('');

    container.querySelectorAll('.dr-note-item, .dr-highlight-item').forEach((item) => {
      const id = item.getAttribute('data-id');
      item.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
        this.deleteItem(id);
      });
      item.querySelector('[data-action="copy"]')?.addEventListener('click', () => {
        const noteItem = item as HTMLElement;
        const noteContent = noteItem.querySelector('.dr-note-content')?.textContent;
        if (noteContent) {
          navigator.clipboard.writeText(noteContent);
          this.showNotification('已复制到剪贴板');
        }
      });
    });
  }

  private async deleteItem(id: string | null): Promise<void> {
    if (!id) return;

    this.highlights = this.highlights.filter((h) => h.id !== id);
    this.notes = this.notes.filter((n) => n.id !== id);

    await Promise.all([this.saveHighlights(), this.saveNotes()]);
    this.renderHighlights();
    this.showNotification('已删除');
  }

  private renderNotes(): void {
    this.renderHighlights();
  }

  private showNotification(message: string): void {
    const notification = document.createElement('div');
    notification.className = 'dr-toast';
    notification.textContent = message;
    this.container.appendChild(notification);

    setTimeout(() => {
      notification.classList.add('dr-toast-hide');
      setTimeout(() => notification.remove(), 300);
    }, 2000);
  }

  get element(): HTMLElement {
    return this.container;
  }
}
