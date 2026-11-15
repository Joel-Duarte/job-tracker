import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import check_db_connection, ensure_db_schema
from app.routers import (
    action_items,
    admin,
    agent_chat,
    ai_config,
    analytics,
    applications,
    candidate_profile,
    companies,
    diagnostics,
    email_accounts,
    events,
    extension,
    intake,
    interview_simulator,
    llm,
    metrics,
    prompts,
    search,
    staging,
    system,
    system_design,
    system_settings,
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

        await maybe_seed_dev_data(AsyncSessionLocal)

        # Initialize the checkpointer pool and tables
        from app.core.database import checkpointer_pool, postgres_saver

        logger.info("Opening LangGraph checkpointer pool...")
        await checkpointer_pool.open()
        await postgres_saver.setup()

        # Start the background workers (staleness archiver, VRAM watcher, queue recovery & dispatcher)
        import asyncio

        from app.core.ai_queue import idle_vram_watcher_loop, set_shutting_down
        from app.services.evaluation_worker import queue_recovery_and_dispatcher_loop
        from app.services.staleness_archiver import staleness_archiver_worker

        set_shutting_down(False)
        app.state.archiver_task = asyncio.create_task(
            staleness_archiver_worker(AsyncSessionLocal)
        )
        app.state.vram_watcher_task = asyncio.create_task(
            idle_vram_watcher_loop(AsyncSessionLocal)
        )
        app.state.queue_dispatcher_task = asyncio.create_task(
            queue_recovery_and_dispatcher_loop(AsyncSessionLocal)
        )
    else:
        print("\n==================================================")
        print(" ERROR: Could not connect to the database!")
        print(" Please check your container or .env configuration.")
        print("==================================================\n")

    yield
    # Executed on shutdown
    logger.info("Shutting down application and disposing connection pools...")
    import asyncio

    from app.core.ai_queue import (
        _RUNNING_TASKS,
        cancel_running_task,
        get_running_task_ids,
        set_shutting_down,
    )

    set_shutting_down(True)

    bg_tasks_to_stop = []
    for attr_name in ("archiver_task", "vram_watcher_task", "queue_dispatcher_task"):
        bg_t = getattr(app.state, attr_name, None)
        if bg_t and not bg_t.done():
            bg_t.cancel()
            bg_tasks_to_stop.append(bg_t)

    for tid in get_running_task_ids():
        running_t = _RUNNING_TASKS.get(tid)
        if running_t and not running_t.done():
            cancel_running_task(tid)
            bg_tasks_to_stop.append(running_t)

    if bg_tasks_to_stop:
        try:
            await asyncio.wait_for(
                asyncio.gather(*bg_tasks_to_stop, return_exceptions=True),
                timeout=5.0,
            )
        except Exception:
            pass

    from app.core.database import checkpointer_pool, engine

    await engine.dispose()
    await checkpointer_pool.close()


app = FastAPI(
    title="Job Tracking API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.PUBLIC_FRONTEND_URL:
    frontend_origin = settings.PUBLIC_FRONTEND_URL.rstrip("/")
    if frontend_origin not in cors_origins:
        cors_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(intake.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(candidate_profile.router, prefix="/api/v1")
app.include_router(extension.router, prefix="/api/v1")
app.include_router(agent_chat.router, prefix="/api/v1")
app.include_router(ai_config.config_ai_router, prefix="/api/v1")
app.include_router(ai_config.router, prefix="/api/v1")
app.include_router(system_settings.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(action_items.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(prompts.router, prefix="/api/v1")
app.include_router(email_accounts.router, prefix="/api/v1")
app.include_router(staging.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(diagnostics.router, prefix="/api/v1")
app.include_router(llm.router, prefix="/api/v1")
app.include_router(interview_simulator.router)
app.include_router(system_design.router)


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
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
