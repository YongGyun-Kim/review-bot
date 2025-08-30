import { promises as fs } from 'fs';
import { join } from 'path';
import { PromptTemplate, GitDiff } from '../types';

export class PromptManager {
  private promptsDir: string;

  constructor(promptsDir = './prompts') {
    this.promptsDir = promptsDir;
  }

  async loadPrompt(templateName: string): Promise<string> {
    const promptPath = join(this.promptsDir, `${templateName}.md`);
    
    try {
      return await fs.readFile(promptPath, 'utf-8');
    } catch (error) {
      if (templateName !== 'default') {
        console.warn(`Prompt template '${templateName}' not found, falling back to default`);
        return this.loadPrompt('default');
      }
      
      throw new Error(`Default prompt template not found: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async getAvailablePrompts(): Promise<PromptTemplate[]> {
    try {
      const files = await fs.readdir(this.promptsDir);
      const prompts: PromptTemplate[] = [];

      for (const file of files) {
        if (file.endsWith('.md')) {
          const name = file.replace('.md', '');
          const content = await fs.readFile(join(this.promptsDir, file), 'utf-8');
          const description = this.extractDescription(content);
          const variables = this.extractVariables(content);

          prompts.push({
            name,
            description,
            template: content,
            variables
          });
        }
      }

      return prompts;
    } catch (error) {
      console.error('Error loading prompts:', error);
      return [];
    }
  }

  async createPrompt(name: string, content: string): Promise<void> {
    const promptPath = join(this.promptsDir, `${name}.md`);
    
    try {
      await fs.writeFile(promptPath, content, 'utf-8');
      console.log(`Prompt template '${name}' created successfully`);
    } catch (error) {
      throw new Error(`Failed to create prompt template: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private extractDescription(content: string): string {
    const lines = content.split('\n');
    const firstLine = lines[0];
    
    if (firstLine.startsWith('#')) {
      return firstLine.replace(/^#\s*/, '');
    }
    
    return 'Custom prompt template';
  }

  private extractVariables(content: string): string[] {
    const variables: string[] = [];
    const regex = /\{\{([^}]+)\}\}/g;
    let match;

    while ((match = regex.exec(content)) !== null) {
      if (!variables.includes(match[1])) {
        variables.push(match[1]);
      }
    }

    return variables;
  }

  populatePrompt(template: string, data: {
    gitDiff: GitDiff;
    codeDiff: string;
    [key: string]: any;
  }): string {
    let populatedPrompt = template;

    const replacements = {
      '{{files_changed}}': data.gitDiff.stats.filesChanged.toString(),
      '{{lines_added}}': data.gitDiff.stats.insertions.toString(),
      '{{lines_removed}}': data.gitDiff.stats.deletions.toString(),
      '{{commit_message}}': data.gitDiff.commitMessage || 'No commit message',
      '{{code_diff}}': data.codeDiff,
      '{{branch}}': data.gitDiff.branch || 'unknown',
      '{{files_list}}': data.gitDiff.files.map(f => f.path).join(', ')
    };

    Object.entries(replacements).forEach(([placeholder, value]) => {
      populatedPrompt = populatedPrompt.replace(new RegExp(placeholder, 'g'), value);
    });

    Object.entries(data).forEach(([key, value]) => {
      if (typeof value === 'string') {
        const placeholder = `{{${key}}}`;
        populatedPrompt = populatedPrompt.replace(new RegExp(placeholder, 'g'), value);
      }
    });

    return populatedPrompt;
  }

  validatePrompt(template: string): { valid: boolean; missingVariables: string[]; errors: string[] } {
    const errors: string[] = [];
    const requiredVariables = ['{{code_diff}}'];
    const foundVariables = this.extractVariables(template);
    
    const missingVariables = requiredVariables.filter(
      variable => !template.includes(variable)
    );

    if (template.trim().length === 0) {
      errors.push('Prompt template cannot be empty');
    }

    if (missingVariables.length > 0) {
      errors.push(`Missing required variables: ${missingVariables.join(', ')}`);
    }

    return {
      valid: errors.length === 0 && missingVariables.length === 0,
      missingVariables,
      errors
    };
  }
}