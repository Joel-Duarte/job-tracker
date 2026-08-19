import json
import logging
import os

from app.core.storage import get_storage_provider

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "global_settings.json"
)


def load_settings() -> dict:
    storage = get_storage_provider()
    if not storage.exists(CONFIG_FILE):
        return {"ENABLE_EMBEDDINGS": True}
    try:
        content = storage.read_text(CONFIG_FILE)
        if content:
            return json.loads(content)
        return {"ENABLE_EMBEDDINGS": True}
    except Exception as e:
        logger.error(f"Failed to load global settings: {e}")
        return {"ENABLE_EMBEDDINGS": True}


def save_settings(settings: dict) -> None:
    try:
        storage = get_storage_provider()
        content = json.dumps(settings, indent=2)
        storage.write_text(CONFIG_FILE, content)
    except Exception as e:
        logger.error(f"Failed to save global settings: {e}")


def get_setting(key: str, default=None):
    return load_settings().get(key, default)


def set_setting(key: str, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
