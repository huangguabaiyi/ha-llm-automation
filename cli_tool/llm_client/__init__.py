from .base import BaseLLMClient
from .anthropic_client import AnthropicClient
from .openai_client import OpenAIClient


def create_client(config: dict) -> BaseLLMClient:
    provider = config.get("provider", "anthropic")
    if provider == "anthropic":
        return AnthropicClient(config)
    elif provider in ("openai", "openai_compatible"):
        return OpenAIClient(config)
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}")


__all__ = ["BaseLLMClient", "AnthropicClient", "OpenAIClient", "create_client"]
