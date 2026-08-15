from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.applications import Base


class CandidateCVModel(Base):
    __tablename__ = "candidate_cvs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    anonymized_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_skills: Mapped[List[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    years_of_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    domain_expertise: Mapped[List[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    core_competencies: Mapped[List[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
