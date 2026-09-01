"""rename poc email tables and indexes

Revision ID: 2b3c4d5e6f7a
Revises: 0a1b2c3d4e5f
Create Date: 2026-09-02 00:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f7a"
down_revision: str = "0a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_RENAMES = [
    ("email_companies", "companies"),
    ("email_applications", "applications"),
    ("email_application_events", "application_events"),
    ("email_application_embeddings", "application_embeddings"),
    ("email_other_events", "other_events"),
    ("email_staging_items", "staging_items"),
    ("email_prompts", "system_prompts"),
    ("email_llm_configs", "llm_configs"),
]

INDEX_RENAMES = [
    ("idx_email_companies_name_normalized", "idx_companies_name_normalized"),
    ("idx_email_companies_domain", "idx_companies_domain"),
    ("idx_email_companies_name_trgm", "idx_companies_name_trgm"),
    ("idx_email_applications_company_id", "idx_applications_company_id"),
    (
        "idx_email_applications_position_normalized",
        "idx_applications_position_normalized",
    ),
    ("idx_email_applications_external_job_id", "idx_applications_external_job_id"),
    ("idx_email_applications_application_key", "idx_applications_application_key"),
    ("idx_email_applications_status", "idx_applications_status"),
    (
        "idx_email_application_events_application_id",
        "idx_application_events_application_id",
    ),
    ("idx_email_application_events_event_type", "idx_application_events_event_type"),
    ("idx_email_application_events_occurred_at", "idx_application_events_occurred_at"),
    (
        "idx_email_application_embeddings_application_id",
        "idx_application_embeddings_application_id",
    ),
    ("email_application_embeddings_idx", "application_embeddings_idx"),
    ("idx_email_other_events_event_type", "idx_other_events_event_type"),
    ("idx_email_other_events_occurred_at", "idx_other_events_occurred_at"),
    ("idx_email_other_events_conversation_id", "idx_other_events_conversation_id"),
    ("idx_email_other_events_received_at", "idx_other_events_received_at"),
    ("idx_email_other_events_action_required", "idx_other_events_action_required"),
    ("idx_email_staging_items_status", "idx_staging_items_status"),
    ("idx_email_staging_items_conversation_id", "idx_staging_items_conversation_id"),
    ("idx_email_staging_items_received_at", "idx_staging_items_received_at"),
]


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table_name)


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    # 1. If old tables exist and empty shadow tables exist (e.g. created by create_all()),
    # drop the empty shadow tables so the real production tables can be renamed in place.
    for old_name, new_name in TABLE_RENAMES:
        if _table_exists(old_name) and _table_exists(new_name):
            bind = op.get_bind()
            new_count = bind.execute(
                sa.text(f"SELECT count(*) FROM {new_name}")
            ).scalar()
            if new_count == 0:
                op.execute(f"DROP TABLE {new_name} CASCADE")

    # 2. Rename tables in-place
    for old_name, new_name in TABLE_RENAMES:
        if _table_exists(old_name) and not _table_exists(new_name):
            op.rename_table(old_name, new_name)

    # 3. Rename indexes
    for old_idx, new_idx in INDEX_RENAMES:
        if _index_exists(old_idx) and not _index_exists(new_idx):
            op.execute(f"ALTER INDEX {old_idx} RENAME TO {new_idx}")


def downgrade() -> None:
    # 1. Revert index names
    for old_idx, new_idx in INDEX_RENAMES:
        if _index_exists(new_idx) and not _index_exists(old_idx):
            op.execute(f"ALTER INDEX {new_idx} RENAME TO {old_idx}")

    # 2. Revert table names
    for old_name, new_name in TABLE_RENAMES:
        if _table_exists(new_name) and not _table_exists(old_name):
            op.rename_table(new_name, old_name)
