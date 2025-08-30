"""Google Gemini provider implementation."""

from typing import Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from models.types import ReviewResult, TokenUsage, ProviderConfig
from .base import BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.default_model = "gemini-pro"
    
    @property
    def name(self) -> str:
        return "gemini"
    
    async def review(self, code: str, prompt: str) -> ReviewResult:
        """Perform code review using Gemini."""
        self.validate_config()
        
        try:
            model_name = self.config.model or self.default_model
            
            # Configure the model
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            # Replace code placeholder in prompt
            full_prompt = prompt.replace('{{code_diff}}', code)
            
            # Generate response
            response = await model.generate_content_async(full_prompt)
            
            # Extract response content
            content = ""
            if response.text:
                content = response.text
            
            # Parse the response
            result = self.parse_review_response(content, self.name, model_name)
            
            # Add token usage information if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                result.tokens = TokenUsage(
                    input_tokens=getattr(usage, 'prompt_token_count', 0),
                    output_tokens=getattr(usage, 'candidates_token_count', 0),
                    total_tokens=getattr(usage, 'total_token_count', 0)
                )
                result.estimated_cost = self.estimate_cost(result.tokens.total_tokens)
            
            return result
            
        except Exception as e:
            raise ValueError(f"Gemini review failed: {e}")
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for Gemini API usage."""
        model = self.config.model or self.default_model
        
        # Pricing per 1K tokens (as of 2024)
        if "gemini-1.5-pro" in model:
            input_rate = 0.00125
            output_rate = 0.00375
        elif "gemini-pro" in model:
            input_rate = 0.00025
            output_rate = 0.0005
        else:
            # Default to gemini-pro pricing
            input_rate = 0.00025
            output_rate = 0.0005
        
        # Estimate input/output token split (70/30)
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        input_cost = (input_tokens / 1000) * input_rate
        output_cost = (output_tokens / 1000) * output_rate
        
        return input_cost + output_cost


# For backward compatibility and easier imports
__all__ = ["GeminiProvider"]