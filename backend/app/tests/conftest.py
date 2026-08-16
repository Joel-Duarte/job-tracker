from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.database import Base
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailPayload, ExtractedEmailInfo


@pytest.fixture(scope="session")
def postgres_container():
    """Spins up a temporary Postgres container with pgvector for testing."""
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_container):
    """Provides an async DB session linked to the test container with required extensions."""
    raw_url = postgres_container.get_connection_url()

    if "postgresql+psycopg2://" in raw_url:
        async_url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    else:
        async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url, echo=False)

    # Enable required PostgreSQL extensions
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Initialize checkpointer pool pointing to test container
    from app.core.database import checkpointer_pool, postgres_saver
    sync_url = async_url.replace("+asyncpg", "")
    checkpointer_pool.conninfo = sync_url
    await checkpointer_pool.open()
    await postgres_saver.setup()

    async with session_factory() as session:
        yield session

    # Drop tables after test run
    await checkpointer_pool.close()
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
        received_at=datetime.now(timezone.utc),
        subject="Interview Invitation - Senior Backend Engineer",
        body="Hi developer, we loved your profile and want to invite you to an interview at Stripe.",
    )


@pytest.fixture
def mock_extracted_job_info():
    """Provides sample LLM extraction output."""
    return ExtractedEmailInfo(
        company="Stripe",
        position="Senior Backend Engineer",
        status="INTERVIEW",
        event_type="INTERVIEW_INVITE",
        summary="Invited for interview at Stripe.",
        action_required=True,
        action="Schedule interview link.",
    )