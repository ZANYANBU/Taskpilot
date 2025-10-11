import requests
from typing import Dict

from ..constants import GROQ_DEFAULT_MODEL, GROQ_DEPRECATED_MODELS

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(RuntimeError):
    """Raised when Groq API returns an error."""


def request_completion(api_key: str, prompt: str, model: str | None = None) -> str:
    if not api_key:
        raise GroqError("GROQ API key is missing. Add it via Settings.")

    model_name = (model or GROQ_DEFAULT_MODEL).strip()
    if model_name in GROQ_DEPRECATED_MODELS:
        model_name = GROQ_DEPRECATED_MODELS[model_name]
    if not model_name:
        model_name = GROQ_DEFAULT_MODEL

    payload: Dict[str, object] = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
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
