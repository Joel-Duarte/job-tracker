"""add provider token cost columns

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-08-29 18:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str = "e4f5a6b7c8d9"
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
    if not _column_exists("ai_providers", "input_cost_per_million"):
        op.add_column(
            "ai_providers",
            sa.Column(
                "input_cost_per_million",
                sa.Float(),
                server_default=sa.text("0.0"),
                nullable=True,
            ),
        )
    if not _column_exists("ai_providers", "output_cost_per_million"):
        op.add_column(
            "ai_providers",
            sa.Column(
                "output_cost_per_million",
                sa.Float(),
                server_default=sa.text("0.0"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _column_exists("ai_providers", "output_cost_per_million"):
        op.drop_column("ai_providers", "output_cost_per_million")
    if _column_exists("ai_providers", "input_cost_per_million"):
        op.drop_column("ai_providers", "input_cost_per_million")
