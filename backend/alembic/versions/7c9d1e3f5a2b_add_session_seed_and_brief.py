"""Add brief_seed, variant_id, variant_selection_mode, and session_brief to system_design_sessions.

Revision ID: 7c9d1e3f5a2b
Revises: 6b8c0d2e4f1a
Create Date: 2026-11-15 19:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7c9d1e3f5a2b"
down_revision: str | Sequence[str] | None = "6b8c0d2e4f1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("system_design_sessions"):
        cols = {col["name"] for col in inspector.get_columns("system_design_sessions")}
        if "brief_seed" not in cols:
            op.add_column(
                "system_design_sessions",
                sa.Column("brief_seed", sa.Text(), nullable=True),
            )
        if "variant_id" not in cols:
            op.add_column(
                "system_design_sessions",
                sa.Column("variant_id", sa.Text(), nullable=True),
            )
        if "variant_selection_mode" not in cols:
            op.add_column(
                "system_design_sessions",
                sa.Column(
                    "variant_selection_mode",
                    sa.Text(),
                    nullable=False,
                    server_default=sa.text("'random'"),
                ),
            )
        if "session_brief" not in cols:
            op.add_column(
                "system_design_sessions",
                sa.Column(
                    "session_brief",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("system_design_sessions"):
        cols = {col["name"] for col in inspector.get_columns("system_design_sessions")}
        for col_name in (
            "session_brief",
            "variant_selection_mode",
            "variant_id",
            "brief_seed",
        ):
            if col_name in cols:
                op.drop_column("system_design_sessions", col_name)
