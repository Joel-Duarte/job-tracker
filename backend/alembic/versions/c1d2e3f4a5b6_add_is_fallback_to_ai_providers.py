"""add is_fallback to ai_providers

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2025-05-20 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
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
    if not _column_exists("ai_providers", "is_fallback"):
        op.add_column(
            "ai_providers",
            sa.Column(
                "is_fallback",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )


def downgrade() -> None:
    if _column_exists("ai_providers", "is_fallback"):
        op.drop_column("ai_providers", "is_fallback")
