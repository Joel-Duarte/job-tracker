from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class StagingItemModel(Base):
    __tablename__ = "staging_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Target email details
    email_account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    email_message_id: Mapped[str | None] = mapped_column(Text, unique=True)
    email_internet_message_id: Mapped[str | None] = mapped_column(Text, unique=True)
    email_conversation_id: Mapped[str | None] = mapped_column(Text)
    email_sender: Mapped[str | None] = mapped_column(Text)
    email_sender_name: Mapped[str | None] = mapped_column(Text)
    email_subject: Mapped[str | None] = mapped_column(Text)
    email_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_raw_body: Mapped[str | None] = mapped_column(Text)

    # Extraction and match evaluation state
    extracted_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_reason: Mapped[str | None] = mapped_column(
        Text
    )  # e.g., "LOW_FUZZY_SCORE", "AMBIGUOUS_POSITION"

    # Staging Queue Lifecycle State: "PENDING", "APPROVED", "REJECTED", "PROCESSED"
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="PENDING")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_staging_items_status", "status"),
        Index("idx_staging_items_conversation_id", "email_conversation_id"),
        Index("idx_staging_items_received_at", "email_received_at"),
    )
