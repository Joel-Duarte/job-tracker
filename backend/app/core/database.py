import logging
from collections.abc import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver, Capabilities
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool
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

# Setup Postgres checkpointer for LangGraph
db_url = settings.get_database_url().replace("+asyncpg", "")

checkpointer_pool = AsyncConnectionPool(
    conninfo=db_url,
    max_size=10,
    kwargs={"autocommit": True, "prepare_threshold": 0},
    open=False,  # Do not open immediately, wait for async loop
)


class LazyAsyncPostgresSaver(AsyncPostgresSaver):
    def __init__(self, pool, pipe=None, serde=None):
        # Delay full loop binding because AsyncPostgresSaver calls asyncio.get_running_loop() on import
        self.conn = pool
        self.pipe = pipe
        self.serde = serde or JsonPlusSerializer()
        self.is_setup = False
        self._lock = None
        self._lock_loop = None
        self._loop = None
        self._supports_pipeline = None

    @property
    def lock(self):
        import asyncio

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._lock is None or self._lock_loop != current_loop:
            self._lock = asyncio.Lock()
            self._lock_loop = current_loop
        return self._lock

    @property
    def loop(self):
        import asyncio

        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return self._loop

    @loop.setter
    def loop(self, value):
        self._loop = value

    @property
    def supports_pipeline(self):
        if self._supports_pipeline is None:
            self._supports_pipeline = Capabilities().has_pipeline()
        return self._supports_pipeline

    def _ensure_thread_id(self, config: dict) -> dict:
        if config is not None:
            configurable = config.setdefault("configurable", {})
            if "thread_id" not in configurable:
                configurable["thread_id"] = "default"
        return config

    async def aget_tuple(self, config):
        self._ensure_thread_id(config)
        return await super().aget_tuple(config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        self._ensure_thread_id(config)
        return await super().aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        self._ensure_thread_id(config)
        return await super().aput_writes(config, writes, task_id, task_path)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        self._ensure_thread_id(config)
        return await super().alist(config, filter=filter, before=before, limit=limit)

    async def setup(self) -> None:
        if not hasattr(self, "loop") or self.loop is None:
            import asyncio

            self.loop = asyncio.get_running_loop()
        await super().setup()
        self.is_setup = True


postgres_saver = LazyAsyncPostgresSaver(checkpointer_pool)


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
    from metadata, and seeds default prompt entries and system settings.
    All schema modifications and column additions must be performed via Alembic migrations.
    """
    # Import all models to ensure complete metadata registration
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        logger.info("Verifying database extensions and schema tables...")

        # 1. Ensure required PostgreSQL extensions exist
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        except Exception as ext_err:
            logger.debug("Extension creation skipped: %s", ext_err)

        # 2. Create missing tables defined in ORM metadata (idempotent)
        await conn.run_sync(Base.metadata.create_all)

        # 2b. Ensure missing columns are added to existing tables
        from sqlalchemy import inspect

        def _sync_schema_columns(connection):
            inspector = inspect(connection)
            if "ai_providers" in inspector.get_table_names():
                cols = [c["name"] for c in inspector.get_columns("ai_providers")]
                if "is_fallback" not in cols:
                    connection.execute(
                        text(
                            "ALTER TABLE ai_providers ADD COLUMN is_fallback BOOLEAN NOT NULL DEFAULT FALSE;"
                        )
                    )

        await conn.run_sync(_sync_schema_columns)

        logger.info("Database schema check completed.")

    # 3. Seed default prompts and system settings if missing
    async with AsyncSessionLocal() as session:
        from app.core.config_manager import load_settings
        from app.core.prompts import seed_default_prompts

        await seed_default_prompts(session)
        await load_settings(session)
