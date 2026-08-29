import os
import socket
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailPayload, ExtractedEmailInfo


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Checks if a TCP port is open and listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def pytest_collection_modifyitems(items):
    """Automatically marks tests requiring db_session or postgres_container with 'docker'."""
    for item in items:
        fixture_names = getattr(item, "fixturenames", [])
        if "db_session" in fixture_names or "postgres_container" in fixture_names:
            item.add_marker(pytest.mark.docker)


class FallbackPostgresConnection:
    """Mock connection provider wrapping an existing PostgreSQL database instance."""

    def __init__(self, url: str):
        self.url = url

    def get_connection_url(self) -> str:
        return self.url


@pytest.fixture(scope="session")
def postgres_container():
    """
    Provides a PostgreSQL connection URL for tests with a four-tier resolution hierarchy:
    1. Explicit TEST_DATABASE_URL environment variable.
    2. Ephemeral Testcontainer (pgvector/pgvector:pg16) if Docker daemon is accessible.
    3. Running local database container on localhost (port from POSTGRES_PORT or 54320).
    4. Graceful skip if neither Docker nor a local PostgreSQL database is reachable.
    """
    # 1. Check for explicit test database URL
    test_db_env = os.environ.get("TEST_DATABASE_URL")
    if test_db_env:
        yield FallbackPostgresConnection(test_db_env)
        return

    # 2. Try Testcontainers (standard isolated container per test session)
    try:
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("pgvector/pgvector:pg16") as postgres:
            yield postgres
            return
    except Exception as container_err:
        # 3. Fall back to running development database container if accessible
        local_port = int(os.environ.get("POSTGRES_PORT", 54320))
        if is_port_open("localhost", local_port):
            dev_db_url = f"postgresql+asyncpg://postgres:postgres@localhost:{local_port}/postgres"
            yield FallbackPostgresConnection(dev_db_url)
            return

        # 4. Gracefully skip with clear, actionable explanation
        pytest.skip(
            f"Docker daemon not accessible ({container_err}) and no PostgreSQL found on localhost:{local_port}. "
            "To run tests, start Docker (or run 'docker compose up -d db'), run './jt dev', "
            "or run pure unit tests with 'pytest -m \"not docker\"'."
        )


@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_container):
    """Provides an async DB session linked to the test container with required extensions."""
    raw_url = postgres_container.get_connection_url()

    if "postgresql+psycopg2://" in raw_url:
        async_url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif "postgresql://" in raw_url and "postgresql+asyncpg://" not in raw_url:
        async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_url = raw_url

    engine = create_async_engine(async_url, echo=False)

    # Enable required PostgreSQL extensions
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # Initialize checkpointer pool pointing to test container
    from psycopg_pool import AsyncConnectionPool

    import app.core.database as db_module

    sync_url = async_url.replace("+asyncpg", "")
    test_pool = AsyncConnectionPool(
        conninfo=sync_url,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        open=False,
    )
    await test_pool.open(wait=True)
    orig_engine = db_module.engine
    orig_session_local = db_module.AsyncSessionLocal
    orig_checkpointer_pool = db_module.checkpointer_pool
    orig_saver_conn = db_module.postgres_saver.conn

    db_module.engine = engine
    db_module.AsyncSessionLocal = session_factory
    db_module.checkpointer_pool = test_pool
    db_module.postgres_saver.conn = test_pool
    await db_module.postgres_saver.setup()

    try:
        async with session_factory() as session:
            yield session
    finally:
        db_module.engine = orig_engine
        db_module.AsyncSessionLocal = orig_session_local
        db_module.checkpointer_pool = orig_checkpointer_pool
        db_module.postgres_saver.conn = orig_saver_conn
        await test_pool.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def sample_email_account(db_session: AsyncSession):
    """Inserts a mock active Email Account into the database."""
    account = EmailAccountModel(
        name="Test Gmail",
        imap_host="imap.gmail.com",
        imap_port=993,
        username="test@gmail.com",
        app_password="test-app-password",
        folder="INBOX",
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
def mock_job_email_payload():
    """Provides sample job application email payload."""
    return EmailPayload(
        conversation_id="msg-stripe-1001",
        received_at=datetime.now(UTC),
        subject="Application Confirmation - Senior Backend Engineer",
        body="Thank you for applying to the Senior Backend Engineer position at Stripe.",
    )


@pytest.fixture
def mock_extracted_job_info():
    """Provides sample LLM extraction output."""
    return ExtractedEmailInfo(
        company="Stripe",
        position="Senior Backend Engineer",
        status="APPLIED",
        event_type="APPLICATION_SUBMITTED",
        summary="Application submitted for Senior Backend Engineer at Stripe.",
        action_required=False,
        action=None,
    )
