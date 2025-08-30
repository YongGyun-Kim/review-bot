import { AIProvider, ProviderConfig, ReviewResult } from '../types';

export abstract class BaseProvider implements AIProvider {
  protected config: ProviderConfig;
  abstract name: string;

  constructor(config: ProviderConfig) {
    this.config = config;
  }

  abstract review(code: string, prompt: string): Promise<ReviewResult>;
  
  configure(config: ProviderConfig): void {
    this.config = { ...this.config, ...config };
  }

  validateConfig(): boolean {
    if (!this.config.apiKey) {
      throw new Error(`API key is required for ${this.name}`);
    }
    return true;
  }

  protected parseReviewResponse(response: string, provider: string, model: string): ReviewResult {
    const timestamp = new Date().toISOString();
    
    const result: ReviewResult = {
      provider,
      model,
      timestamp,
      summary: '',
      strengths: [],
      issues: [],
      suggestions: [],
      rawResponse: response
    };

    try {
      const sections = response.split(/#{2,3}\s+/);
      
      sections.forEach(section => {
        const lines = section.trim().split('\n');
        const title = lines[0]?.toLowerCase();
        
        if (title?.includes('summary')) {
          result.summary = lines.slice(1).join('\n').trim();
        } else if (title?.includes('strength')) {
          result.strengths = this.extractListItems(lines.slice(1).join('\n'));
        } else if (title?.includes('issue')) {
          result.issues = this.parseIssues(lines.slice(1).join('\n'));
        } else if (title?.includes('suggestion') || title?.includes('improvement')) {
          result.suggestions = this.parseSuggestions(lines.slice(1).join('\n'));
        }
      });
    } catch (error) {
      console.error('Error parsing review response:', error);
    }

    return result;
  }

  private extractListItems(text: string): string[] {
    const items: string[] = [];
    const lines = text.split('\n');
    
    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.match(/^[-*•]\s+/) || trimmed.match(/^\d+\.\s+/)) {
        items.push(trimmed.replace(/^[-*•]\s+/, '').replace(/^\d+\.\s+/, ''));
      }
    });
    
    return items;
  }

  private parseIssues(text: string): any[] {
    const issues: any[] = [];
    const lines = text.split('\n');
    let currentIssue: any = null;
    
    lines.forEach(line => {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('🔴') || trimmed.includes('Critical')) {
        if (currentIssue) issues.push(currentIssue);
        currentIssue = {
          severity: 'critical',
          type: 'general',
          description: trimmed.replace(/^🔴\s*\*?\*?Critical\*?\*?:?\s*/i, '')
        };
      } else if (trimmed.startsWith('🟡') || trimmed.includes('Major')) {
        if (currentIssue) issues.push(currentIssue);
        currentIssue = {
          severity: 'major',
          type: 'general',
          description: trimmed.replace(/^🟡\s*\*?\*?Major\*?\*?:?\s*/i, '')
        };
      } else if (trimmed.startsWith('🟢') || trimmed.includes('Minor')) {
        if (currentIssue) issues.push(currentIssue);
        currentIssue = {
          severity: 'minor',
          type: 'general',
          description: trimmed.replace(/^🟢\s*\*?\*?Minor\*?\*?:?\s*/i, '')
        };
      } else if (currentIssue && trimmed) {
        currentIssue.description += ' ' + trimmed;
      }
    });
    
    if (currentIssue) issues.push(currentIssue);
    return issues;
  }

  private parseSuggestions(text: string): any[] {
    const suggestions: any[] = [];
    const items = this.extractListItems(text);
    
    items.forEach((item, index) => {
      suggestions.push({
        id: `suggestion-${index + 1}`,
        title: item.split('.')[0] || item,
        description: item,
        priority: 'medium',
        completed: false
      });
    });
    
    return suggestions;
  }

  estimateCost?(tokens: number): number {
    return 0;
  }
}