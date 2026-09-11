import asyncio
import heapq
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PrioritySemaphore:
    """
    A semaphore that grants locks based on priority.
    Waiters with a lower priority number execute first.
    When max_concurrency >= 2 and interactive_headroom=True, background tasks (priority >= 2)
    are restricted to at most max(1, max_concurrency - 1) concurrent slots,
    reserving 1 slot exclusively for interactive tasks (priority = 1).
    """

    def __init__(self, value: int = 1, interactive_headroom: bool = True):
        self._capacity = value
        self._value = value
        self._interactive_headroom = interactive_headroom
        self._active_priority_2 = 0
        self._active_priority_1 = 0
        self._waiters = []
        self._count = 0  # Tie-breaker for tasks with the same priority
        self._lock = asyncio.Lock()

    def _can_acquire(self, priority: int) -> bool:
        if self._value <= 0:
            return False
        if priority == 1:
            return True
        # priority >= 2 (background task)
        if self._interactive_headroom and self._capacity >= 2:
            # Reserve 1 slot for priority 1
            # Background tasks can acquire if _value > 1, OR if no interactive headroom is breached
            # Equivalent: total active background tasks cannot exceed capacity - 1
            max_bg_slots = max(1, self._capacity - 1)
            if self._active_priority_2 >= max_bg_slots:
                return False
            # Also if only 1 slot is left (_value == 1), reserve it for priority 1
            if self._value <= 1:
                return False
        return True

    async def acquire(self, priority: int = 1):
        async with self._lock:
            if self._can_acquire(priority):
                self._value -= 1
                if priority == 1:
                    self._active_priority_1 += 1
                else:
                    self._active_priority_2 += 1
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

    async def release(self, priority: int = 1):
        async with self._lock:
            self._value += 1
            if priority == 1:
                self._active_priority_1 = max(0, self._active_priority_1 - 1)
            else:
                self._active_priority_2 = max(0, self._active_priority_2 - 1)

            # Check waiters in priority order (min-heap)
            temp_skipped = []
            while self._waiters:
                w_prio, w_cnt, fut = heapq.heappop(self._waiters)
                if fut.done():
                    continue
                if self._can_acquire(w_prio):
                    self._value -= 1
                    if w_prio == 1:
                        self._active_priority_1 += 1
                    else:
                        self._active_priority_2 += 1
                    fut.set_result(True)
                    break
                else:
                    temp_skipped.append((w_prio, w_cnt, fut))

            for item in temp_skipped:
                heapq.heappush(self._waiters, item)


class ProviderConcurrencyManager:
    """
    Manages per-provider concurrency pools using dynamic PrioritySemaphore instances.
    Prioritizes critical LLM tasks (Priority 1) over background tasks like Embeddings (Priority 2).
    """

    def __init__(self) -> None:
        self._semaphores: dict[int, tuple[int, PrioritySemaphore]] = {}
        self._lock = asyncio.Lock()
        self._default_semaphore = PrioritySemaphore(5)
        self._last_active: dict[int, float] = {}
        self._active_tasks_count: dict[int, int] = {}

    def get_last_active(self, provider_id: int) -> float:
        return self._last_active.get(provider_id, time.time())

    def get_active_count(self, provider_id: int) -> int:
        return self._active_tasks_count.get(provider_id, 0)

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
        if provider_id is not None:
            self._active_tasks_count[provider_id] = (
                self._active_tasks_count.get(provider_id, 0) + 1
            )
        try:
            yield
        finally:
            if provider_id is not None:
                self._active_tasks_count[provider_id] = max(
                    0, self._active_tasks_count.get(provider_id, 1) - 1
                )
                self._last_active[provider_id] = time.time()
            await sem.release(priority=priority)


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


async def idle_vram_watcher_loop(
    session_factory, check_interval_seconds: int = 30
) -> None:
    """
    Background loop that inspects provider inactivity.
    If active_tasks == 0 and time.time() - last_active > (auto_release_vram_minutes * 60),
    automatically dispatches release_provider_vram to free GPU memory.
    """
    logger.info("Starting idle VRAM watcher loop...")
    while True:
        try:
            await asyncio.sleep(check_interval_seconds)
            now = time.time()
            async with session_factory() as session:
                from sqlalchemy import select

                from app.models.ai_providers import AIProviderModel
                from app.services.provider_lifecycle_service import (
                    release_provider_vram,
                )

                stmt = select(AIProviderModel).where(
                    AIProviderModel.is_active.is_(True),
                    AIProviderModel.auto_release_vram_minutes.isnot(None),
                    AIProviderModel.auto_release_vram_minutes > 0,
                )
                res = await session.execute(stmt)
                providers = res.scalars().all()

                for p in providers:
                    p_id = p.id
                    active_count = concurrency_manager.get_active_count(p_id)
                    if active_count > 0:
                        continue

                    last_active = concurrency_manager.get_last_active(p_id)
                    idle_minutes = (now - last_active) / 60.0
                    threshold_minutes = p.auto_release_vram_minutes or 10

                    if idle_minutes >= threshold_minutes:
                        logger.info(
                            "Provider %s (ID %d) idle for %.1f min (threshold %d min). Triggering VRAM release.",
                            p.name,
                            p_id,
                            idle_minutes,
                            threshold_minutes,
                        )
                        try:
                            await release_provider_vram(p_id, session)
                            # Reset last active to prevent spamming unload calls every 30s
                            concurrency_manager._last_active[p_id] = now
                        except Exception as r_err:
                            logger.warning(
                                "Error auto-releasing VRAM for provider %d: %s",
                                p_id,
                                r_err,
                            )
        except asyncio.CancelledError:
            logger.info("Idle VRAM watcher loop cancelled.")
            break
        except Exception as exc:
            logger.error("Error in idle VRAM watcher loop: %s", exc)
