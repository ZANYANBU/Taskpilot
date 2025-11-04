from abc import ABC, abstractmethod
from typing import Dict, List, Optional


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