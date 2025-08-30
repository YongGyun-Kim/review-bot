import { promises as fs } from 'fs';
import { join, dirname } from 'path';
import { ReviewResult, ReviewConfig, GitDiff, TodoItem } from '../types';
import { createProvider } from '../providers';
import { GitManager } from './git.manager';
import { PromptManager } from './prompt.manager';
import { ConfigManager } from './config.manager';

export class ReviewManager {
  private gitManager: GitManager;
  private promptManager: PromptManager;
  private configManager: ConfigManager;

  constructor() {
    this.gitManager = new GitManager();
    this.promptManager = new PromptManager();
    this.configManager = new ConfigManager();
  }

  async runReview(options: {
    staged?: boolean;
    commitHash?: string;
    promptTemplate?: string;
    outputFormat?: 'markdown' | 'json';
  } = {}): Promise<ReviewResult> {
    const config = await this.configManager.loadConfig();
    const validation = this.configManager.validateConfig(config);
    
    if (!validation.valid) {
      throw new Error(`Invalid configuration: ${validation.errors.join(', ')}`);
    }

    const isGitRepo = await this.gitManager.isGitRepository();
    if (!isGitRepo) {
      throw new Error('Not a git repository');
    }

    const gitDiff = options.commitHash 
      ? await this.gitManager.getCommitDiff(options.commitHash)
      : options.staged 
        ? await this.gitManager.getStagedDiff()
        : await this.gitManager.getWorkingDiff();

    if (gitDiff.files.length === 0) {
      throw new Error('No changes found to review');
    }

    console.log(`Reviewing ${gitDiff.files.length} files with ${gitDiff.stats.insertions} additions and ${gitDiff.stats.deletions} deletions`);

    const prompt = await this.promptManager.loadPrompt(
      options.promptTemplate || config.promptTemplate || 'default'
    );

    const codeDiff = await this.gitManager.formatDiffForReview();
    const populatedPrompt = this.promptManager.populatePrompt(prompt, {
      gitDiff,
      codeDiff
    });

    const provider = createProvider(config.provider, {
      apiKey: config.apiKey,
      model: config.model,
      maxTokens: config.maxTokens
    });

    console.log(`Running review with ${config.provider}${config.model ? ` (${config.model})` : ''}...`);
    
    const result = await provider.review(codeDiff, populatedPrompt);
    
    await this.saveReviewResult(result, config.outputDir || './reviews');
    
    if (result.suggestions.length > 0) {
      await this.saveTodoItems(result.suggestions, result.timestamp, config.outputDir || './reviews');
    }

    return result;
  }

  private async saveReviewResult(result: ReviewResult, outputDir: string): Promise<void> {
    await this.ensureDirectoryExists(outputDir);

    const timestamp = new Date(result.timestamp);
    const filename = `review-${timestamp.toISOString().replace(/[:.]/g, '-')}.md`;
    const filepath = join(outputDir, filename);

    const markdown = this.formatReviewAsMarkdown(result);
    
    await fs.writeFile(filepath, markdown, 'utf-8');
    console.log(`Review saved to: ${filepath}`);
  }

  private formatReviewAsMarkdown(result: ReviewResult): string {
    const timestamp = new Date(result.timestamp);
    
    let markdown = `# Code Review - ${timestamp.toLocaleDateString()}\n\n`;
    
    markdown += `**Provider:** ${result.provider}\n`;
    markdown += `**Model:** ${result.model}\n`;
    markdown += `**Timestamp:** ${result.timestamp}\n`;
    
    if (result.tokens) {
      markdown += `**Tokens:** ${result.tokens.total} (${result.tokens.input} input, ${result.tokens.output} output)\n`;
    }
    
    if (result.estimatedCost) {
      markdown += `**Estimated Cost:** $${result.estimatedCost.toFixed(4)}\n`;
    }
    
    markdown += '\n---\n\n';

    if (result.summary) {
      markdown += `## Summary\n\n${result.summary}\n\n`;
    }

    if (result.strengths.length > 0) {
      markdown += `## Strengths\n\n`;
      result.strengths.forEach(strength => {
        markdown += `- ${strength}\n`;
      });
      markdown += '\n';
    }

    if (result.issues.length > 0) {
      markdown += `## Issues Found\n\n`;
      
      const critical = result.issues.filter(i => i.severity === 'critical');
      const major = result.issues.filter(i => i.severity === 'major');
      const minor = result.issues.filter(i => i.severity === 'minor');

      if (critical.length > 0) {
        markdown += `### 🔴 Critical Issues\n\n`;
        critical.forEach(issue => {
          markdown += `**${issue.type}**${issue.file ? ` (${issue.file}:${issue.line || '?'})` : ''}\n\n`;
          markdown += `${issue.description}\n\n`;
          if (issue.suggestion) {
            markdown += `*Suggestion:* ${issue.suggestion}\n\n`;
          }
          if (issue.codeExample) {
            markdown += `\`\`\`\n${issue.codeExample}\n\`\`\`\n\n`;
          }
        });
      }

      if (major.length > 0) {
        markdown += `### 🟡 Major Issues\n\n`;
        major.forEach(issue => {
          markdown += `**${issue.type}**${issue.file ? ` (${issue.file}:${issue.line || '?'})` : ''}\n\n`;
          markdown += `${issue.description}\n\n`;
          if (issue.suggestion) {
            markdown += `*Suggestion:* ${issue.suggestion}\n\n`;
          }
          if (issue.codeExample) {
            markdown += `\`\`\`\n${issue.codeExample}\n\`\`\`\n\n`;
          }
        });
      }

      if (minor.length > 0) {
        markdown += `### 🟢 Minor Issues\n\n`;
        minor.forEach(issue => {
          markdown += `**${issue.type}**${issue.file ? ` (${issue.file}:${issue.line || '?'})` : ''}\n\n`;
          markdown += `${issue.description}\n\n`;
          if (issue.suggestion) {
            markdown += `*Suggestion:* ${issue.suggestion}\n\n`;
          }
          if (issue.codeExample) {
            markdown += `\`\`\`\n${issue.codeExample}\n\`\`\`\n\n`;
          }
        });
      }
    }

    if (result.suggestions.length > 0) {
      markdown += `## Improvement Suggestions\n\n`;
      result.suggestions.forEach((suggestion, index) => {
        markdown += `### ${index + 1}. ${suggestion.title}\n\n`;
        markdown += `**Priority:** ${suggestion.priority}\n\n`;
        markdown += `${suggestion.description}\n\n`;
        if (suggestion.files && suggestion.files.length > 0) {
          markdown += `**Files:** ${suggestion.files.join(', ')}\n\n`;
        }
        if (suggestion.example) {
          markdown += `**Example:**\n\`\`\`\n${suggestion.example}\n\`\`\`\n\n`;
        }
      });
    }

    return markdown;
  }

  private async saveTodoItems(suggestions: any[], reviewId: string, outputDir: string): Promise<void> {
    const todoDir = join(outputDir, 'todo');
    await this.ensureDirectoryExists(todoDir);

    const todoItems: TodoItem[] = suggestions.map(suggestion => ({
      ...suggestion,
      createdAt: new Date().toISOString(),
      reviewId
    }));

    const filename = `todo-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    const filepath = join(todoDir, filename);

    await fs.writeFile(filepath, JSON.stringify(todoItems, null, 2), 'utf-8');
    console.log(`TODO items saved to: ${filepath}`);
  }

  async getTodoItems(outputDir = './reviews'): Promise<TodoItem[]> {
    const todoDir = join(outputDir, 'todo');
    
    try {
      const files = await fs.readdir(todoDir);
      const todoFiles = files.filter(f => f.startsWith('todo-') && f.endsWith('.json'));
      
      const allTodos: TodoItem[] = [];
      
      for (const file of todoFiles) {
        const filepath = join(todoDir, file);
        const content = await fs.readFile(filepath, 'utf-8');
        const todos = JSON.parse(content) as TodoItem[];
        allTodos.push(...todos);
      }
      
      return allTodos.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    } catch (error) {
      console.warn('No TODO items found or error reading todos:', error);
      return [];
    }
  }

  async markTodoCompleted(todoId: string, outputDir = './reviews'): Promise<void> {
    const todos = await this.getTodoItems(outputDir);
    const todo = todos.find(t => t.id === todoId);
    
    if (!todo) {
      throw new Error(`TODO item with id '${todoId}' not found`);
    }
    
    todo.completed = true;
    
    const todoDir = join(outputDir, 'todo');
    const filename = `todo-${todo.createdAt.replace(/[:.]/g, '-')}.json`;
    const filepath = join(todoDir, filename);
    
    const todosInFile = todos.filter(t => t.createdAt === todo.createdAt);
    await fs.writeFile(filepath, JSON.stringify(todosInFile, null, 2), 'utf-8');
    
    console.log(`TODO item '${todoId}' marked as completed`);
  }

  private async ensureDirectoryExists(dir: string): Promise<void> {
    try {
      await fs.mkdir(dir, { recursive: true });
    } catch (error) {
      if ((error as any).code !== 'EEXIST') {
        throw error;
      }
    }
  }
}