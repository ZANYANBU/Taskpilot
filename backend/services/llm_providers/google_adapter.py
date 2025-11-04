import requests
from typing import Dict

from .base import LLMProvider
from ...constants import GOOGLE_DEFAULT_MODEL


class GoogleError(Exception):
    """Custom exception for Google API errors."""
    pass


class GoogleProvider(LLMProvider):
    """Google Generative AI (Gemini) provider implementation."""

    def __init__(self, api_key: str, model: str = GOOGLE_DEFAULT_MODEL):
        super().__init__("google", api_key, model)

    def request_completion(self, prompt: str) -> str:
        if not self.api_key:
            raise GoogleError("Google API key is missing. Add it via Settings.")

        model_name = self.model.strip() or GOOGLE_DEFAULT_MODEL
        
        # Construct the API URL for Google Generative AI
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        payload: Dict[str, object] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                api_url, 
                json=payload, 
                headers=headers, 
                params=params,
                timeout=30
            )
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
            raise GoogleError(f"Google API request failed: {detail}") from None
        except requests.exceptions.RequestException as err:
            raise GoogleError(f"Google API request failed: {err}") from None

        try:
            data = response.json()
            # Extract text from Google's response format
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return content
        except (KeyError, IndexError, ValueError) as err:
            raise GoogleError(f"Unexpected Google API response format: {err}") from None
