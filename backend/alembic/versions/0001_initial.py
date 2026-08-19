"""Initial migration containing full database schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import pgvector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ensure extensions exist
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # agent_chats
    op.create_table(
        "agent_chats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), server_default="New Chat", nullable=False),
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ai_providers
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.Text(), server_default="openai", nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("max_concurrency", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ai_task_bindings
    op.create_table(
        "ai_task_bindings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column(
            "extra_kwargs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["ai_providers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_task_bindings_task_type"),
        "ai_task_bindings",
        ["task_type"],
        unique=True,
    )

    # candidate_cvs
    op.create_table(
        "candidate_cvs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("anonymized_text", sa.Text(), nullable=True),
        sa.Column(
            "extracted_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("years_of_experience", sa.Float(), nullable=True),
        sa.Column(
            "domain_expertise",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # companies
    op.create_table(
        "email_companies",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalized", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_email_companies_name_normalized",
        "email_companies",
        ["name_normalized"],
        unique=True,
    )
    op.create_index("idx_email_companies_domain", "email_companies", ["domain"])
    op.create_index(
        "idx_email_companies_name_trgm",
        "email_companies",
        ["name_normalized"],
        postgresql_using="gin",
        postgresql_ops={"name_normalized": "gin_trgm_ops"},
    )

    # email_accounts
    op.create_table(
        "email_accounts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("email_address", sa.VARCHAR(length=255), nullable=False),
        sa.Column(
            "auth_type", sa.VARCHAR(length=50), server_default="IMAP", nullable=False
        ),
        sa.Column("imap_host", sa.VARCHAR(length=255), nullable=True),
        sa.Column("imap_port", sa.Integer(), server_default="993", nullable=True),
        sa.Column("username", sa.VARCHAR(length=255), nullable=True),
        sa.Column("app_password", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "folder", sa.VARCHAR(length=100), server_default="INBOX", nullable=False
        ),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("client_id", sa.VARCHAR(length=255), nullable=True),
        sa.Column("client_secret", sa.VARCHAR(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "sync_interval", sa.VARCHAR(length=50), server_default="1h", nullable=False
        ),
        sa.Column(
            "sync_schedule_time",
            sa.VARCHAR(length=20),
            server_default="09:00",
            nullable=True,
        ),
        sa.Column(
            "sync_schedule_day",
            sa.VARCHAR(length=20),
            server_default="MON",
            nullable=True,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_address"),
    )

    # email_applications
    op.create_table(
        "email_applications",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("position_normalized", sa.Text(), nullable=True),
        sa.Column("external_job_id", sa.Text(), nullable=True),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("application_key", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="APPLIED", nullable=False),
        sa.Column("application_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_guide_html", sa.Text(), nullable=True),
        sa.Column(
            "interview_guide_language", sa.Text(), server_default="en", nullable=True
        ),
        sa.Column(
            "interview_guide_generated_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "interview_guide_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["email_companies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # email_prompts
    op.create_table(
        "email_prompts",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("name"),
    )

    # intake_evaluation_tasks
    op.create_table(
        "intake_evaluation_tasks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "task_type", sa.Text(), server_default="JOB_ASSESSMENT", nullable=False
        ),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("title_hint", sa.Text(), server_default="Job Lead", nullable=False),
        sa.Column("status", sa.Text(), server_default="QUEUED", nullable=False),
        sa.Column("stage", sa.Text(), server_default="FETCHING", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # llm_configs
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # trace_events
    op.create_table(
        "trace_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), server_default="llm", nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_trace_events_category"), "trace_events", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_trace_events_run_id"), "trace_events", ["run_id"], unique=False
    )

    # email_application_events
    op.create_table(
        "email_application_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_application_id", sa.BigInteger(), nullable=False),
        sa.Column("email_message_id", sa.Text(), nullable=True),
        sa.Column("email_internet_message_id", sa.Text(), nullable=True),
        sa.Column("email_conversation_id", sa.Text(), nullable=True),
        sa.Column("email_sender", sa.Text(), nullable=True),
        sa.Column("email_sender_name", sa.Text(), nullable=True),
        sa.Column("email_subject", sa.Text(), nullable=True),
        sa.Column("email_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "email_event_type",
            sa.Text(),
            server_default="EMAIL_RECEIVED",
            nullable=False,
        ),
        sa.Column("email_status_after_event", sa.Text(), nullable=True),
        sa.Column("email_summary", sa.Text(), nullable=True),
        sa.Column(
            "email_action_required", sa.Boolean(), server_default="false", nullable=True
        ),
        sa.Column("email_action", sa.Text(), nullable=True),
        sa.Column("email_raw_body", sa.Text(), nullable=True),
        sa.Column("source_channel", sa.Text(), server_default="EMAIL", nullable=False),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_application_id"], ["email_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # email_processed_messages
    op.create_table(
        "email_processed_messages",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_account_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.VARCHAR(length=255), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_account_id"], ["email_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "email_account_id", "message_id", name="uix_account_message"
        ),
    )

    # email_staging_items
    op.create_table(
        "email_staging_items",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_account_id", sa.BigInteger(), nullable=True),
        sa.Column("email_message_id", sa.Text(), nullable=True),
        sa.Column("email_internet_message_id", sa.Text(), nullable=True),
        sa.Column("email_conversation_id", sa.Text(), nullable=True),
        sa.Column("email_sender", sa.Text(), nullable=True),
        sa.Column("email_sender_name", sa.Text(), nullable=True),
        sa.Column("email_subject", sa.Text(), nullable=True),
        sa.Column("email_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_raw_body", sa.Text(), nullable=True),
        sa.Column(
            "extracted_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="PENDING", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_account_id"], ["email_accounts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # job_postings
    op.create_table(
        "job_postings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_application_id", sa.BigInteger(), nullable=False),
        sa.Column("description_markdown", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Float(), nullable=True),
        sa.Column("salary_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), server_default="USD", nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("work_model", sa.Text(), nullable=True),
        sa.Column(
            "required_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=True,
        ),
        sa.Column(
            "structured_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_application_id"], ["email_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_application_id"),
    )

    # action_items
    op.create_table(
        "action_items",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_application_id", sa.BigInteger(), nullable=False),
        sa.Column("email_application_event_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_application_event_id"],
            ["email_application_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["email_application_id"], ["email_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # application_embeddings
    op.create_table(
        "application_embeddings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email_application_id", sa.BigInteger(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_application_id"], ["email_applications.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_application_id"),
    )


def downgrade() -> None:
    op.drop_table("application_embeddings")
    op.drop_table("action_items")
    op.drop_table("job_postings")
    op.drop_table("email_staging_items")
    op.drop_table("email_processed_messages")
    op.drop_table("email_application_events")
    op.drop_index(op.f("ix_trace_events_run_id"), table_name="trace_events")
    op.drop_index(op.f("ix_trace_events_category"), table_name="trace_events")
    op.drop_table("trace_events")
    op.drop_table("llm_configs")
    op.drop_table("intake_evaluation_tasks")
    op.drop_table("email_prompts")
    op.drop_table("email_applications")
    op.drop_table("email_accounts")
    op.drop_table("companies")
    op.drop_table("candidate_cvs")
    op.drop_index(op.f("ix_ai_task_bindings_task_type"), table_name="ai_task_bindings")
    op.drop_table("ai_task_bindings")
    op.drop_table("ai_providers")
    op.drop_table("agent_chats")
