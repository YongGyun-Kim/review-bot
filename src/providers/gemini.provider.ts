import { GoogleGenerativeAI } from '@google/generative-ai';
import { BaseProvider } from './base.provider';
import { ProviderConfig, ReviewResult } from '../types';

export class GeminiProvider extends BaseProvider {
  name = 'gemini';
  private client: GoogleGenerativeAI;

  constructor(config: ProviderConfig) {
    super(config);
    this.client = new GoogleGenerativeAI(config.apiKey);
  }

  async review(code: string, prompt: string): Promise<ReviewResult> {
    this.validateConfig();

    try {
      const model = this.client.getGenerativeModel({ 
        model: this.config.model || 'gemini-pro',
        generationConfig: {
          maxOutputTokens: this.config.maxTokens || 4000,
          temperature: this.config.temperature || 0.1,
        },
      });

      const fullPrompt = prompt.replace('{{code_diff}}', code);
      const response = await model.generateContent(fullPrompt);
      const text = response.response.text();

      const result = this.parseReviewResponse(text, this.name, this.config.model || 'gemini-pro');
      
      if (response.response.usageMetadata) {
        result.tokens = {
          input: response.response.usageMetadata.promptTokenCount || 0,
          output: response.response.usageMetadata.candidatesTokenCount || 0,
          total: response.response.usageMetadata.totalTokenCount || 0
        };
        
        result.estimatedCost = this.estimateCost(result.tokens.total);
      }
      
      return result;
    } catch (error) {
      console.error('Gemini API error:', error);
      throw new Error(`Gemini review failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  estimateCost(tokens: number): number {
    const model = this.config.model || 'gemini-pro';
    
    let inputRate = 0.00025;
    let outputRate = 0.0005;
    
    if (model.includes('gemini-1.5-pro')) {
      inputRate = 0.00125;
      outputRate = 0.00375;
    }
    
    const inputTokens = Math.ceil(tokens * 0.7);
    const outputTokens = Math.ceil(tokens * 0.3);
    
    const inputCost = (inputTokens / 1000) * inputRate;
    const outputCost = (outputTokens / 1000) * outputRate;
    
    return inputCost + outputCost;
  }
}