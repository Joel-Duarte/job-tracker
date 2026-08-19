from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enable_embeddings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    agent_chat_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    enable_auto_cover_letter: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    cover_letter_match_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
