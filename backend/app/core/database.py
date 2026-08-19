import logging
import os
from collections.abc import AsyncGenerator

from alembic.config import Config
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver, Capabilities
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import settings

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


def run_alembic_upgrade(connection) -> None:
    """Runs Alembic migrations using the provided database connection."""
    # Locate alembic.ini relative to this file or current working directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ini_path = os.path.join(base_dir, "alembic.ini")

    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    alembic_cfg.attributes["connection"] = connection

    command.upgrade(alembic_cfg, "head")


async def ensure_db_schema() -> None:
    """Ensures required extensions exist, runs Alembic migrations, and seeds default prompts."""
    async with engine.begin() as conn:
        logger.info("Verifying database extensions and schema migrations...")

        # 1. Ensure required PostgreSQL extensions exist
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        # 2. Run Alembic migrations programmatically
        await conn.run_sync(run_alembic_upgrade)

        logger.info(
            "Database schema check and Alembic migrations completed successfully."
        )

    # 3. Seed default prompts into email_prompts table if missing
    async with AsyncSessionLocal() as session:
        from app.core.prompts import seed_default_prompts

        await seed_default_prompts(session)
