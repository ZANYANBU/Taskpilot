import configparser
from threading import Lock
from typing import Dict

from .constants import CONFIG_FILE, DEFAULT_CONFIG, GROQ_DEFAULT_MODEL, GROQ_DEPRECATED_MODELS
from .crypto import decrypt_value, encrypt_value, get_master_key

_config_lock = Lock()


def _ensure_defaults(cfg: configparser.ConfigParser) -> None:
    for section, defaults in DEFAULT_CONFIG.items():
        if section not in cfg:
            cfg[section] = {}
        
        # All values in DEFAULT_CONFIG are now dictionaries
        for key, value in defaults.items():
            current = cfg[section].get(key, "").strip()
            if not current:
                cfg[section][key] = value

    # Handle deprecated Groq models
    model_value = cfg["GROQ"].get("model", "").strip()
    if model_value in GROQ_DEPRECATED_MODELS:
        cfg["GROQ"]["model"] = GROQ_DEPRECATED_MODELS[model_value]
    elif not model_value:
        cfg["GROQ"]["model"] = GROQ_DEFAULT_MODEL


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    with _config_lock:
        if CONFIG_FILE.exists():
            cfg.read(CONFIG_FILE)
        else:
            cfg.read_dict(DEFAULT_CONFIG)
            with CONFIG_FILE.open("w") as fh:
                cfg.write(fh)
        _ensure_defaults(cfg)
    return cfg


def get_decrypted_config() -> Dict[str, Dict[str, str]]:
    """Get config with decrypted sensitive values."""
    cfg = load_config()
    result = {}
    master_key = get_master_key()
    for section in cfg.sections():
        result[section] = {}
        for key, value in cfg[section].items():
            if key == "api_key" and value:
                try:
                    result[section][key] = decrypt_value(value, master_key)
                except Exception:
                    # If decryption fails, return empty (better than crashing)
                    result[section][key] = ""
            else:
                result[section][key] = value
    return result


def save_config(payload: Dict[str, Dict[str, str]]) -> None:
    cfg = load_config()
    with _config_lock:
        for section, values in payload.items():
            if section not in cfg:
                cfg[section] = {}
            if isinstance(values, str):
                # Handle cases where a string is passed instead of a dictionary
                # This is a workaround for the 'str' object has no attribute 'items' error
                continue
            for key, value in values.items():
                if key == "api_key" and value:
                    # Encrypt API keys
                    cfg[section][key] = encrypt_value(str(value), get_master_key())
                else:
                    cfg[section][key] = str(value or "")
        _ensure_defaults(cfg)
        with CONFIG_FILE.open("w") as fh:
            cfg.write(fh)
