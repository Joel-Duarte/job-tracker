"""encrypt runtime credentials stored in the database

Revision ID: 9b5f2a7c1d4e
Revises: f66de35140ce
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.security import encrypt_secret

revision: str = "9b5f2a7c1d4e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SECRET_COLUMNS = {
    "ai_providers": ("api_key",),
    "email_accounts": (
        "app_password",
        "access_token",
        "refresh_token",
        "client_secret",
    ),
    "email_llm_configs": ("api_key",),
}


def _encrypt_table_secrets(
    connection: sa.Connection, table_name: str, columns: tuple[str, ...]
) -> None:
    table = sa.table(
        table_name,
        sa.column("id", sa.BigInteger()),
        *(sa.column(column, sa.Text()) for column in columns),
    )
    rows = connection.execute(sa.select(table)).mappings().all()
    for row in rows:
        values = {
            column: encrypt_secret(row[column]) for column in columns if row[column]
        }
        if values:
            connection.execute(
                table.update().where(table.c.id == row["id"]).values(**values)
            )


def upgrade() -> None:
    connection = op.get_bind()
    for table_name, columns in _SECRET_COLUMNS.items():
        _encrypt_table_secrets(connection, table_name, columns)


def downgrade() -> None:
    # Encrypted values cannot be safely reverted to plaintext during downgrade.
    raise RuntimeError("Credential encryption migrations cannot be downgraded safely")
