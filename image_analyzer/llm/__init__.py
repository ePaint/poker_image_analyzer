from typing import Literal

from image_analyzer.llm.protocol import LLMProvider
from image_analyzer.llm.anthropic import AnthropicProvider

ProviderName = Literal["anthropic"]

_PROVIDERS = {
    "anthropic": AnthropicProvider,
}


def get_provider(
    name: ProviderName = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
) -> LLMProvider:
    """Factory function to get provider by name.

    Args:
        name: Provider name ("anthropic" or "deepseek")
        api_key: API key (uses env var if None)
        model: Model name (uses provider default if None)

    Returns:
        LLMProvider instance
    """
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")

    provider_cls = _PROVIDERS[name]
    if model is None:
        return provider_cls(api_key)
    return provider_cls(api_key, model)


__all__ = [
    "LLMProvider",
    "ProviderName",
    "AnthropicProvider",
    "get_provider",
]
