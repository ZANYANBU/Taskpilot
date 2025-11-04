from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "taskpilot_config.ini"
DB_FILE = BASE_DIR / "taskpilot.db"
DEFAULT_USER_AGENT = "taskpilot-agent/2.0"
REDIRECT_URI = "http://localhost:8080"
UA_HEADERS = {"User-Agent": "Mozilla/5.0"}
REGION_CODES = {
    "united_states": "US",
    "united_kingdom": "GB",
    "japan": "JP",
    "germany": "DE",
    "australia": "AU"
}
GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"
GROQ_MODEL_CHOICES = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "llama-guard-3-8b"
]
GROQ_DEPRECATED_MODELS = {
    "llama3-8b-8192": GROQ_DEFAULT_MODEL,
    "llama3-70b-8192": "llama-3.1-70b-versatile"
}
GOOGLE_DEFAULT_MODEL = "gemini-2.0-flash"
GOOGLE_MODEL_CHOICES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]
OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo"
OPENAI_MODEL_CHOICES = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini"
]
DEFAULT_CONFIG = {
    "GROQ": {"api_key": "", "model": GROQ_DEFAULT_MODEL},
    "GOOGLE": {"api_key": "", "model": GOOGLE_DEFAULT_MODEL, "project_name": "", "project_number": ""},
    "OPENAI": {"api_key": "", "model": OPENAI_DEFAULT_MODEL},
    "REDDIT": {
        "client_id": "",
        "client_secret": "",
        "username": "",
        "password": "",
        "refresh_token": "",
        "user_agent": DEFAULT_USER_AGENT,
    },
    "SETTINGS": {
        "default_llm_provider": "google"
    }
}
CONTENT_LENGTH_PRESETS = {
    "Short": 3,
    "Standard": 5,
    "Extended": 7,
}
