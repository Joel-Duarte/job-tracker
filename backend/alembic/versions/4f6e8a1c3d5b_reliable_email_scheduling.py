"""Persist email scheduling provenance and display timezone without reinterpreting legacy dates."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "4f6e8a1c3d5b"
down_revision = "1eebe7b09947"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "system_settings", sa.Column("display_timezone", sa.String(100), nullable=True)
    )
    op.add_column(
        "system_settings",
        sa.Column(
            "timezone_source", sa.String(16), nullable=False, server_default="auto"
        ),
    )
    op.add_column(
        "action_items",
        sa.Column("temporal_metadata", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "email_calendar_occurrences",
        sa.Column("identity_key", sa.Text(), primary_key=True),
        sa.Column(
            "application_id",
            sa.BigInteger(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calendar_data", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_email_calendar_occurrences_application_id",
        "email_calendar_occurrences",
        ["application_id"],
    )


def downgrade():
    op.drop_table("email_calendar_occurrences")
    op.drop_column("action_items", "temporal_metadata")
    op.drop_column("system_settings", "timezone_source")
    op.drop_column("system_settings", "display_timezone")
