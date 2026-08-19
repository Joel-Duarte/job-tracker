import asyncio
import json
import os
from unittest.mock import patch

import pytest

from app.core import config_manager
from app.core.config_manager import (
    clear_cache,
    get_setting,
    get_setting_sync,
    load_settings,
    load_settings_sync,
    save_settings,
    save_settings_sync,
    set_setting,
    set_setting_sync,
)


@pytest.fixture(autouse=True)
def reset_config_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.mark.asyncio
async def test_async_load_and_save_settings(tmp_path):
    test_file = str(tmp_path / "global_settings.json")
    with patch.object(config_manager, "CONFIG_FILE", test_file):
        clear_cache()

        # Initial load should return default dictionary
        settings = await load_settings()
        assert settings.get("ENABLE_EMBEDDINGS") is True

        # Set setting and get setting
        await set_setting("ENABLE_EMBEDDINGS", False)
        assert await get_setting("ENABLE_EMBEDDINGS") is False

        # Save settings and reload
        await save_settings({"ENABLE_EMBEDDINGS": True, "CUSTOM_KEY": "test_value"})
        reloaded = await load_settings()
        assert reloaded.get("CUSTOM_KEY") == "test_value"
        assert await get_setting("CUSTOM_KEY") == "test_value"


@pytest.mark.asyncio
async def test_in_memory_caching(tmp_path):
    test_file = str(tmp_path / "global_settings.json")
    with patch.object(config_manager, "CONFIG_FILE", test_file):
        clear_cache()

        # Seed initial config file
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump({"ENABLE_EMBEDDINGS": True, "INITIAL": True}, f)

        # First load populates cache
        settings_1 = await load_settings()
        assert settings_1.get("INITIAL") is True

        # Modify file directly on disk
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump({"ENABLE_EMBEDDINGS": False, "INITIAL": False}, f)

        # Subsequent load should hit in-memory cache and return initial value
        settings_2 = await load_settings()
        assert settings_2.get("INITIAL") is True

        # Clearing cache forces read from disk
        clear_cache()
        settings_3 = await load_settings()
        assert settings_3.get("INITIAL") is False


@pytest.mark.asyncio
async def test_atomic_write_operations(tmp_path):
    test_file = str(tmp_path / "global_settings.json")
    with patch.object(config_manager, "CONFIG_FILE", test_file):
        clear_cache()

        await save_settings({"ENABLE_EMBEDDINGS": False, "TEST": "atomic"})

        # Confirm target file exists and contains valid JSON
        assert os.path.exists(test_file)
        with open(test_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"ENABLE_EMBEDDINGS": False, "TEST": "atomic"}

        # Ensure no temp files remain in target directory
        temp_files = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
        assert len(temp_files) == 0


@pytest.mark.asyncio
async def test_concurrent_reads_and_writes(tmp_path):
    test_file = str(tmp_path / "global_settings.json")
    with patch.object(config_manager, "CONFIG_FILE", test_file):
        clear_cache()

        async def worker(idx: int):
            await set_setting(f"key_{idx}", idx)
            val = await get_setting(f"key_{idx}")
            assert val == idx

        # Run 30 concurrent workers performing writes and reads
        tasks = [worker(i) for i in range(30)]
        await asyncio.gather(*tasks)

        final_settings = await load_settings()
        for i in range(30):
            assert final_settings.get(f"key_{i}") == i


@pytest.mark.asyncio
async def test_fallback_config_writing(tmp_path):
    primary_file = "/proc/invalid_dir/global_settings.json"
    fallback_file = str(tmp_path / "fallback_global_settings.json")

    with (
        patch.object(config_manager, "CONFIG_FILE", primary_file),
        patch.object(config_manager, "FALLBACK_CONFIG_FILE", fallback_file),
    ):
        clear_cache()

        await save_settings({"FALLBACK_TEST": True})
        assert os.path.exists(fallback_file)
        with open(fallback_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("FALLBACK_TEST") is True


def test_sync_methods(tmp_path):
    test_file = str(tmp_path / "global_settings.json")
    with patch.object(config_manager, "CONFIG_FILE", test_file):
        clear_cache()

        settings = load_settings_sync()
        assert settings.get("ENABLE_EMBEDDINGS") is True

        set_setting_sync("SYNC_KEY", "sync_val")
        assert get_setting_sync("SYNC_KEY") == "sync_val"

        save_settings_sync({"ENABLE_EMBEDDINGS": True, "SYNC_KEY": "new_val"})
        assert get_setting_sync("SYNC_KEY") == "new_val"
