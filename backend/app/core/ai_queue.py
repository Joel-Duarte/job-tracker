import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class ProviderConcurrencyManager:
    """
    Manages per-provider concurrency pools using dynamic asyncio.Semaphore instances.
    Prevents GPU VRAM thrashing on local providers (LM Studio, Ollama) while allowing
    higher parallel throughput for cloud providers (OpenAI, Gemini, Anthropic).
    """

    def __init__(self) -> None:
        self._semaphores: dict[int, tuple[int, asyncio.Semaphore]] = {}
        self._lock = asyncio.Lock()
        self._default_semaphore = asyncio.Semaphore(5)

    async def get_semaphore(self, provider_id: int | None, max_concurrency: int = 1) -> asyncio.Semaphore:
        if provider_id is None:
            return self._default_semaphore

        limit = max(1, max_concurrency)
        async with self._lock:
            if provider_id in self._semaphores:
                curr_limit, sem = self._semaphores[provider_id]
                if curr_limit == limit:
                    return sem
                # If concurrency changed in settings, update pool
                logger.info(
                    "Updating concurrency pool for provider %d from %d to %d",
                    provider_id,
                    curr_limit,
                    limit,
                )

            sem = asyncio.Semaphore(limit)
            self._semaphores[provider_id] = (limit, sem)
            return sem

    @asynccontextmanager
    async def acquire(self, provider_id: int | None, max_concurrency: int = 1) -> AsyncGenerator[None, None]:
        sem = await self.get_semaphore(provider_id, max_concurrency)
        async with sem:
            yield


# Global singleton instance
concurrency_manager = ProviderConcurrencyManager()
