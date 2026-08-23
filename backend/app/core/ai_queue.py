import asyncio
import heapq
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PrioritySemaphore:
    """
    A semaphore that grants locks based on priority.
    Waiters with a lower priority number execute first.
    """

    def __init__(self, value: int = 1):
        self._value = value
        self._waiters = []
        self._count = 0  # Tie-breaker for tasks with the same priority
        self._lock = asyncio.Lock()

    async def acquire(self, priority: int = 1):
        async with self._lock:
            if self._value > 0:
                self._value -= 1
                return True

            fut = asyncio.Future()
            self._count += 1
            # heapq sorts by first element (priority), then insertion order (self._count)
            heapq.heappush(self._waiters, (priority, self._count, fut))

        try:
            await fut
            return True
        except asyncio.CancelledError:
            async with self._lock:
                # Clean up if the task is cancelled while waiting
                waiter_item = (priority, self._count, fut)
                if waiter_item in self._waiters:
                    self._waiters.remove(waiter_item)
                    heapq.heapify(self._waiters)
            raise

    async def release(self):
        async with self._lock:
            self._value += 1
            while self._waiters:
                _, _, fut = heapq.heappop(self._waiters)
                if not fut.done():
                    self._value -= 1
                    fut.set_result(True)
                    break


class ProviderConcurrencyManager:
    """
    Manages per-provider concurrency pools using dynamic PrioritySemaphore instances.
    Prioritizes critical LLM tasks (Priority 1) over background tasks like Embeddings (Priority 2).
    """

    def __init__(self) -> None:
        self._semaphores: dict[int, tuple[int, PrioritySemaphore]] = {}
        self._lock = asyncio.Lock()
        self._default_semaphore = PrioritySemaphore(5)

    async def get_semaphore(
        self, provider_id: int | None, max_concurrency: int = 1
    ) -> PrioritySemaphore:
        if provider_id is None:
            return self._default_semaphore

        limit = max(1, max_concurrency)
        async with self._lock:
            if provider_id in self._semaphores:
                curr_limit, sem = self._semaphores[provider_id]
                if curr_limit == limit:
                    return sem

                logger.info(
                    "Updating concurrency pool for provider %d from %d to %d",
                    provider_id,
                    curr_limit,
                    limit,
                )
                # Adjust limits for the updated provider pool
                sem._value += limit - curr_limit
                self._semaphores[provider_id] = (limit, sem)
                return sem

            sem = PrioritySemaphore(limit)
            self._semaphores[provider_id] = (limit, sem)
            return sem

    @asynccontextmanager
    async def acquire(
        self, provider_id: int | None, max_concurrency: int = 1, priority: int = 1
    ) -> AsyncGenerator[None, None]:
        sem = await self.get_semaphore(provider_id, max_concurrency)
        await sem.acquire(priority=priority)
        try:
            yield
        finally:
            await sem.release()


# Global singleton instance
concurrency_manager = ProviderConcurrencyManager()

# In-flight task registry for background evaluation workers
_RUNNING_TASKS: dict[int, asyncio.Task] = {}


def register_running_task(task_id: int, task: asyncio.Task) -> None:
    """Registers an in-memory running asyncio Task by database task ID."""
    _RUNNING_TASKS[task_id] = task


def unregister_running_task(task_id: int) -> None:
    """Removes a finished or cancelled task from the in-memory registry."""
    _RUNNING_TASKS.pop(task_id, None)


def cancel_running_task(task_id: int) -> bool:
    """
    Cancels an active background asyncio.Task in memory.
    Disconnects the active socket connection to the AI provider.
    Returns True if an active task was found and cancellation requested.
    """
    task = _RUNNING_TASKS.get(task_id)
    if task and not task.done():
        logger.info("Cancelling in-flight asyncio task for task ID %d", task_id)
        task.cancel()
        return True
    return False


def get_running_task_ids() -> list[int]:
    """Returns list of currently active running task IDs."""
    return [tid for tid, t in _RUNNING_TASKS.items() if not t.done()]
