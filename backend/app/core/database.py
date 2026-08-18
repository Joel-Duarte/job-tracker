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
    from metadata, ensures all expected columns exist on existing tables, and seeds default prompt entries.
    """
    # Import all models to ensure complete metadata registration
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        logger.info("Verifying database extensions and schema tables...")

        # 1. Ensure required PostgreSQL extensions exist
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        # 2. Create any missing tables defined in ORM metadata (idempotent)
        await conn.run_sync(Base.metadata.create_all)

        # 3. Explicit column migrations for existing tables (idempotent ADD COLUMN IF NOT EXISTS)
        migration_statements = [
            # ai_providers
            "ALTER TABLE IF EXISTS ai_providers ADD COLUMN IF NOT EXISTS max_concurrency INTEGER NOT NULL DEFAULT 1;",
            "ALTER TABLE IF EXISTS ai_providers ADD COLUMN IF NOT EXISTS api_key TEXT;",
            "ALTER TABLE IF EXISTS ai_providers ADD COLUMN IF NOT EXISTS base_url TEXT;",
            "ALTER TABLE IF EXISTS ai_providers ADD COLUMN IF NOT EXISTS provider_type TEXT NOT NULL DEFAULT 'openai';",
            "ALTER TABLE IF EXISTS ai_providers ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;",
            # ai_task_bindings
            "ALTER TABLE IF EXISTS ai_task_bindings ADD COLUMN IF NOT EXISTS max_tokens INTEGER;",
            "ALTER TABLE IF EXISTS ai_task_bindings ADD COLUMN IF NOT EXISTS top_p FLOAT;",
            "ALTER TABLE IF EXISTS ai_task_bindings ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER;",
            "ALTER TABLE IF EXISTS ai_task_bindings ADD COLUMN IF NOT EXISTS extra_kwargs JSONB DEFAULT '{}'::jsonb;",
            "ALTER TABLE IF EXISTS ai_task_bindings ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;",
            # email_applications
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS position_normalized TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS external_job_id TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS job_url TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS application_key TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'APPLIED';",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS application_date TIMESTAMPTZ;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS interview_guide_html TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS interview_guide_language TEXT DEFAULT 'en';",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS interview_guide_generated_at TIMESTAMPTZ;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS interview_guide_preferences JSONB;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS cover_letter_markdown TEXT;",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS cover_letter_status TEXT DEFAULT 'PENDING';",
            "ALTER TABLE IF EXISTS email_applications ADD COLUMN IF NOT EXISTS cover_letter_highlighted_skills JSONB DEFAULT '[]'::jsonb;",
            # job_postings
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS description_markdown TEXT;",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS salary_min FLOAT;",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS salary_max FLOAT;",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD';",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS location TEXT;",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS work_model TEXT;",
            "ALTER TABLE IF EXISTS job_postings ADD COLUMN IF NOT EXISTS required_skills JSONB DEFAULT '[]'::jsonb;",
            # email_application_events
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_message_id TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_internet_message_id TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_conversation_id TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_sender TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_sender_name TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_subject TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_received_at TIMESTAMPTZ;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_event_type TEXT NOT NULL DEFAULT 'EMAIL_RECEIVED';",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_status_after_event TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_summary TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_action_required BOOLEAN DEFAULT false;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_action TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS email_raw_body TEXT;",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'EMAIL';",
            "ALTER TABLE IF EXISTS email_application_events ADD COLUMN IF NOT EXISTS raw_payload JSONB;",
            # candidate_cvs
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS anonymized_text TEXT;",
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS extracted_skills JSONB DEFAULT '[]'::jsonb;",
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS years_of_experience FLOAT;",
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS domain_expertise JSONB DEFAULT '[]'::jsonb;",
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS summary TEXT;",
            "ALTER TABLE IF EXISTS candidate_cvs ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;",
            # intake_evaluation_tasks
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS task_type TEXT NOT NULL DEFAULT 'JOB_ASSESSMENT';",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS job_url TEXT;",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS raw_text TEXT;",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS title_hint TEXT NOT NULL DEFAULT 'Job Lead';",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'QUEUED';",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS stage TEXT NOT NULL DEFAULT 'FETCHING';",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS error_message TEXT;",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS result_json JSONB;",
            "ALTER TABLE IF EXISTS intake_evaluation_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;",
            # email_accounts
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS auth_type VARCHAR(50) NOT NULL DEFAULT 'IMAP';",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS imap_host VARCHAR(255);",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS imap_port INTEGER DEFAULT 993;",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS username VARCHAR(255);",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS app_password VARCHAR(255);",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS folder VARCHAR(100) NOT NULL DEFAULT 'INBOX';",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS access_token TEXT;",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS refresh_token TEXT;",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS client_id VARCHAR(255);",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS client_secret VARCHAR(255);",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS sync_interval VARCHAR(50) NOT NULL DEFAULT '1h';",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS sync_schedule_time VARCHAR(20) DEFAULT '09:00';",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS sync_schedule_day VARCHAR(20) DEFAULT 'MON';",
            "ALTER TABLE IF EXISTS email_accounts ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;",
            "UPDATE email_accounts SET sync_interval = '1h' WHERE sync_interval IS NULL;",
            "UPDATE email_accounts SET sync_schedule_time = '09:00' WHERE sync_schedule_time IS NULL;",
            "UPDATE email_accounts SET sync_schedule_day = 'MON' WHERE sync_schedule_day IS NULL;",
            # email_staging_items
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_account_id BIGINT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_message_id TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_internet_message_id TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_conversation_id TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_sender TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_sender_name TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_subject TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_received_at TIMESTAMPTZ;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS email_raw_body TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS extracted_data JSONB DEFAULT '{}'::jsonb;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS match_score FLOAT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS match_reason TEXT;",
            "ALTER TABLE IF EXISTS email_staging_items ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PENDING';",
            # trace_events
            "ALTER TABLE IF EXISTS trace_events ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'llm';",
        ]

        for stmt in migration_statements:
            await conn.execute(text(stmt))

        logger.info("Database schema check and automatic column migration completed.")

    # 4. Seed default prompts into email_prompts table if missing
    async with AsyncSessionLocal() as session:
        from app.core.prompts import seed_default_prompts

        await seed_default_prompts(session)
