from datetime import UTC, datetime

from app.models.applications import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class ProcessedEmailModel(Base):
    """
    Single source of truth for all email deduplication.
    Every email that passes through the intake pipeline (whether ingested,
    staged, filtered out by keyword, or classified as non-job) gets a record here.
    This prevents re-evaluation on subsequent syncs of the same date window.

    Status values:
    - "ingested"     : Committed to applications pipeline
    - "staged"       : Routed to human-in-the-loop staging queue
    - "not_a_job"    : Passed the LLM but was not a job application
    - "filtered_out" : Rejected by keyword pre-filter before any LLM call
    """

    __tablename__ = "processed_email_ids"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_processed_email_message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("email_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
