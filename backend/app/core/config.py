from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "postgres"

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    SEED_DEV_DATA: bool = False

    # Public exposed API base URL (for Docker port forwarding or reverse proxy)
    PUBLIC_API_URL: str | None = None

    # Camofox Browser Automation Server URL
    CAMOUFOX_ENDPOINT: str = "http://localhost:9377"

    # Embedding Service Configuration
    EMBEDDING_API_URL: str = "http://localhost:1234/v1/embeddings"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL_NAME: str = "nomic-embed-text-v2-moe"
    EMBEDDING_DIMENSION: int = 768

    LLM_PROVIDER_NAME: str = "openai"  # Options: "custom", "openai", "anthropic", etc.
    LLM_API_BASE: str = "http://localhost:1234/v1"
    LLM_API_KEY: str = (
        "lm-1234"  # LM Studio ignores key value, but client requires non-empty string
    )
    LLM_MODEL_NAME: str = "qwen/qwen3.5-9b"

    STAGING_MATCH_THRESHOLD: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """Always constructs the connection URI dynamically from current settings."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
