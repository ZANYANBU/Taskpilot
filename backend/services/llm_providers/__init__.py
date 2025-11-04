from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .base import LLMProvider
from .groq_adapter import GroqProvider
from .google_adapter import GoogleProvider, GoogleError
from .openai_adapter import OpenAIProvider
from ..groq import GroqError


class LLMRegistry:
    """Registry for LLM providers."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.enabled_providers: set = set()

    def register_provider(self, provider: LLMProvider):
        """Register a provider."""
        self.providers[provider.name] = provider

    def enable_provider(self, name: str):
        """Enable a provider."""
        if name in self.providers:
            self.enabled_providers.add(name)

    def disable_provider(self, name: str):
        """Disable a provider."""
        self.enabled_providers.discard(name)

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get a provider by name."""
        return self.providers.get(name)

    def get_enabled_providers(self) -> List[LLMProvider]:
        """Get all enabled providers."""
        return [self.providers[name] for name in self.enabled_providers if name in self.providers]

    def get_all_providers(self) -> List[LLMProvider]:
        """Get all registered providers."""
        return list(self.providers.values())


# Global registry instance
_registry = LLMRegistry()


def get_registry() -> LLMRegistry:
    """Get the global LLM registry."""
    return _registry


def create_provider(name: str, api_key: str, model: str) -> Optional[LLMProvider]:
    """Factory function to create a provider instance."""
    if name == "groq":
        return GroqProvider(api_key, model)
    elif name == "google":
        return GoogleProvider(api_key, model)
    elif name == "openai":
        return OpenAIProvider(api_key, model)
    return None


def request_completion(api_key: str, prompt: str, model: str) -> str:
    """Request completion from appropriate LLM provider.
    
    Determines provider based on the model name or tries OpenAI first if available.
    """
    # Check if it's an OpenAI model
    if model and any(o_model in model for o_model in ["gpt-", "gpt3", "gpt4"]):
        provider = create_provider("openai", api_key, model)
        if provider:
            result = provider.request_completion(prompt)
            if result:
                return result
    
    # Check if it's a Google model
    if model and any(g_model in model for g_model in ["gemini", "gemini-pro", "gemini-1.5"]):
        provider = create_provider("google", api_key, model)
        if provider:
            try:
                return provider.request_completion(prompt)
            except GoogleError as e:
                raise GoogleError(str(e)) from None
    
    # Default to Groq
    provider = create_provider("groq", api_key, model)
    if provider:
        return provider.request_completion(prompt)
    raise GroqError("Provider not available")