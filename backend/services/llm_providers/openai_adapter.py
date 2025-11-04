import requests
from typing import Optional
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for content generation."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def request_completion(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Request a completion from OpenAI API.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0-2)
            
        Returns:
            The generated text or None if request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            print(f"OpenAI API request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Failed to parse OpenAI response: {e}")
            return None
