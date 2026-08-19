import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def run():
    engine = create_async_engine(settings.get_database_url())
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(
            text(
                "ALTER TABLE email_applications ADD COLUMN IF NOT EXISTS match_analysis_payload JSONB;"
            )
        )
    await engine.dispose()


asyncio.run(run())
