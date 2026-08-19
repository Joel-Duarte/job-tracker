from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Text, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import decrypt_secret, encrypt_secret
from app.models.applications import Base


class LLMConfigModel(Base):
    __tablename__ = "email_llm_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False, default="custom")
    api_base: Mapped[str | None] = mapped_column(Text, nullable=True)
    _api_key: Mapped[str | None] = mapped_column("api_key", Text, nullable=True)

    # Default / Primary Model Settings
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True, default=50)
    top_p: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Agent Specific Settings
    agent_model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    agent_top_k: Mapped[int | None] = mapped_column(Integer, nullable=True, default=50)
    agent_top_p: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)
    agent_max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_max_recursions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @hybrid_property
    def api_key(self) -> str | None:
        return decrypt_secret(self._api_key)

    @api_key.setter
    def api_key(self, value: str | None) -> None:
        self._api_key = encrypt_secret(value)
