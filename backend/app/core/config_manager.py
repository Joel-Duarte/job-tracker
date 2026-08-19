import asyncio
import json
import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "global_settings.json")
)
FALLBACK_CONFIG_FILE = os.path.join(tempfile.gettempdir(), "global_settings.json")

_SETTINGS_CACHE: dict[str, Any] | None = None
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def clear_cache() -> None:
    """Clears the in-memory cache and lock state (useful for tests)."""
    global _SETTINGS_CACHE, _lock
    _SETTINGS_CACHE = None
    _lock = None


def _sync_read_settings() -> dict[str, Any]:
    for path in (CONFIG_FILE, FALLBACK_CONFIG_FILE):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.error(f"Failed to load global settings from {path}: {e}")
    return {"ENABLE_EMBEDDINGS": True}


def _sync_write_settings(
    settings: dict[str, Any], target_file: str | None = None
) -> None:
    if target_file is None:
        target_file = CONFIG_FILE

    temp_path: str | None = None
    try:
        target_dir = os.path.dirname(os.path.abspath(target_file))
        os.makedirs(target_dir, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=target_dir, prefix="global_settings_", suffix=".tmp"
        )
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_file)
    except Exception as primary_exc:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

        if target_file != FALLBACK_CONFIG_FILE:
            logger.warning(
                f"Failed to write to primary config path {target_file}: {primary_exc}. "
                f"Attempting fallback path {FALLBACK_CONFIG_FILE}."
            )
            _sync_write_settings(settings, target_file=FALLBACK_CONFIG_FILE)
        else:
            logger.error(
                f"Failed to save global settings to fallback path: {primary_exc}"
            )
            raise primary_exc


def load_settings_sync() -> dict[str, Any]:
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None:
        return dict(_SETTINGS_CACHE)
    settings = _sync_read_settings()
    _SETTINGS_CACHE = settings
    return dict(_SETTINGS_CACHE)


def save_settings_sync(settings: dict[str, Any]) -> None:
    global _SETTINGS_CACHE
    _SETTINGS_CACHE = dict(settings)
    _sync_write_settings(dict(settings))


def get_setting_sync(key: str, default: Any = None) -> Any:
    return load_settings_sync().get(key, default)


def set_setting_sync(key: str, value: Any) -> None:
    settings = load_settings_sync()
    settings[key] = value
    save_settings_sync(settings)


async def load_settings() -> dict[str, Any]:
    global _SETTINGS_CACHE
    lock = _get_lock()
    async with lock:
        if _SETTINGS_CACHE is not None:
            return dict(_SETTINGS_CACHE)
        settings = await asyncio.to_thread(_sync_read_settings)
        _SETTINGS_CACHE = settings
        return dict(_SETTINGS_CACHE)


async def save_settings(settings: dict[str, Any]) -> None:
    global _SETTINGS_CACHE
    lock = _get_lock()
    async with lock:
        _SETTINGS_CACHE = dict(settings)
        await asyncio.to_thread(_sync_write_settings, dict(settings))


async def get_setting(key: str, default: Any = None) -> Any:
    settings = await load_settings()
    return settings.get(key, default)


async def set_setting(key: str, value: Any) -> None:
    lock = _get_lock()
    async with lock:
        global _SETTINGS_CACHE
        if _SETTINGS_CACHE is None:
            _SETTINGS_CACHE = await asyncio.to_thread(_sync_read_settings)
        updated = dict(_SETTINGS_CACHE)
        updated[key] = value
        _SETTINGS_CACHE = updated
        await asyncio.to_thread(_sync_write_settings, updated)
