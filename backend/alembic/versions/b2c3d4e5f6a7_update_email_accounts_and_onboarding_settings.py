"""update email accounts column types and add onboarding settings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-22 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table_name):
        return False
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 1. Expand email_accounts folder and secret columns to Text for OAuth/Graph long IDs
    if _column_exists("email_accounts", "folder"):
        op.alter_column(
            "email_accounts",
            "folder",
            existing_type=sa.String(length=100),
            type_=sa.Text(),
            existing_nullable=True,
        )
    if _column_exists("email_accounts", "client_secret"):
        op.alter_column(
            "email_accounts",
            "client_secret",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )
    if _column_exists("email_accounts", "app_password"):
        op.alter_column(
            "email_accounts",
            "app_password",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )

    # 2. Add onboarding & email intake toggles to system_settings
    if not _column_exists("system_settings", "has_completed_onboarding"):
        op.add_column(
            "system_settings",
            sa.Column(
                "has_completed_onboarding",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )
    if not _column_exists("system_settings", "enable_email_intake"):
        op.add_column(
            "system_settings",
            sa.Column(
                "enable_email_intake",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )


def downgrade() -> None:
    if _column_exists("system_settings", "enable_email_intake"):
        op.drop_column("system_settings", "enable_email_intake")
    if _column_exists("system_settings", "has_completed_onboarding"):
        op.drop_column("system_settings", "has_completed_onboarding")

    if _column_exists("email_accounts", "app_password"):
        op.alter_column(
            "email_accounts",
            "app_password",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
    if _column_exists("email_accounts", "client_secret"):
        op.alter_column(
            "email_accounts",
            "client_secret",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
    if _column_exists("email_accounts", "folder"):
        op.alter_column(
            "email_accounts",
            "folder",
            existing_type=sa.Text(),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
