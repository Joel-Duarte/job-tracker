"""Add system design challenges and sessions tables.

Revision ID: 5a7b9c1d3e5f
Revises: 4f6e8a1c3d5b
Create Date: 2026-11-15 01:26:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "5a7b9c1d3e5f"
down_revision: str | Sequence[str] | None = "4f6e8a1c3d5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_index(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
) -> None:
    existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("system_design_challenges"):
        op.create_table(
            "system_design_challenges",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column("slug", sa.Text(), nullable=False, unique=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column(
                "category",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'DISTRIBUTED_SYSTEMS'"),
            ),
            sa.Column(
                "difficulty",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'MEDIUM'"),
            ),
            sa.Column("prompt_summary", sa.Text(), nullable=False),
            sa.Column("initial_prompt", sa.Text(), nullable=False),
            sa.Column(
                "tags",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "interviewer_brief",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "is_builtin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )
        inspector.clear_cache()

    _ensure_index(
        inspector,
        "system_design_challenges",
        "idx_sd_challenges_category",
        ["category"],
    )
    _ensure_index(
        inspector,
        "system_design_challenges",
        "idx_sd_challenges_difficulty",
        ["difficulty"],
    )

    if not inspector.has_table("system_design_sessions"):
        op.create_table(
            "system_design_sessions",
            sa.Column("id", sa.BigInteger(), primary_key=True),
            sa.Column(
                "challenge_id",
                sa.BigInteger(),
                sa.ForeignKey("system_design_challenges.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "application_id",
                sa.BigInteger(),
                sa.ForeignKey("applications.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "mode",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'INTERVIEW'"),
            ),
            sa.Column(
                "stage",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'REQUIREMENTS'"),
            ),
            sa.Column(
                "status",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'IN_PROGRESS'"),
            ),
            sa.Column(
                "requirements_transcript",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "requirements_ledger",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "diagrams_metadata",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "architecture_reviews",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "defence_transcript",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("final_evaluation", postgresql.JSONB(), nullable=True),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("readiness_rating", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        inspector.clear_cache()

    _ensure_index(
        inspector,
        "system_design_sessions",
        "idx_sd_sessions_challenge_id",
        ["challenge_id"],
    )
    _ensure_index(
        inspector,
        "system_design_sessions",
        "idx_sd_sessions_status",
        ["status"],
    )
    _ensure_index(
        inspector,
        "system_design_sessions",
        "idx_sd_sessions_stage",
        ["stage"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("system_design_sessions"):
        op.drop_table("system_design_sessions")
    if inspector.has_table("system_design_challenges"):
        op.drop_table("system_design_challenges")
