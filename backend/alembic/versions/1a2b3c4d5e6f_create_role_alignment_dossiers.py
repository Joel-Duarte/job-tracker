"""create role_alignment_dossiers table

Revision ID: 1a2b3c4d5e6f
Revises: f5a6b7c8d9e0
Create Date: 2026-09-01 23:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: str = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table_name)


def upgrade() -> None:
    if not _table_exists("role_alignment_dossiers"):
        op.create_table(
            "role_alignment_dossiers",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "cv_id",
                sa.BigInteger(),
                sa.ForeignKey("candidate_cvs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role_track", sa.Text(), nullable=False),
            sa.Column(
                "ai_payload",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
            sa.Column("model_name", sa.Text(), nullable=True),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "cv_id", "role_track", name="uq_role_alignment_dossier_cv_track"
            ),
        )
        op.create_index(
            "ix_role_alignment_dossiers_cv_id",
            "role_alignment_dossiers",
            ["cv_id"],
        )
        op.create_index(
            "ix_role_alignment_dossiers_role_track",
            "role_alignment_dossiers",
            ["role_track"],
        )
        op.create_index(
            "idx_role_alignment_dossier_track",
            "role_alignment_dossiers",
            ["role_track"],
        )


def downgrade() -> None:
    if _table_exists("role_alignment_dossiers"):
        op.drop_table("role_alignment_dossiers")
