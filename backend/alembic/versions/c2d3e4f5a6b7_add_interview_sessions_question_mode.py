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


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table_name):
        return False
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists("interview_sessions", "question_mode"):
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
    if _column_exists("interview_sessions", "question_mode"):
        op.drop_column("interview_sessions", "question_mode")
