"""add interview_sessions question_mode column

Revision ID: c2d3e4f5a6b7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23 01:06:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column(
            "question_mode",
            sa.Text(),
            nullable=False,
            server_default="TEXT_CONVERSATIONAL",
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "question_mode")
