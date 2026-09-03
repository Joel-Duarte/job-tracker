"""Shared rate and concurrency controls for outbound web operations."""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


class TokenBucket:
    """A bounded token bucket implemented with scheduled token availability."""

    def __init__(self, capacity: int, refill_seconds: float) -> None:
        self._interval = refill_seconds
        self._capacity = capacity
        self._next_available = time.monotonic() - capacity * refill_seconds
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            scheduled = max(now, self._next_available)
            wait_seconds = scheduled - now
            self._next_available = scheduled + self._interval
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)


class WebOperationLimiter:
    """
    Limits web request bursts and simultaneous operations per provider.
    Enforces token buckets for external search providers (DDGS, SearXNG)
    and bounds maximum concurrency inherited from AI provider settings.
    """

    DDGS_MAX_CONCURRENCY = 2
    SEARXNG_MAX_CONCURRENCY = 5
    CAMOFOX_MAX_CONCURRENCY = 4

    def __init__(self) -> None:
        self._limiters: dict[
            str, tuple[int, asyncio.Semaphore, TokenBucket | None]
        ] = {}
        self._lock = asyncio.Lock()

    def resolve_concurrency(self, provider: str, requested_concurrency: int = 1) -> int:
        req = max(1, requested_concurrency)
        if provider == "ddgs":
            return min(req, self.DDGS_MAX_CONCURRENCY)
        if provider == "searxng":
            return min(req, self.SEARXNG_MAX_CONCURRENCY)
        return min(req, self.CAMOFOX_MAX_CONCURRENCY)

    async def _get_limiter(
        self, provider: str, concurrency_limit: int
    ) -> tuple[asyncio.Semaphore, TokenBucket | None]:
        actual_limit = self.resolve_concurrency(provider, concurrency_limit)
        async with self._lock:
            current = self._limiters.get(provider)
            if current and current[0] == actual_limit:
                return current[1], current[2]

            bucket: TokenBucket | None = None
            if provider == "ddgs":
                # Max 2 concurrent, 3 tokens capacity, 1 token / 2.0s refill
                bucket = TokenBucket(capacity=3, refill_seconds=2.0)
            elif provider == "searxng":
                # Max 5 concurrent, 10 tokens capacity, 2 tokens / 1.0s refill (0.5s per token)
                bucket = TokenBucket(capacity=10, refill_seconds=0.5)

            semaphore = asyncio.Semaphore(actual_limit)
            self._limiters[provider] = (actual_limit, semaphore, bucket)
            return semaphore, bucket

    @asynccontextmanager
    async def acquire(
        self, provider: str, concurrency_limit: int = 1
    ) -> AsyncGenerator[None, None]:
        semaphore, bucket = await self._get_limiter(provider, concurrency_limit)
        if bucket is not None:
            await bucket.acquire()
        await semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()


web_operation_limiter = WebOperationLimiter()
