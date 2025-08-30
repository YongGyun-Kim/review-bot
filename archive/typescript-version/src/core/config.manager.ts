import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { ReviewConfig } from '../types';

export class ConfigManager {
  private configPath: string;
  private localConfigPath: string;

  constructor() {
    this.configPath = join(homedir(), '.reviewbotrc');
    this.localConfigPath = join(process.cwd(), '.reviewbotrc');
  }

  async loadConfig(): Promise<ReviewConfig> {
    const defaultConfig: ReviewConfig = {
      provider: 'claude',
      apiKey: '',
      promptTemplate: 'default',
      autoReview: {
        onCommit: false,
        onPush: false
      },
      outputDir: './reviews',
      excludePatterns: ['node_modules/**', '*.log', 'dist/**', 'build/**'],
      includePatterns: ['**/*.ts', '**/*.js', '**/*.tsx', '**/*.jsx', '**/*.py', '**/*.go', '**/*.rs'],
      maxFilesPerReview: 50,
      maxTokens: 4000
    };

    try {
      const localConfig = await this.loadLocalConfig();
      const globalConfig = await this.loadGlobalConfig();
      
      const config = { ...defaultConfig, ...globalConfig, ...localConfig };
      
      if (!config.apiKey) {
        config.apiKey = this.getApiKeyFromEnv(config.provider);
      }
      
      return config;
    } catch (error) {
      console.warn('Using default configuration:', error instanceof Error ? error.message : 'Unknown error');
      return defaultConfig;
    }
  }

  private async loadLocalConfig(): Promise<Partial<ReviewConfig>> {
    try {
      const configData = await fs.readFile(this.localConfigPath, 'utf-8');
      return JSON.parse(configData);
    } catch (error) {
      return {};
    }
  }

  private async loadGlobalConfig(): Promise<Partial<ReviewConfig>> {
    try {
      const configData = await fs.readFile(this.configPath, 'utf-8');
      return JSON.parse(configData);
    } catch (error) {
      return {};
    }
  }

  async saveConfig(config: Partial<ReviewConfig>, global = false): Promise<void> {
    const targetPath = global ? this.configPath : this.localConfigPath;
    
    try {
      const existingConfig = global ? await this.loadGlobalConfig() : await this.loadLocalConfig();
      const mergedConfig = { ...existingConfig, ...config };
      
      await fs.writeFile(targetPath, JSON.stringify(mergedConfig, null, 2), 'utf-8');
      console.log(`Configuration saved to ${targetPath}`);
    } catch (error) {
      throw new Error(`Failed to save configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async initConfig(): Promise<void> {
    const exists = await this.configExists();
    
    if (exists) {
      console.log('Configuration file already exists');
      return;
    }

    const defaultConfig: ReviewConfig = {
      provider: 'claude',
      apiKey: '',
      promptTemplate: 'default',
      autoReview: {
        onCommit: false,
        onPush: false
      },
      outputDir: './reviews',
      excludePatterns: ['node_modules/**', '*.log', 'dist/**', 'build/**'],
      includePatterns: ['**/*.ts', '**/*.js', '**/*.tsx', '**/*.jsx', '**/*.py', '**/*.go', '**/*.rs'],
      maxFilesPerReview: 50,
      maxTokens: 4000
    };

    await this.saveConfig(defaultConfig, false);
    console.log('Configuration initialized successfully');
  }

  private async configExists(): Promise<boolean> {
    try {
      await fs.access(this.localConfigPath);
      return true;
    } catch {
      return false;
    }
  }

  private getApiKeyFromEnv(provider: string): string {
    const envMap = {
      claude: 'ANTHROPIC_API_KEY',
      chatgpt: 'OPENAI_API_KEY',
      gemini: 'GOOGLE_API_KEY'
    };

    const envKey = envMap[provider as keyof typeof envMap];
    return process.env[envKey] || '';
  }

  validateConfig(config: ReviewConfig): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!config.provider) {
      errors.push('Provider is required');
    }

    if (!config.apiKey) {
      errors.push(`API key is required for ${config.provider}`);
    }

    if (!config.outputDir) {
      errors.push('Output directory is required');
    }

    if (config.maxFilesPerReview && config.maxFilesPerReview <= 0) {
      errors.push('Max files per review must be greater than 0');
    }

    if (config.maxTokens && config.maxTokens <= 0) {
      errors.push('Max tokens must be greater than 0');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  async getConfigPath(global = false): Promise<string> {
    return global ? this.configPath : this.localConfigPath;
  }
}