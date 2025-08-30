"""AI providers for code review."""

from .base import BaseAIProvider
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider

from models.types import Provider, ProviderConfig, AIProvider


def create_provider(provider_name: str, config: ProviderConfig) -> AIProvider:
    """Create an AI provider instance.
    
    Args:
        provider_name: Name of the provider ('claude', 'chatgpt', 'gemini')
        config: Provider configuration
        
    Returns:
        Configured AI provider instance
        
    Raises:
        ValueError: If provider name is unknown
    """
    providers = {
        Provider.CLAUDE: ClaudeProvider,
        Provider.CHATGPT: OpenAIProvider,
        Provider.GEMINI: GeminiProvider,
    }
    
    try:
        provider_enum = Provider(provider_name.lower())
    except ValueError:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    provider_class = providers[provider_enum]
    return provider_class(config)


# Available providers
AVAILABLE_PROVIDERS = [provider.value for provider in Provider]

# Default models for each provider
DEFAULT_MODELS = {
    Provider.CLAUDE: "claude-3-sonnet-20240229",
    Provider.CHATGPT: "gpt-4",
    Provider.GEMINI: "gemini-pro",
}


__all__ = [
    "BaseAIProvider",
    "ClaudeProvider", 
    "OpenAIProvider",
    "GeminiProvider",
    "create_provider",
    "AVAILABLE_PROVIDERS",
    "DEFAULT_MODELS",
]