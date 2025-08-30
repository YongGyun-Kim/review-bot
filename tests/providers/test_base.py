"""Tests for base AI provider."""

import pytest
from abc import ABC
from unittest.mock import Mock, AsyncMock

from providers.base import BaseAIProvider
from models.types import ReviewConfig, Provider


class TestBaseProvider:
    """Test BaseProvider abstract class."""
    
    def test_base_provider_is_abstract(self):
        """Test that BaseAIProvider cannot be instantiated directly."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        with pytest.raises(TypeError):
            BaseAIProvider(config)
    
    def test_concrete_provider_implementation(self):
        """Test concrete provider implementation."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        class ConcreteProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "test"
            
            async def review_code(self, prompt: str) -> str:
                return "Mock review result"
            
            def estimate_cost(self, text: str) -> dict:
                return {"tokens": 100, "estimated_cost": 0.01}
        
        provider = ConcreteProvider(config)
        
        assert provider.config == config
        assert provider.provider_name == "test"
    
    def test_base_provider_initialization(self):
        """Test base provider initialization with config."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            model="claude-3-sonnet",
            temperature=0.2,
            max_tokens=50000
        )
        
        class TestProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "test"
            
            async def review_code(self, prompt: str) -> str:
                return "test"
            
            def estimate_cost(self, text: str) -> dict:
                return {}
        
        provider = TestProvider(config)
        
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "claude-3-sonnet"
        assert provider.config.temperature == 0.2
        assert provider.config.max_tokens == 50000
    
    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        # Missing review_code implementation
        class IncompleteProvider1(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "incomplete1"
            
            def estimate_cost(self, text: str) -> dict:
                return {}
        
        with pytest.raises(TypeError):
            IncompleteProvider1(config)
        
        # Missing estimate_cost implementation  
        class IncompleteProvider2(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "incomplete2"
            
            async def review_code(self, prompt: str) -> str:
                return "test"
        
        with pytest.raises(TypeError):
            IncompleteProvider2(config)
    
    @pytest.mark.asyncio
    async def test_review_code_interface(self):
        """Test review_code method interface."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        class MockProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "mock"
            
            async def review_code(self, prompt: str) -> str:
                assert isinstance(prompt, str)
                assert len(prompt) > 0
                return f"Review for: {prompt[:20]}..."
            
            def estimate_cost(self, text: str) -> dict:
                return {"tokens": len(text), "estimated_cost": 0.01}
        
        provider = MockProvider(config)
        result = await provider.review_code("Test code to review")
        
        assert isinstance(result, str)
        assert "Review for: Test code to revie..." in result
    
    def test_estimate_cost_interface(self):
        """Test estimate_cost method interface."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        class MockProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "mock"
            
            async def review_code(self, prompt: str) -> str:
                return "test"
            
            def estimate_cost(self, text: str) -> dict:
                word_count = len(text.split())
                token_count = word_count * 1.3  # Rough estimation
                cost = token_count * 0.00001
                
                return {
                    "tokens": int(token_count),
                    "estimated_cost": round(cost, 4),
                    "word_count": word_count
                }
        
        provider = MockProvider(config)
        test_text = "This is a test code snippet for cost estimation"
        
        result = provider.estimate_cost(test_text)
        
        assert isinstance(result, dict)
        assert "tokens" in result
        assert "estimated_cost" in result
        assert isinstance(result["tokens"], int)
        assert isinstance(result["estimated_cost"], (int, float))
        assert result["tokens"] > 0
        assert result["estimated_cost"] >= 0
    
    def test_provider_name_attribute(self):
        """Test that provider_name attribute is accessible."""
        config = ReviewConfig(provider=Provider.CLAUDE, api_key="test")
        
        class NamedProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "custom-provider"
            
            async def review_code(self, prompt: str) -> str:
                return "test"
            
            def estimate_cost(self, text: str) -> dict:
                return {}
        
        provider = NamedProvider(config)
        assert hasattr(provider, 'provider_name')
        assert provider.provider_name == "custom-provider"
    
    def test_config_accessibility(self):
        """Test that config is accessible from provider instance."""
        config = ReviewConfig(
            provider=Provider.CHATGPT,
            api_key="openai-key",
            model="gpt-4",
            temperature=0.5
        )
        
        class ConfigAccessProvider(BaseAIProvider):
            def __init__(self, config):
                super().__init__(config)
                self.provider_name = "config-test"
            
            async def review_code(self, prompt: str) -> str:
                # Use config in implementation
                return f"Review using {self.config.model} at temp {self.config.temperature}"
            
            def estimate_cost(self, text: str) -> dict:
                return {"model": self.config.model}
        
        provider = ConfigAccessProvider(config)
        
        # Config should be accessible
        assert provider.config.provider == Provider.CHATGPT
        assert provider.config.api_key == "openai-key"
        assert provider.config.model == "gpt-4"
        assert provider.config.temperature == 0.5
        
        # Config should be usable in methods
        cost_info = provider.estimate_cost("test")
        assert cost_info["model"] == "gpt-4"