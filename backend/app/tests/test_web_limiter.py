import asyncio

import pytest

from app.services.web_limiter import TokenBucket, WebOperationLimiter


@pytest.mark.asyncio
async def test_token_bucket_burst_and_rate_limit():
    bucket = TokenBucket(capacity=2, refill_seconds=0.1)
    # First 2 acquire immediately from capacity
    await bucket.acquire()
    await bucket.acquire()

    start = asyncio.get_running_loop().time()
    await bucket.acquire()
    duration = asyncio.get_running_loop().time() - start
    assert duration >= 0.08  # Had to wait ~0.1s for refill


@pytest.mark.asyncio
async def test_web_operation_limiter_concurrency_caps():
    limiter = WebOperationLimiter()
    # Requested 10, but DDGS should cap at 2
    assert limiter.resolve_concurrency("ddgs", 10) == 2
    # Requested 10, but SearXNG should cap at 5
    assert limiter.resolve_concurrency("searxng", 10) == 5
    # Requested 10, Camofox caps at 4
    assert limiter.resolve_concurrency("camofox", 10) == 4
    # Minimum 1
    assert limiter.resolve_concurrency("ddgs", 0) == 1


@pytest.mark.asyncio
async def test_web_operation_limiter_acquire_context():
    limiter = WebOperationLimiter()
    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        async with limiter.acquire("ddgs", concurrency_limit=2):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(*(worker() for _ in range(4)))
    assert max_active <= 2
