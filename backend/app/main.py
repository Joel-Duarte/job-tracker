import logging
from fastapi import FastAPI, Response, status

from contextlib import asynccontextmanager

from app.core.database import check_db_connection, ensure_db_schema
from app.routers import (
    action_items,
    admin,
    agent_chat,
    ai_config,
    applications,
    candidate_profile,
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

        # Initialize the checkpointer pool and tables
        from app.core.database import checkpointer_pool, postgres_saver
        logger.info("Opening LangGraph checkpointer pool...")
        await checkpointer_pool.open()
        await postgres_saver.setup()
    else:
        print("\n==================================================")
        print(" ERROR: Could not connect to the database!")
        print(" Please check your container or .env configuration.")
        print("==================================================\n")

    yield
    # Executed on shutdown
    logger.info("Shutting down application and disposing connection pools...")
    from app.core.database import engine, checkpointer_pool
    await engine.dispose()
    await checkpointer_pool.close()


app = FastAPI(
    title="Job Tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(intake.router, prefix="/api/v1")
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
app.include_router(llm.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check(response: Response):
    """
    Health check endpoint for application and database connectivity.
    Returns 200 OK if healthy, or 503 Service Unavailable if DB connection fails.
    """
    db_healthy = await check_db_connection()

    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }

    return {
        "status": "ok",
        "database": "connected",
    }
