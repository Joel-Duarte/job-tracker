import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "global_settings.json")

def load_settings() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {"ENABLE_EMBEDDINGS": True}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load global settings: {e}")
        return {"ENABLE_EMBEDDINGS": True}

def save_settings(settings: dict) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save global settings: {e}")

def get_setting(key: str, default=None):
    return load_settings().get(key, default)

def set_setting(key: str, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
