from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.security import _get_fernet
from app.schemas.applications import (
    AllowedApplicationStatus,
    BulkTransitionRequest,
    BulkTransitionResult,
)


def test_new_terminal_statuses_exist():
    assert AllowedApplicationStatus.HIRED == "HIRED"
    assert AllowedApplicationStatus.ARCHIVED == "ARCHIVED"
    assert AllowedApplicationStatus.WITHDRAWN == "WITHDRAWN"


def test_bulk_transition_request_schema():
    req = BulkTransitionRequest(
        target_status=AllowedApplicationStatus.ARCHIVED,
        from_statuses=[
            AllowedApplicationStatus.APPLIED,
            AllowedApplicationStatus.OFFER,
        ],
    )
    assert req.target_status == "ARCHIVED"
    assert "APPLIED" in [str(s) for s in req.from_statuses]
    assert req.exclude_ids == []


def test_bulk_transition_result_schema():
    res = BulkTransitionResult(updated_count=2, updated_ids=[1, 2])
    assert res.updated_count == 2
    assert res.updated_ids == [1, 2]


def test_secret_key_validation_in_non_dev_environments():
    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly configured"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="default-development-secret-key-change-in-production",
        )

    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly configured"):
        Settings(ENVIRONMENT="production", SECRET_KEY="")

    valid_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-secret-1234567890",
    )
    assert valid_settings.SECRET_KEY == "secure-production-secret-1234567890"


def test_secret_key_auto_generation_and_persistence(tmp_path):
    fake_key_file = tmp_path / "data" / ".sec_key"
    with patch("app.core.config.PROJECT_ROOT", tmp_path):
        # 1. First init: auto-generate and persist key in dev/staging
        s1 = Settings(ENVIRONMENT="development", SECRET_KEY="")
        assert s1.SECRET_KEY != ""
        assert fake_key_file.exists()
        persisted_key = fake_key_file.read_text().strip()
        assert s1.SECRET_KEY == persisted_key
        assert oct(fake_key_file.stat().st_mode)[-3:] == "600"

        # 2. Second init: read existing persisted key
        s2 = Settings(ENVIRONMENT="staging", SECRET_KEY="")
        assert s2.SECRET_KEY == persisted_key

        # 3. Explicit secret key overrides persisted file
        s3 = Settings(ENVIRONMENT="development", SECRET_KEY="custom-explicit-key")
        assert s3.SECRET_KEY == "custom-explicit-key"


def test_security_fernet_secret_key_validation():
    dummy_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-secret-1234567890",
    )
    # Mutate attribute to simulate unvalidated state
    dummy_settings.SECRET_KEY = "default-development-secret-key-change-in-production"

    with patch("app.core.security.settings", dummy_settings):
        with pytest.raises(
            ValueError, match="SECRET_KEY must be explicitly configured"
        ):
            _get_fernet()
