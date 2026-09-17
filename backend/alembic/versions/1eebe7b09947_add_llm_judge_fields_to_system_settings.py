"""Add LLM Judge fields to system_settings

Revision ID: 1eebe7b09947
Revises: b3c4d5e6f7a8
Create Date: 2026-09-16 23:59:57.686017

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1eebe7b09947"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column(
            "enable_llm_judge",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "llm_judge_audit_cover_letter",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "llm_judge_audit_application_qa",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "llm_judge_audit_interview_guide",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "llm_judge_action",
            sa.String(length=50),
            server_default=sa.text("'auto_rewrite'"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "llm_judge_max_retries",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_settings", "llm_judge_max_retries")
    op.drop_column("system_settings", "llm_judge_action")
    op.drop_column("system_settings", "llm_judge_audit_interview_guide")
    op.drop_column("system_settings", "llm_judge_audit_application_qa")
    op.drop_column("system_settings", "llm_judge_audit_cover_letter")
    op.drop_column("system_settings", "enable_llm_judge")
