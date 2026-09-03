"""add cover_letter_tone to system_settings

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-09-03 22:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c0d1e2f3a4b"
down_revision: str = "8b9c0d1e2f3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column(
            "cover_letter_tone",
            sa.String(length=50),
            server_default=sa.text("'professional'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_settings", "cover_letter_tone")
