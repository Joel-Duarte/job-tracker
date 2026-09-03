"""add research_status and about_url to companies

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-09-02 23:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f7a8b9c0d1e"
down_revision: str = "5e6f7a8b9c0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # research_status: pipeline state for AI research jobs (NONE/QUEUED/IN_PROGRESS/COMPLETED/FAILED)
    op.add_column(
        "companies",
        sa.Column(
            "research_status",
            sa.Text(),
            nullable=False,
            server_default="NONE",
        ),
    )
    # about_url: user-provided "About Us" seed URL for the research scraper
    op.add_column(
        "companies",
        sa.Column("about_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "about_url")
    op.drop_column("companies", "research_status")
