import json
import logging
import os

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "global_settings.json"
)

DEFAULT_SETTINGS = {
    "ENABLE_EMBEDDINGS": True,
    "auto_generate_cover_letter": False,
    "cover_letter_min_match_pct": 50,
}


def load_settings() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(CONFIG_FILE) as f:
            loaded = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(loaded)
            return merged
    except Exception as e:
        logger.error(f"Failed to load global settings: {e}")
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save global settings: {e}")


def get_setting(key: str, default=None):
    loaded = load_settings()
    if default is None and key in DEFAULT_SETTINGS:
        default = DEFAULT_SETTINGS[key]
    return loaded.get(key, default)


def set_setting(key: str, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
