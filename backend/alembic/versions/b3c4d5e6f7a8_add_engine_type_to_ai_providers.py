"""add engine_type to ai_providers

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-11 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str = "a2b3c4d5e6f7"
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
    if not _column_exists("ai_providers", "engine_type"):
        op.add_column(
            "ai_providers",
            sa.Column(
                "engine_type",
                sa.String(length=50),
                server_default=sa.text("'auto'"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _column_exists("ai_providers", "engine_type"):
        op.drop_column("ai_providers", "engine_type")
