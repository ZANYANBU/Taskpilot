from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .groq_adapter import GroqProvider
from ..groq import GroqError


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, name: str, api_key: str, model: str):
        self.name = name
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def request_completion(self, prompt: str) -> str:
        """Request a completion from the LLM."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models for this provider."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the provider configuration."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities (e.g., streaming, function calling)."""
        pass


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
    # Add other providers here
    return None


def request_completion(api_key: str, prompt: str, model: str) -> str:
    """Backward compatibility function for Groq."""
    provider = create_provider("groq", api_key, model)
    if provider:
        return provider.request_completion(prompt)
    raise GroqError("Provider not available")