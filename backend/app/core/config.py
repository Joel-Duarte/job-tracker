from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    SEED_DEV_DATA: bool = False

    # PostgreSQL Connection Pool Configuration
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: float = 60.0
    DB_POOL_RECYCLE: int = 1800

    # Bootstrap security configuration; runtime provider credentials live in PostgreSQL.
    SECRET_KEY: str = ""
    ADMIN_SECRET: str = ""

    # Public exposed API base URL (for Docker port forwarding or reverse proxy)
    PUBLIC_API_URL: str | None = None
    PUBLIC_FRONTEND_URL: str | None = None

    # Camofox Browser Automation Server URL
    CAMOUFOX_ENDPOINT: str = "http://localhost:9377"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        env = (self.ENVIRONMENT or "development").strip().lower()
        allowed_auto_envs = {"development", "staging", "test", "testing"}

        raw_key = (self.SECRET_KEY or "").strip()
        is_explicit = bool(
            raw_key and raw_key != "default-development-secret-key-change-in-production"
        )

        if env not in allowed_auto_envs and not is_explicit:
            raise ValueError(
                "SECRET_KEY must be explicitly configured in non-development environments"
            )

        if is_explicit:
            self.SECRET_KEY = raw_key
        else:
            self.SECRET_KEY = _get_or_generate_secret_key()

        return self

    def get_database_url(self) -> str:
        """Always constructs the connection URI dynamically from current settings."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


def _get_or_generate_secret_key() -> str:
    """Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a secure Fernet key."""
    key_file = PROJECT_ROOT / "data" / ".sec_key"
    if key_file.exists():
        try:
            key = key_file.read_text(encoding="utf-8").strip()
            if key:
                return key
        except Exception:
            pass

    from cryptography.fernet import Fernet

    new_key = Fernet.generate_key().decode("utf-8")
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(new_key, encoding="utf-8")
        try:
            key_file.chmod(0o600)
        except Exception:
            pass
    except Exception:
        pass
    return new_key


settings = Settings()
