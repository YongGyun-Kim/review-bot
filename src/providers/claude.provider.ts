import Anthropic from '@anthropic-ai/sdk';
import { BaseProvider } from './base.provider';
import { ProviderConfig, ReviewResult } from '../types';

export class ClaudeProvider extends BaseProvider {
  name = 'claude';
  private client: Anthropic;

  constructor(config: ProviderConfig) {
    super(config);
    this.client = new Anthropic({
      apiKey: config.apiKey,
    });
  }

  async review(code: string, prompt: string): Promise<ReviewResult> {
    this.validateConfig();

    try {
      const response = await this.client.messages.create({
        model: this.config.model || 'claude-3-sonnet-20240229',
        max_tokens: this.config.maxTokens || 4000,
        temperature: this.config.temperature || 0.1,
        messages: [
          {
            role: 'user',
            content: prompt.replace('{{code_diff}}', code)
          }
        ]
      });

      const content = response.content[0];
      const text = content.type === 'text' ? content.text : '';

      const result = this.parseReviewResponse(text, this.name, this.config.model || 'claude-3-sonnet-20240229');
      
      result.tokens = {
        input: response.usage.input_tokens,
        output: response.usage.output_tokens,
        total: response.usage.input_tokens + response.usage.output_tokens
      };
      
      result.estimatedCost = this.estimateCost(result.tokens.total);
      
      return result;
    } catch (error) {
      console.error('Claude API error:', error);
      throw new Error(`Claude review failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  estimateCost(tokens: number): number {
    const inputTokens = Math.ceil(tokens * 0.7);
    const outputTokens = Math.ceil(tokens * 0.3);
    
    const inputCost = (inputTokens / 1000) * 0.003;
    const outputCost = (outputTokens / 1000) * 0.015;
    
    return inputCost + outputCost;
  }
}