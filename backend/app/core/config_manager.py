import json
import logging
import os

logger = logging.getLogger(__name__)

PRIMARY_CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "global_settings.json")
)
FALLBACK_CONFIG_FILE = "/tmp/global_settings.json"

DEFAULT_SETTINGS = {
    "ENABLE_EMBEDDINGS": True,
    "auto_generate_cover_letter": False,
    "cover_letter_min_match_pct": 50,
}

_SETTINGS_CACHE: dict | None = None


def load_settings() -> dict:
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None:
        return dict(_SETTINGS_CACHE)

    loaded_data = None
    for file_path in [PRIMARY_CONFIG_FILE, FALLBACK_CONFIG_FILE]:
        if os.path.exists(file_path):
            try:
                with open(file_path) as f:
                    loaded_data = json.load(f)
                    break
            except Exception as e:
                logger.warning(f"Could not load global settings from {file_path}: {e}")

    merged = dict(DEFAULT_SETTINGS)
    if loaded_data and isinstance(loaded_data, dict):
        merged.update(loaded_data)

    _SETTINGS_CACHE = merged
    return dict(_SETTINGS_CACHE)


def save_settings(settings: dict) -> None:
    global _SETTINGS_CACHE
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    _SETTINGS_CACHE = merged

    saved = False
    for file_path in [PRIMARY_CONFIG_FILE, FALLBACK_CONFIG_FILE]:
        try:
            with open(file_path, "w") as f:
                json.dump(merged, f, indent=2)
            saved = True
            break
        except Exception as e:
            logger.warning(f"Could not save global settings to {file_path}: {e}")

    if not saved:
        logger.error(
            "Failed to save global settings to any file path, kept in-memory cache."
        )


def get_setting(key: str, default=None):
    loaded = load_settings()
    if default is None and key in DEFAULT_SETTINGS:
        default = DEFAULT_SETTINGS[key]
    return loaded.get(key, default)


def set_setting(key: str, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
