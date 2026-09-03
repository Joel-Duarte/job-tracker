from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    has_completed_onboarding: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enable_email_intake: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enable_embeddings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enable_web_search: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
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
    cover_letter_length: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )
    cover_letter_tone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="professional"
    )
    search_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="automatic"
    )
    searxng_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
