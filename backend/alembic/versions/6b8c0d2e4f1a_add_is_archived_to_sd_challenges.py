"""Add is_archived column to system_design_challenges and align session mode default.

Revision ID: 6b8c0d2e4f1a
Revises: 5a7b9c1d3e5f
Create Date: 2026-11-15 14:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6b8c0d2e4f1a"
down_revision: str | Sequence[str] | None = "5a7b9c1d3e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("system_design_challenges"):
        cols = {
            col["name"] for col in inspector.get_columns("system_design_challenges")
        }
        if "is_archived" not in cols:
            op.add_column(
                "system_design_challenges",
                sa.Column(
                    "is_archived",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )

    if inspector.has_table("system_design_sessions"):
        op.alter_column(
            "system_design_sessions",
            "mode",
            server_default=sa.text("'ADAPTIVE'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("system_design_sessions"):
        op.alter_column(
            "system_design_sessions",
            "mode",
            server_default=sa.text("'INTERVIEW'"),
        )

    if inspector.has_table("system_design_challenges"):
        cols = {
            col["name"] for col in inspector.get_columns("system_design_challenges")
        }
        if "is_archived" in cols:
            op.drop_column("system_design_challenges", "is_archived")
