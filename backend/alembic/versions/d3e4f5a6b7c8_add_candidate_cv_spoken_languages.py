"""add candidate_cv spoken_languages column

Revision ID: d3e4f5a6b7c8
Revises: b2c3d4e5f6a7, c1d2e3f4a5b6, c2d3e4f5a6b7
Create Date: 2026-08-29 01:42:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: tuple[str, ...] = ("b2c3d4e5f6a7", "c1d2e3f4a5b6", "c2d3e4f5a6b7")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_cvs",
        sa.Column(
            "spoken_languages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_cvs", "spoken_languages")
