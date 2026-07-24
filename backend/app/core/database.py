import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.models.applications import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.get_database_url(),
    echo=(settings.LOG_LEVEL == "DEBUG"),
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Tests the connection to PostgreSQL and logs the connected database name."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            logger.info(f"Successfully connected to database: '{db_name}'")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

async def ensure_db_schema() -> None:
    """Ensures required extensions exist, provisions any missing database tables 
    from metadata, and seeds default prompt entries into the database.
    """
    async with engine.begin() as conn:
        logger.info("Verifying database extensions and schema tables...")

        # 1. Ensure required PostgreSQL extensions exist
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        # 2. Create any missing tables defined in ORM metadata (idempotent)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema check completed.")

    # 3. Seed default prompts into email_prompts table if missing
    async with AsyncSessionLocal() as session:
        from app.core.prompts import seed_default_prompts
        await seed_default_prompts(session)