from fastapi import FastAPI
from app.routers import applications, emails, events, search

app = FastAPI(
    title="Job Tracking API",
    version="0.0.1",
)

# Register routers under unified API version prefix
app.include_router(emails.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}