import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import check_db_connection, ensure_db_schema


@pytest.mark.docker
@pytest.mark.asyncio
async def test_ensure_db_schema_runs_alembic(db_session: AsyncSession):
    """Test that ensure_db_schema runs extensions and Alembic migrations successfully."""
    await db_session.execute(text("DROP SCHEMA public CASCADE"))
    await db_session.execute(text("CREATE SCHEMA public"))
    await db_session.commit()

    # Run schema verification / migration
    await ensure_db_schema()

    # Verify tables exist
    result = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
    )
    tables = {row[0] for row in result.all()}

    assert "alembic_version" in tables
    assert "email_applications" in tables
    assert "email_companies" in tables
    assert "ai_providers" in tables
    assert "trace_events" in tables


@pytest.mark.docker
@pytest.mark.asyncio
async def test_check_db_connection(db_session: AsyncSession):
    """Test check_db_connection utility function with database active."""
    is_connected = await check_db_connection()
    assert is_connected is True
