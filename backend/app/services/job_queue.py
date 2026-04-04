"""
In-process async job queue backed by asyncio.Queue.

Design:
- A single Queue[str] holds job IDs.
- N worker coroutines (configured via settings.worker_concurrency) pull
  from the queue and process one job at a time.
- SSE subscribers can listen for status changes via per-job asyncio.Event.

To migrate to Celery+Redis later: replace enqueue() and the worker loop
in cad_worker.py. The routers and DB layer are unchanged.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        # job_id → Event that fires on any status transition
        self._events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)

    async def enqueue(self, job_id: str) -> None:
        await self._queue.put(job_id)

    async def dequeue(self) -> str:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    def notify(self, job_id: str) -> None:
        """Signal that the job's status has changed."""
        event = self._events[job_id]
        event.set()
        # Reset immediately so the next status change can be awaited again
        event.clear()

    async def wait_for_update(self, job_id: str, timeout: float = 30.0) -> bool:
        """
        Wait until the job's status changes or timeout expires.
        Returns True if a change occurred, False on timeout.
        """
        event = self._events[job_id]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


# Singleton — imported by routers and workers
job_queue = JobQueue()
