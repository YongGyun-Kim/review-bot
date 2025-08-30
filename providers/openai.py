"""OpenAI (ChatGPT) provider implementation."""

from typing import Optional

from openai import AsyncOpenAI

from models.types import ReviewResult, TokenUsage, ProviderConfig
from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """OpenAI ChatGPT provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.default_model = "gpt-4"
    
    @property
    def name(self) -> str:
        return "chatgpt"
    
    async def review(self, code: str, prompt: str) -> ReviewResult:
        """Perform code review using OpenAI."""
        self.validate_config()
        
        try:
            model = self.config.model or self.default_model
            
            # Replace code placeholder in prompt
            full_prompt = prompt.replace('{{code_diff}}', code)
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Provide detailed, constructive feedback on code quality, security, performance, and best practices."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # Extract response content
            content = ""
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    content = choice.message.content
            
            # Parse the response
            result = self.parse_review_response(content, self.name, model)
            
            # Add token usage information
            if response.usage:
                result.tokens = TokenUsage(
                    input_tokens=response.usage.prompt_tokens or 0,
                    output_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0
                )
                result.estimated_cost = self.estimate_cost(result.tokens.total_tokens)
            
            return result
            
        except Exception as e:
            raise ValueError(f"OpenAI review failed: {e}")
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for OpenAI API usage."""
        model = self.config.model or self.default_model
        
        # Pricing per 1K tokens (as of 2024)
        if "gpt-4-turbo" in model:
            input_rate = 0.01
            output_rate = 0.03
        elif "gpt-4" in model:
            input_rate = 0.03
            output_rate = 0.06
        elif "gpt-3.5-turbo" in model:
            input_rate = 0.0015
            output_rate = 0.002
        else:
            # Default to GPT-4 pricing
            input_rate = 0.03
            output_rate = 0.06
        
        # Estimate input/output token split (70/30)
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate
        
        return input_cost + output_cost


# For backward compatibility and easier imports
__all__ = ["OpenAIProvider"]