from datetime import datetime
from typing import Any

from app.models.applications import Base
from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class IntakeEvaluationTaskModel(Base):
    """
    Persisted queue for asynchronous job lead intake & AI qualification assessments,
    as well as candidate CV de-identification and extraction tasks.
    Enables continuous input UX and tracks pipeline execution bounded by provider concurrency limits.
    """

    __tablename__ = "intake_evaluation_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_type: Mapped[str] = mapped_column(
        Text, nullable=False, default="JOB_ASSESSMENT", index=True
    )
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_hint: Mapped[str] = mapped_column(Text, nullable=False, default="Job Lead")

    # Status: 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="QUEUED", index=True
    )

    # Stage: 'FETCHING', 'SCRUBBING', 'EXTRACTING', 'MATCHING', 'ASSESSING', 'SAVING', 'COMPLETE', 'FAILED'
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="FETCHING")

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Holds evaluated JobAssessmentResult or CVAnonymizationResult JSON structure upon completion
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
