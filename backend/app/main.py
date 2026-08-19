import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from app.core.database import check_db_connection, ensure_db_schema
from app.routers import (
    action_items,
    admin,
    agent_chat,
    ai_config,
    analytics,
    applications,
    candidate_profile,
    diagnostics,
    email_accounts,
    events,
    extension,
    intake,
    llm,
    prompts,
    search,
    staging,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executed on startup
    logger.info("Checking database connection...")
    is_connected = await check_db_connection()

    if is_connected:
        print("\n==================================================")
        print(" SUCCESS: Database connection established!")
        print("==================================================\n")

        # Verify schema exists or create tables and indexes
        await ensure_db_schema()

        # Seed mock development dataset if started in development mode on clean database
        from app.core.database import AsyncSessionLocal
        from app.services.seed_data import maybe_seed_dev_data

        app.state.db_connected = True
        try:
            await maybe_seed_dev_data(AsyncSessionLocal)
        except Exception as seed_err:
            logger.error(
                "Error during automatic development data seeding: %s",
                seed_err,
                exc_info=True,
            )

        # Initialize the checkpointer pool and tables
        from app.core.database import checkpointer_pool, postgres_saver

        logger.info("Opening LangGraph checkpointer pool...")
        await checkpointer_pool.open()
        await postgres_saver.setup()

        # Start the background worker for staleness archiver
        import asyncio

        from app.services.staleness_archiver import staleness_archiver_worker

        app.state.archiver_task = asyncio.create_task(
            staleness_archiver_worker(AsyncSessionLocal)
        )
    else:
        print("\n==================================================")
        print(" ERROR: Could not connect to the database!")
        print(" Initializing In-Memory Fallback Repository from seed_data.py...")
        print("==================================================\n")
        from app.services.fallback_store import get_fallback_repository

        app.state.db_connected = False
        app.state.fallback_repo = get_fallback_repository()
        logger.info(
            "In-Memory Fallback Repository initialized with dataset stats: %s",
            app.state.fallback_repo.get_stats(),
        )

    yield
    # Executed on shutdown
    logger.info("Shutting down application and disposing connection pools...")

    archiver_task = getattr(app.state, "archiver_task", None)
    if archiver_task:
        archiver_task.cancel()

    from app.core.database import checkpointer_pool, engine

    if is_connected:
        await engine.dispose()
        await checkpointer_pool.close()


app = FastAPI(
    title="Job Tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(intake.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(candidate_profile.router, prefix="/api/v1")
app.include_router(extension.router, prefix="/api/v1")
app.include_router(agent_chat.router, prefix="/api/v1")
app.include_router(ai_config.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(action_items.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(prompts.router, prefix="/api/v1")
app.include_router(email_accounts.router, prefix="/api/v1")
app.include_router(staging.router, prefix="/api/v1")
app.include_router(diagnostics.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check(response: Response):
    """
    Health check endpoint for application and database connectivity.
    Returns 200 OK if healthy, or degraded status if running on fallback memory store.
    """
    db_healthy = await check_db_connection()

    if not db_healthy:
        fallback_repo = getattr(app.state, "fallback_repo", None)
        if fallback_repo is None:
            from app.services.fallback_store import get_fallback_repository

            fallback_repo = get_fallback_repository()
            app.state.fallback_repo = fallback_repo

        response.status_code = status.HTTP_200_OK
        return {
            "status": "degraded",
            "database": "disconnected",
            "fallback_mode": "in_memory_repository",
            "message": "Operating using in-memory fallback state repository from seed_data.py",
            "fallback_stats": fallback_repo.get_stats(),
        }

    return {
        "status": "ok",
        "database": "connected",
    }
