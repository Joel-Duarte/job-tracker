import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

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
    """Checks if database tables exist. If missing, installs extensions and creates schema from models."""
    async with engine.begin() as conn:
        # 1. Check if the core table exists
        result = await conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'public' AND table_name = 'email_applications'"
                ");"
            )
        )
        schema_exists = result.scalar()

        if schema_exists:
            logger.info("Database schema check passed. Core tables found.")
            return

        logger.warning("Database schema incomplete or missing. Initializing database schema...")

        # 2. Required extensions must be created explicitly before table creation
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        # 3. Create tables and custom indexes defined in models
        await conn.run_sync(Base.metadata.create_all)

        logger.info("Database schema successfully initialized.")