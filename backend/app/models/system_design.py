from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.applications import Base

if TYPE_CHECKING:
    from app.models.applications import ApplicationModel


class SystemDesignChallengeModel(Base):
    """Curated or custom system design interview challenge with hidden ground-truth brief."""

    __tablename__ = "system_design_challenges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="DISTRIBUTED_SYSTEMS",
        server_default=text("'DISTRIBUTED_SYSTEMS'"),
    )
    difficulty: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="MEDIUM",
        server_default=text("'MEDIUM'"),
    )
    prompt_summary: Mapped[str] = mapped_column(Text, nullable=False)
    initial_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    # Hidden interviewer ground truth (scale targets, expected components, traps).
    # Must NEVER be exposed in candidate-facing Pydantic response schemas.
    interviewer_brief: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_sd_challenges_category", "category"),
        Index("idx_sd_challenges_difficulty", "difficulty"),
    )


class SystemDesignSessionModel(Base):
    """Authoritative PostgreSQL record for a system design interview session lifecycle."""

    __tablename__ = "system_design_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    challenge_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("system_design_challenges.id", ondelete="RESTRICT"),
        nullable=False,
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="ADAPTIVE",
        server_default=text("'ADAPTIVE'"),
    )
    brief_seed: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_selection_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="random",
        server_default=text("'random'"),
    )
    # Hidden snapshot of the resolved interviewer brief for this specific session/seed.
    # Must NEVER be exposed in candidate-facing Pydantic response schemas.
    session_brief: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    stage: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="REQUIREMENTS",
        server_default=text("'REQUIREMENTS'"),
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="IN_PROGRESS",
        server_default=text("'IN_PROGRESS'"),
    )
    requirements_transcript: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    requirements_ledger: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    diagrams_metadata: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    diagram_guidance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    architecture_reviews: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    defence_transcript: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    final_evaluation: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    challenge: Mapped["SystemDesignChallengeModel"] = relationship(
        "SystemDesignChallengeModel"
    )
    application: Mapped["ApplicationModel | None"] = relationship("ApplicationModel")

    __table_args__ = (
        Index("idx_sd_sessions_challenge_id", "challenge_id"),
        Index("idx_sd_sessions_status", "status"),
        Index("idx_sd_sessions_stage", "stage"),
    )
