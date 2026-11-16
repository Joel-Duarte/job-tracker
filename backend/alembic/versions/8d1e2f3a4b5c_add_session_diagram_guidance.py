"""Add diagram_guidance JSONB column to system_design_sessions.

Revision ID: 8d1e2f3a4b5c
Revises: 7c9d1e3f5a2b
Create Date: 2026-11-15 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d1e2f3a4b5c"
down_revision: str | None = "7c9d1e3f5a2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols = _existing_columns("system_design_sessions")
    if "diagram_guidance" not in cols:
        op.add_column(
            "system_design_sessions",
            sa.Column(
                "diagram_guidance",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    cols = _existing_columns("system_design_sessions")
    if "diagram_guidance" in cols:
        op.drop_column("system_design_sessions", "diagram_guidance")
