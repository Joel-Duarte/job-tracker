from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.applications import Base


class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("email_applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    persona: Mapped[str] = mapped_column(Text, nullable=False, server_default="TECHNICAL_BAR_RAISER")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="IN_PROGRESS")
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    turns_data: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default="[]"
    )
    summary_feedback: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    application: Mapped[Optional["ApplicationModel"]] = relationship()

    __table_args__ = (
        Index("idx_interview_sessions_application_id", "application_id"),
        Index("idx_interview_sessions_status", "status"),
    )
