import requests
from typing import Dict, List

from . import LLMProvider
from ...constants import GROQ_DEFAULT_MODEL, GROQ_DEPRECATED_MODELS
from ..groq import GroqError

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    """Groq LLM provider implementation."""

    def __init__(self, api_key: str, model: str = GROQ_DEFAULT_MODEL):
        super().__init__("groq", api_key, model)

    def request_completion(self, prompt: str) -> str:
        if not self.api_key:
            raise GroqError("GROQ API key is missing. Add it via Settings.")

        model_name = self.model.strip()
        if model_name in GROQ_DEPRECATED_MODELS:
            model_name = GROQ_DEPRECATED_MODELS[model_name]
        if not model_name:
            model_name = GROQ_DEFAULT_MODEL

        payload: Dict[str, object] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            detail = ""
            if err.response is not None:
                try:
                    detail_json = err.response.json()
                    detail = (
                        detail_json.get("error", {}).get("message")
                        or detail_json.get("message")
                        or err.response.text
                    )
                except ValueError:
                    detail = err.response.text
            detail = detail or str(err)
            raise GroqError(f"Groq request failed: {detail}") from None
        except requests.exceptions.RequestException as err:
            raise GroqError(f"Groq request failed: {err}") from None

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as err:
            raise GroqError(f"Unexpected Groq response format: {err}") from None

    def list_models(self) -> List[str]:
        # Groq doesn't have a public models endpoint, so return known models
        return [
            "llama3-8b-8192",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma-7b-it",
            "gemma2-9b-it",
        ]

    def validate_config(self) -> bool:
        return bool(self.api_key and self.model)

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "streaming": False,
            "function_calling": False,
            "vision": False,
        }