"""add durable assessment identity to applications

Revision ID: 7a8b9c0d1e2f
Revises: f5a6b7c8d9e0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a8b9c0d1e2f"
down_revision: str | tuple[str, str] = ("6f7a8b9c0d1e", "f5a6b7c8d9e0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column(
            "is_assessment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE applications SET is_assessment = true "
            "WHERE status = 'ASSESSMENT' OR "
            "(status = 'ARCHIVED' AND match_analysis_payload IS NOT NULL)"
        )
    )


def downgrade() -> None:
    op.drop_column("applications", "is_assessment")