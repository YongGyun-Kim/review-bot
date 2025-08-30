export interface ReviewConfig {
  provider: 'claude' | 'chatgpt' | 'gemini';
  model?: string;
  apiKey: string;
  promptTemplate?: string;
  autoReview?: {
    onCommit?: boolean;
    onPush?: boolean;
  };
  outputDir?: string;
  excludePatterns?: string[];
  includePatterns?: string[];
  maxFilesPerReview?: number;
  maxTokens?: number;
}

export interface AIProvider {
  name: string;
  review(code: string, prompt: string): Promise<ReviewResult>;
  configure(config: ProviderConfig): void;
  validateConfig(): boolean;
  estimateCost?(tokens: number): number;
}

export interface ProviderConfig {
  apiKey: string;
  model?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface ReviewResult {
  provider: string;
  model: string;
  timestamp: string;
  summary: string;
  strengths: string[];
  issues: Issue[];
  suggestions: Suggestion[];
  rawResponse?: string;
  tokens?: {
    input: number;
    output: number;
    total: number;
  };
  estimatedCost?: number;
}

export interface Issue {
  severity: 'critical' | 'major' | 'minor';
  type: string;
  file?: string;
  line?: number;
  description: string;
  suggestion?: string;
  codeExample?: string;
}

export interface Suggestion {
  id: string;
  title: string;
  description: string;
  files?: string[];
  priority: 'high' | 'medium' | 'low';
  completed?: boolean;
  example?: string;
}

export interface GitDiff {
  files: FileChange[];
  stats: {
    filesChanged: number;
    insertions: number;
    deletions: number;
  };
  commitMessage?: string;
  branch?: string;
}

export interface FileChange {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  patch?: string;
}

export interface PromptTemplate {
  name: string;
  description: string;
  template: string;
  variables: string[];
}

export interface TodoItem extends Suggestion {
  createdAt: string;
  reviewId: string;
  assignee?: string;
  dueDate?: string;
}