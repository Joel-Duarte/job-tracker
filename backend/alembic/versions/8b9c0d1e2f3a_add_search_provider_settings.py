"""add search_provider and searxng_url to system_settings

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-09-03 21:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b9c0d1e2f3a"
down_revision: str = "7a8b9c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column(
            "search_provider",
            sa.String(length=20),
            server_default=sa.text("'automatic'"),
            nullable=False,
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "searxng_url",
            sa.String(length=500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_settings", "searxng_url")
    op.drop_column("system_settings", "search_provider")
