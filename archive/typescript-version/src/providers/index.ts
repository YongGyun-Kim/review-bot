export { BaseProvider } from './base.provider';
export { ClaudeProvider } from './claude.provider';
export { ChatGPTProvider } from './chatgpt.provider';
export { GeminiProvider } from './gemini.provider';

import { ClaudeProvider } from './claude.provider';
import { ChatGPTProvider } from './chatgpt.provider';
import { GeminiProvider } from './gemini.provider';
import { AIProvider, ProviderConfig } from '../types';

export function createProvider(providerName: string, config: ProviderConfig): AIProvider {
  switch (providerName.toLowerCase()) {
    case 'claude':
      return new ClaudeProvider(config);
    case 'chatgpt':
      return new ChatGPTProvider(config);
    case 'gemini':
      return new GeminiProvider(config);
    default:
      throw new Error(`Unknown provider: ${providerName}`);
  }
}

export const AVAILABLE_PROVIDERS = ['claude', 'chatgpt', 'gemini'] as const;
export const DEFAULT_MODELS = {
  claude: 'claude-3-sonnet-20240229',
  chatgpt: 'gpt-4',
  gemini: 'gemini-pro'
} as const;