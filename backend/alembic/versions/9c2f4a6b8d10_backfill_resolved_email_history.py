"""Backfill automatically processed emails into staging history.

Revision ID: 9c2f4a6b8d10
Revises: 8d1e2f3a4b5c
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c2f4a6b8d10"
down_revision: str | None = "8d1e2f3a4b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE system_settings SET enable_embeddings = false"))
    op.execute(
        sa.text("DELETE FROM intake_evaluation_tasks WHERE task_type = 'EMBEDDING'")
    )
    op.execute(sa.text("DELETE FROM ai_task_bindings WHERE task_type = 'EMBEDDING'"))
    op.execute(
        sa.text(
            """
            INSERT INTO staging_items (
                email_message_id,
                email_internet_message_id,
                email_conversation_id,
                email_sender,
                email_sender_name,
                email_subject,
                email_received_at,
                email_raw_body,
                extracted_data,
                match_score,
                match_reason,
                status
            )
            SELECT
                e.email_message_id,
                e.email_internet_message_id,
                e.email_conversation_id,
                e.email_sender,
                e.email_sender_name,
                e.email_subject,
                e.email_received_at,
                e.email_raw_body,
                jsonb_build_object(
                    'company', c.name,
                    'position', a.position,
                    'status', e.email_status_after_event,
                    'event_type', e.email_event_type,
                    'summary', e.email_summary,
                    'action_required', e.email_action_required,
                    'action', e.email_action,
                    '_application_id', a.id,
                    '_application_event_id', e.id,
                    '_previous_application_status', NULL
                ) || COALESCE(e.raw_payload, '{}'::jsonb),
                1.0,
                'AUTO_PROCESSED_EMAIL',
                'PROCESSED'
            FROM application_events e
            JOIN applications a ON a.id = e.email_application_id
            JOIN companies c ON c.id = a.company_id
            WHERE e.email_message_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM staging_items s
                  WHERE s.email_message_id = e.email_message_id
                     OR (
                         e.email_internet_message_id IS NOT NULL
                         AND s.email_internet_message_id = e.email_internet_message_id
                     )
              )
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO staging_items (
                email_message_id,
                email_internet_message_id,
                email_conversation_id,
                email_sender,
                email_sender_name,
                email_subject,
                email_received_at,
                email_raw_body,
                extracted_data,
                match_score,
                match_reason,
                status
            )
            SELECT
                o.email_message_id,
                o.email_internet_message_id,
                o.email_conversation_id,
                o.email_sender,
                o.email_sender_name,
                o.email_subject,
                o.email_received_at,
                o.raw_body,
                jsonb_build_object(
                    'email_type', o.email_type,
                    'summary', o.summary,
                    'action_required', o.action_required,
                    'action', o.action,
                    '_other_event_id', o.id
                ),
                1.0,
                'AUTO_PROCESSED_OTHER_EMAIL',
                'PROCESSED'
            FROM other_events o
            WHERE o.email_message_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM staging_items s
                  WHERE s.email_message_id = o.email_message_id
                     OR (
                         o.email_internet_message_id IS NOT NULL
                         AND s.email_internet_message_id = o.email_internet_message_id
                     )
              )
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # History rows may have been edited after the upgrade, so they are retained.
    pass
