from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.applications import Base

if TYPE_CHECKING:
    from app.models.candidate_profile import CandidateCVModel


class RoleAlignmentDossierModel(Base):
    __tablename__ = "role_alignment_dossiers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cv_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidate_cvs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_track: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ai_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cv: Mapped["CandidateCVModel"] = relationship("CandidateCVModel")

    __table_args__ = (
        UniqueConstraint(
            "cv_id", "role_track", name="uq_role_alignment_dossier_cv_track"
        ),
        Index("idx_role_alignment_dossier_track", "role_track"),
    )
