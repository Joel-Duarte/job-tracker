from datetime import UTC, datetime

from app.models.applications import Base
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class PromptModel(Base):
    __tablename__ = "email_prompts"

    name: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )  # 'extraction' or 'summarization'
    template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
