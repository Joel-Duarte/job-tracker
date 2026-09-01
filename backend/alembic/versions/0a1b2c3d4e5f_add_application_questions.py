"""add application_questions column

Revision ID: 0a1b2c3d4e5f
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
down_revision: str = "1a2b3c4d5e6f"
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
    if not _column_exists("email_applications", "application_questions"):
        op.add_column(
            "email_applications",
            sa.Column(
                "application_questions",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _column_exists("email_applications", "application_questions"):
        op.drop_column("email_applications", "application_questions")
