"""add company rating and research fields to companies

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-09-02 17:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e6f7a8b9c0d"
down_revision: str = "4d5e6f7a8b9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("rating", sa.Integer(), nullable=True))
    op.add_column("companies", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "companies",
        sa.Column(
            "pros",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "red_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "company_research",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "researched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "researched_at")
    op.drop_column("companies", "company_research")
    op.drop_column("companies", "red_flags")
    op.drop_column("companies", "pros")
    op.drop_column("companies", "notes")
    op.drop_column("companies", "rating")
