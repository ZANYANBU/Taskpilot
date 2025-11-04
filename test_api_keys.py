#!/usr/bin/env python3
"""Test script to check which API keys are working."""

from backend.config import get_decrypted_config
from backend.services.llm_providers import create_provider

def test_provider(name: str, api_key: str, model: str) -> bool:
    """Test if a provider works with the given credentials."""
    try:
        provider = create_provider(name, api_key, model)
        if not provider:
            print(f"❌ {name.upper()}: Provider creation failed")
            return False

        result = provider.request_completion("Say 'Hello, world!' in exactly 3 words.")
        if result and len(result.strip()) > 0:
            print(f"✅ {name.upper()}: Working - Response: {result.strip()}")
            return True
        else:
            print(f"❌ {name.upper()}: Empty response")
            return False
    except Exception as e:
        print(f"❌ {name.upper()}: Error - {str(e)}")
        return False

def main():
    config = get_decrypted_config()

    print("Testing API keys...\n")

    # Test Groq
    groq_config = config.get('GROQ', {})
    test_provider('groq', groq_config.get('api_key', ''), groq_config.get('model', ''))

    # Test Google
    google_config = config.get('GOOGLE', {})
    test_provider('google', google_config.get('api_key', ''), google_config.get('model', ''))

    # Test OpenAI
    openai_config = config.get('OPENAI', {})
    test_provider('openai', openai_config.get('api_key', ''), openai_config.get('model', ''))

    print("\nTest complete!")

if __name__ == "__main__":
    main()