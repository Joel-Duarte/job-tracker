"""add auto_release_vram_minutes to ai_providers

Revision ID: a2b3c4d5e6f7
Revises: 9c0d1e2f3a4b
Create Date: 2026-09-10 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str = "9c0d1e2f3a4b"
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
    if not _column_exists("ai_providers", "auto_release_vram_minutes"):
        op.add_column(
            "ai_providers",
            sa.Column(
                "auto_release_vram_minutes",
                sa.Integer(),
                server_default=sa.text("10"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _column_exists("ai_providers", "auto_release_vram_minutes"):
        op.drop_column("ai_providers", "auto_release_vram_minutes")
