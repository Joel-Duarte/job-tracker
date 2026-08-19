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

    # Bootstrap security configuration; runtime provider credentials live in PostgreSQL.
    SECRET_KEY: str = "default-development-secret-key-change-in-production"
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
        if env not in {"development", "test", "testing"} and self.SECRET_KEY in {
            "",
            "default-development-secret-key-change-in-production",
        }:
            raise ValueError(
                "SECRET_KEY must be explicitly configured in non-development environments"
            )
        return self

    def get_database_url(self) -> str:
        """Always constructs the connection URI dynamically from current settings."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
