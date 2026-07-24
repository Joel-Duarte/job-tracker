from datetime import datetime
from typing import Any, List, Optional, Dict
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass


class CompanyModel(Base):
    __tablename__ = "email_companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    applications: Mapped[List["ApplicationModel"]] = relationship(back_populates="company")

    __table_args__ = (
        Index("idx_email_companies_name_normalized", "name_normalized", unique=True),
        Index("idx_email_companies_domain", "domain"),
        Index(
            "idx_email_companies_name_trgm",
            "name_normalized",
            postgresql_using="gin",
            postgresql_ops={"name_normalized": "gin_trgm_ops"},
        ),
    )


class ApplicationModel(Base):
    __tablename__ = "email_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("email_companies.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[Optional[str]] = mapped_column(Text)
    position_normalized: Mapped[Optional[str]] = mapped_column(Text)
    external_job_id: Mapped[Optional[str]] = mapped_column(Text)
    job_url: Mapped[Optional[str]] = mapped_column(Text)
    application_key: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="APPLIED")
    application_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["CompanyModel"] = relationship(back_populates="applications")
    events: Mapped[List["ApplicationEventModel"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(ApplicationEventModel.email_received_at)",
    )

    embedding_record: Mapped[Optional["ApplicationEmbeddingModel"]] = relationship(
        back_populates="application",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_email_applications_company_id", "company_id"),
        Index("idx_email_applications_position_normalized", "position_normalized"),
        Index("idx_email_applications_external_job_id", "external_job_id"),
        Index("idx_email_applications_application_key", "application_key"),
        Index("idx_email_applications_status", "status"),
    )


class ApplicationEventModel(Base):
    __tablename__ = "email_application_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email_application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("email_applications.id", ondelete="CASCADE"), nullable=False
    )
    email_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_internet_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_conversation_id: Mapped[Optional[str]] = mapped_column(Text)
    email_sender: Mapped[Optional[str]] = mapped_column(Text)
    email_sender_name: Mapped[Optional[str]] = mapped_column(Text)
    email_subject: Mapped[Optional[str]] = mapped_column(Text)
    email_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    email_event_type: Mapped[str] = mapped_column(Text, nullable=False)
    email_status_after_event: Mapped[Optional[str]] = mapped_column(Text)
    email_summary: Mapped[Optional[str]] = mapped_column(Text)
    email_action_required: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    email_action: Mapped[Optional[str]] = mapped_column(Text)
    email_raw_body: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["ApplicationModel"] = relationship(back_populates="events")

    __table_args__ = (
        Index("idx_email_application_events_application_id", "email_application_id"),
        Index("idx_email_application_events_conversation_id", "email_conversation_id"),
        Index("idx_email_application_events_received_at", "email_received_at"),
        Index("idx_email_application_events_type", "email_event_type"),
    )


class ApplicationEmbeddingModel(Base):
    __tablename__ = "email_application_embeddings"

    email_application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("email_applications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    
    embedding: Mapped[List[float]] = mapped_column(Vector(768), nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["ApplicationModel"] = relationship(back_populates="embedding_record")

    __table_args__ = (
        Index(
            "email_application_embeddings_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class OtherEventModel(Base):
    __tablename__ = "email_other_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_internet_message_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    email_conversation_id: Mapped[Optional[str]] = mapped_column(Text)
    email_sender: Mapped[Optional[str]] = mapped_column(Text)
    email_sender_name: Mapped[Optional[str]] = mapped_column(Text)
    email_subject: Mapped[Optional[str]] = mapped_column(Text)
    email_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    email_type: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(Text)
    action_required: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    action: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    raw_body: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_email_other_events_conversation_id", "email_conversation_id"),
        Index("idx_email_other_events_received_at", "email_received_at"),
        Index("idx_email_other_events_type", "email_type"),
        Index(
            "idx_email_other_events_action_required",
            "action_required",
            postgresql_where=text("action_required = TRUE"),
        ),
    )