from datetime import datetime
from typing import Any, Optional
from sqlalchemy import BigInteger, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class IntakeEvaluationTaskModel(Base):
    """
    Persisted queue for asynchronous job lead intake & AI qualification assessments.
    Enables continuous input UX and tracks 4-stage pipeline execution safely.
    """
    __tablename__ = "intake_evaluation_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_hint: Mapped[str] = mapped_column(Text, nullable=False, default="Job Lead")
    
    # Status: 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'
    status: Mapped[str] = mapped_column(Text, nullable=False, default="QUEUED", index=True)
    
    # Stage: 'FETCHING', 'EXTRACTING', 'MATCHING', 'ASSESSING', 'COMPLETE', 'FAILED'
    stage: Mapped[str] = mapped_column(Text, nullable=False, default="FETCHING")
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Holds the complete evaluated JobAssessmentResult JSON structure upon completion
    result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
