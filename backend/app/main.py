from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import check_db_connection, get_db
from app.routers import applications, emails, events, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executed on startup
    logger.info("Checking database connection...")
    is_connected = await check_db_connection()
    if is_connected:
        print("\n==================================================")
        print(" SUCCESS: Database connection established! (pgvector)")
        print("==================================================\n")
    else:
        print("\n==================================================")
        print(" ERROR: Could not connect to the database!")
        print(" Please check your container or .env configuration.")
        print("==================================================\n")

    yield
    # Executed on shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title="Job Tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(emails.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


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