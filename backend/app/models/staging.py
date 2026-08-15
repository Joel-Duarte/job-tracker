from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, DateTime, Float, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.applications import Base



class StagingItemModel(Base):
    __tablename__ = "email_staging_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Target email details
    email_account_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    email_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_internet_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_conversation_id: Mapped[Optional[str]] = mapped_column(Text)
    email_sender: Mapped[Optional[str]] = mapped_column(Text)
    email_sender_name: Mapped[Optional[str]] = mapped_column(Text)
    email_subject: Mapped[Optional[str]] = mapped_column(Text)
    email_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    email_raw_body: Mapped[Optional[str]] = mapped_column(Text)

    # Extraction and match evaluation state
    extracted_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_reason: Mapped[Optional[str]] = mapped_column(Text)  # e.g., "LOW_FUZZY_SCORE", "AMBIGUOUS_POSITION"
    
    # Staging Queue Lifecycle State: "PENDING", "APPROVED", "REJECTED", "PROCESSED"
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="PENDING")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_email_staging_items_status", "status"),
        Index("idx_email_staging_items_conversation_id", "email_conversation_id"),
        Index("idx_email_staging_items_received_at", "email_received_at"),
    )