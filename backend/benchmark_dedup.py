import asyncio
import time
import uuid
from collections import namedtuple

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select

from app.models.processed_email import ProcessedEmailModel

# Assuming we have a way to connect to a test database or just mock the DB execution
# To make it simple and self-contained, we'll setup a small in-memory SQLite for async,
# but since the project probably uses postgres based on previous logs, we'll mock the db.execute part to measure the overhead of looping vs batching.

class MockResult:
    def scalar_one_or_none(self):
        return None

class MockDB:
    async def execute(self, stmt):
        # simulate some slight async delay
        await asyncio.sleep(0.0001)
        return MockResult()

MockEmail = namedtuple("MockEmail", ["message_id", "subject", "body"])

async def benchmark_n_plus_one(db, raw_emails):
    start = time.perf_counter()
    skipped_duplicates = 0
    for email in raw_emails:
        mid = email.message_id
        if mid:
            existing = (await db.execute(
                select(ProcessedEmailModel.id).where(ProcessedEmailModel.message_id == mid)
            )).scalar_one_or_none()
            if existing is not None:
                skipped_duplicates += 1
    end = time.perf_counter()
    return end - start

async def benchmark_batch(db, raw_emails):
    start = time.perf_counter()
    skipped_duplicates = 0
    mids = [email.message_id for email in raw_emails if email.message_id]

    if mids:
        # simulate a single batched query
        await db.execute(
            select(ProcessedEmailModel.id).where(ProcessedEmailModel.message_id.in_(mids))
        )
        existing_mids = set() # mock empty result

        for email in raw_emails:
            if email.message_id in existing_mids:
                skipped_duplicates += 1

    end = time.perf_counter()
    return end - start

async def run_benchmark():
    db = MockDB()
    num_emails = 1000
    print(f"Benchmarking with {num_emails} mock emails...")

    raw_emails = [
        MockEmail(message_id=str(uuid.uuid4()), subject="test", body="test body")
        for _ in range(num_emails)
    ]

    n_plus_one_time = await benchmark_n_plus_one(db, raw_emails)
    print(f"N+1 Query implementation time: {n_plus_one_time:.4f} seconds")

    batch_time = await benchmark_batch(db, raw_emails)
    print(f"Batch implementation time: {batch_time:.4f} seconds")

    if batch_time > 0:
        speedup = n_plus_one_time / batch_time
        print(f"Speedup: {speedup:.2f}x")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
