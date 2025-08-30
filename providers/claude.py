"""Claude AI provider using Anthropic API."""

import asyncio
from typing import Optional

import anthropic
from anthropic import AsyncAnthropic

from models.types import ReviewResult, TokenUsage, ProviderConfig
from .base import BaseAIProvider


class ClaudeProvider(BaseAIProvider):
    """Claude AI provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key)
        self.default_model = "claude-3-sonnet-20240229"
    
    @property
    def name(self) -> str:
        return "claude"
    
    async def review(self, code: str, prompt: str) -> ReviewResult:
        """Perform code review using Claude."""
        self.validate_config()
        
        try:
            model = self.config.model or self.default_model
            
            # Replace code placeholder in prompt
            full_prompt = prompt.replace('{{code_diff}}', code)
            
            response = await self.client.messages.create(
                model=model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )
            
            # Extract response content
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            
            # Parse the response
            result = self.parse_review_response(content, self.name, model)
            
            # Add token usage information
            if response.usage:
                result.tokens = TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens
                )
                result.estimated_cost = self.estimate_cost(result.tokens.total_tokens)
            
            return result
            
        except anthropic.APIError as e:
            raise ValueError(f"Claude API error: {e}")
        except Exception as e:
            raise ValueError(f"Claude review failed: {e}")
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for Claude API usage."""
        # Estimate input/output token split (70/30)
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        # Claude 3 Sonnet pricing (per 1K tokens)
        input_cost = (input_tokens / 1000) * 0.003
        output_cost = (output_tokens / 1000) * 0.015
        
        return input_cost + output_cost


# For backward compatibility and easier imports
__all__ = ["ClaudeProvider"]