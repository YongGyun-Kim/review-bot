"""Tests for Claude provider."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import json

from providers.claude import ClaudeProvider
from models.types import ReviewConfig, Provider


class TestClaudeProvider:
    """Test ClaudeProvider functionality."""
    
    def test_claude_provider_initialization(self):
        """Test Claude provider initialization."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=100000
        )
        
        provider = ClaudeProvider(config)
        
        assert provider.provider_name == "claude"
        assert provider.config == config
        assert hasattr(provider, 'client')
    
    def test_claude_provider_default_model(self):
        """Test Claude provider with default model."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        # Should use default model when none specified
        assert provider.model == "claude-3-5-sonnet-20241022"
    
    def test_claude_provider_custom_model(self):
        """Test Claude provider with custom model."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            model="claude-3-haiku-20240307"
        )
        
        provider = ClaudeProvider(config)
        
        assert provider.model == "claude-3-haiku-20240307"
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_review_code_success(self, mock_anthropic):
        """Test successful code review with Claude."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=50000
        )
        
        # Mock response
        mock_message = Mock()
        mock_message.content = [Mock(text="This code looks good. No issues found.")]
        mock_message.usage = Mock(input_tokens=100, output_tokens=50)
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        prompt = "Review this Python code:\n\ndef hello():\n    print('Hello world')"
        result = await provider.review_code(prompt)
        
        assert result == "This code looks good. No issues found."
        
        # Verify API call
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50000,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_review_code_api_error(self, mock_anthropic):
        """Test API error handling during code review."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        # Mock API error
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        with pytest.raises(Exception) as exc_info:
            await provider.review_code("test prompt")
        
        assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_review_code_empty_response(self, mock_anthropic):
        """Test handling of empty API response."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        # Mock empty response
        mock_message = Mock()
        mock_message.content = []
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        result = await provider.review_code("test prompt")
        
        assert result == ""
    
    def test_estimate_cost_basic(self):
        """Test basic cost estimation."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        test_text = "This is a test prompt for cost estimation."
        cost_info = provider.estimate_cost(test_text)
        
        assert "tokens" in cost_info
        assert "estimated_cost" in cost_info
        assert cost_info["tokens"] > 0
        assert cost_info["estimated_cost"] > 0
        assert isinstance(cost_info["tokens"], int)
        assert isinstance(cost_info["estimated_cost"], float)
    
    def test_estimate_cost_empty_text(self):
        """Test cost estimation with empty text."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        cost_info = provider.estimate_cost("")
        
        assert cost_info["tokens"] == 0
        assert cost_info["estimated_cost"] == 0.0
    
    def test_estimate_cost_long_text(self):
        """Test cost estimation with long text."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        # Create long text
        long_text = "word " * 1000  # ~1000 words
        cost_info = provider.estimate_cost(long_text)
        
        assert cost_info["tokens"] > 1000  # Should be more than word count
        assert cost_info["estimated_cost"] > 0.01  # Should have meaningful cost
    
    def test_estimate_cost_different_models(self):
        """Test cost estimation varies by model."""
        base_config = {
            "provider": Provider.CLAUDE,
            "api_key": "test-key"
        }
        
        sonnet_config = ReviewConfig(**base_config, model="claude-3-5-sonnet-20241022")
        haiku_config = ReviewConfig(**base_config, model="claude-3-haiku-20240307")
        
        sonnet_provider = ClaudeProvider(sonnet_config)
        haiku_provider = ClaudeProvider(haiku_config)
        
        test_text = "This is a test prompt for cost estimation."
        
        sonnet_cost = sonnet_provider.estimate_cost(test_text)
        haiku_cost = haiku_provider.estimate_cost(test_text)
        
        # Sonnet should be more expensive than Haiku
        assert sonnet_cost["estimated_cost"] > haiku_cost["estimated_cost"]
        assert sonnet_cost["tokens"] == haiku_cost["tokens"]  # Same token count
    
    def test_count_tokens_approximation(self):
        """Test token counting approximation."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        # Test various text samples
        assert provider._count_tokens("") == 0
        assert provider._count_tokens("hello") >= 1
        assert provider._count_tokens("hello world") >= 2
        
        # Longer text should have more tokens
        short_text = "hello world"
        long_text = "hello world " * 10
        
        short_tokens = provider._count_tokens(short_text)
        long_tokens = provider._count_tokens(long_text)
        
        assert long_tokens > short_tokens * 5  # Should be roughly 10x
    
    def test_get_model_cost_rates(self):
        """Test model-specific cost rates."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        # Test known models
        sonnet_rate = provider._get_model_cost_rates("claude-3-5-sonnet-20241022")
        haiku_rate = provider._get_model_cost_rates("claude-3-haiku-20240307")
        opus_rate = provider._get_model_cost_rates("claude-3-opus-20240229")
        
        assert sonnet_rate["input"] > 0
        assert sonnet_rate["output"] > 0
        assert haiku_rate["input"] < sonnet_rate["input"]  # Haiku cheaper
        assert opus_rate["input"] > sonnet_rate["input"]   # Opus more expensive
    
    def test_get_model_cost_rates_unknown(self):
        """Test cost rates for unknown model."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        provider = ClaudeProvider(config)
        
        # Unknown model should use default rates
        unknown_rate = provider._get_model_cost_rates("unknown-model")
        sonnet_rate = provider._get_model_cost_rates("claude-3-5-sonnet-20241022")
        
        assert unknown_rate == sonnet_rate
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_system_message_handling(self, mock_anthropic):
        """Test system message handling in Claude API calls."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key"
        )
        
        mock_message = Mock()
        mock_message.content = [Mock(text="Review response")]
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        # Test with system-like prompt
        system_prompt = "You are a code reviewer. Review this code: def test(): pass"
        await provider.review_code(system_prompt)
        
        # Should still use user role (Claude API doesn't use system role the same way)
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["messages"][0]["role"] == "user"
        assert call_args[1]["messages"][0]["content"] == system_prompt
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_max_tokens_configuration(self, mock_anthropic):
        """Test max tokens configuration is passed to API."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            max_tokens=75000
        )
        
        mock_message = Mock()
        mock_message.content = [Mock(text="Response")]
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        await provider.review_code("test prompt")
        
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["max_tokens"] == 75000
    
    @pytest.mark.asyncio
    @patch('anthropic.AsyncAnthropic')
    async def test_temperature_configuration(self, mock_anthropic):
        """Test temperature configuration is passed to API."""
        config = ReviewConfig(
            provider=Provider.CLAUDE,
            api_key="test-key",
            temperature=0.3
        )
        
        mock_message = Mock()
        mock_message.content = [Mock(text="Response")]
        
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(config)
        
        await provider.review_code("test prompt")
        
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["temperature"] == 0.3