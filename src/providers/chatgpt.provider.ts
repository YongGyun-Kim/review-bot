import OpenAI from 'openai';
import { BaseProvider } from './base.provider';
import { ProviderConfig, ReviewResult } from '../types';

export class ChatGPTProvider extends BaseProvider {
  name = 'chatgpt';
  private client: OpenAI;

  constructor(config: ProviderConfig) {
    super(config);
    this.client = new OpenAI({
      apiKey: config.apiKey,
    });
  }

  async review(code: string, prompt: string): Promise<ReviewResult> {
    this.validateConfig();

    try {
      const response = await this.client.chat.completions.create({
        model: this.config.model || 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert code reviewer. Provide detailed, constructive feedback on code quality, security, performance, and best practices.'
          },
          {
            role: 'user',
            content: prompt.replace('{{code_diff}}', code)
          }
        ],
        max_tokens: this.config.maxTokens || 4000,
        temperature: this.config.temperature || 0.1,
      });

      const text = response.choices[0]?.message?.content || '';
      const result = this.parseReviewResponse(text, this.name, this.config.model || 'gpt-4');
      
      if (response.usage) {
        result.tokens = {
          input: response.usage.prompt_tokens,
          output: response.usage.completion_tokens,
          total: response.usage.total_tokens
        };
        
        result.estimatedCost = this.estimateCost(result.tokens.total);
      }
      
      return result;
    } catch (error) {
      console.error('OpenAI API error:', error);
      throw new Error(`ChatGPT review failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  estimateCost(tokens: number): number {
    const model = this.config.model || 'gpt-4';
    
    let inputRate = 0.03;
    let outputRate = 0.06;
    
    if (model.includes('gpt-4-turbo')) {
      inputRate = 0.01;
      outputRate = 0.03;
    } else if (model.includes('gpt-3.5-turbo')) {
      inputRate = 0.0015;
      outputRate = 0.002;
    }
    
    const inputTokens = Math.ceil(tokens * 0.7);
    const outputTokens = Math.ceil(tokens * 0.3);
    
    const inputCost = (inputTokens / 1000) * inputRate;
    const outputCost = (outputTokens / 1000) * outputRate;
    
    return inputCost + outputCost;
  }
}