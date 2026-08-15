from datetime import datetime
from typing import Any, Dict, List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    interview_guide_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interview_guide_language: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="en")
    interview_guide_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_guide_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["CompanyModel"] = relationship(back_populates="applications")
    events: Mapped[List["ApplicationEventModel"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(ApplicationEventModel.email_received_at)",
    )

    embedding_record: Mapped[Optional["ApplicationEmbeddingModel"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="application",
        uselist=False,
    )

    job_posting: Mapped[Optional["JobPostingModel"]] = relationship(
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )

    action_items: Mapped[List["ActionItemModel"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
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

    source_channel: Mapped[str] = mapped_column(Text, nullable=False, server_default="EMAIL")
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped["ApplicationModel"] = relationship(back_populates="events")
    action_items: Mapped[List["ActionItemModel"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_email_application_events_application_id", "email_application_id"),
        Index("idx_email_application_events_conversation_id", "email_conversation_id"),
        Index("idx_email_application_events_received_at", "email_received_at"),
        Index("idx_email_application_events_type", "email_event_type"),
    )


class JobPostingModel(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("email_applications.id", ondelete="CASCADE"), nullable=True
    )
    job_url: Mapped[str] = mapped_column(Text, nullable=False)
    description_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(Text, server_default="USD")
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Remote, Hybrid, Onsite
    required_skills: Mapped[List[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    application: Mapped[Optional["ApplicationModel"]] = relationship(back_populates="job_posting")

    __table_args__ = (
        Index("idx_job_postings_application_id", "application_id"),
        Index("idx_job_postings_job_url", "job_url"),
    )


class ActionItemModel(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("email_applications.id", ondelete="CASCADE"), nullable=True
    )
    event_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("email_application_events.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="PENDING")  # PENDING, COMPLETED, DISMISSED
    action_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(Text, server_default="MEDIUM")  # HIGH, MEDIUM, LOW
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    application: Mapped[Optional["ApplicationModel"]] = relationship(back_populates="action_items")
    event: Mapped[Optional["ApplicationEventModel"]] = relationship(back_populates="action_items")

    __table_args__ = (
        Index("idx_action_items_application_id", "application_id"),
        Index("idx_action_items_event_id", "event_id"),
        Index("idx_action_items_status", "status"),
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