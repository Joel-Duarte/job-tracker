"""add cover letter fields and system settings

Revision ID: a1b2c3d4e5f6
Revises: 9b5f2a7c1d4e
Create Date: 2025-05-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9b5f2a7c1d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column(
            "enable_auto_cover_letter",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "cover_letter_match_threshold",
            sa.Integer(),
            nullable=False,
            server_default="70",
        ),
    )

    op.add_column(
        "email_applications", sa.Column("cover_letter_text", sa.Text(), nullable=True)
    )
    op.add_column(
        "email_applications", sa.Column("cover_letter_status", sa.Text(), nullable=True)
    )
    op.add_column(
        "email_applications",
        sa.Column(
            "cover_letter_generated_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("email_applications", "cover_letter_generated_at")
    op.drop_column("email_applications", "cover_letter_status")
    op.drop_column("email_applications", "cover_letter_text")

    op.drop_column("system_settings", "cover_letter_match_threshold")
    op.drop_column("system_settings", "enable_auto_cover_letter")
