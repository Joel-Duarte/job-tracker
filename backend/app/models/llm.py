from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.applications import Base

class LLMConfigModel(Base):
    __tablename__ = "email_llm_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "openai", "ollama", "anthropic", "custom"
    api_base: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)    # e.g., "gpt-4o", "qwen3.5-9b"
    embedding_model_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())