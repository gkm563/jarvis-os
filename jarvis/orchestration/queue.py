"""
Task Execution Queue & Scheduler Pipeline.
Manages priority queuing for background, interactive, and cron tasks.
"""

import asyncio
from typing import List, Optional
from jarvis.core.models import Plan
from jarvis.orchestration.executor import ExecutionManager
from jarvis.utils.logger import get_logger

logger = get_logger("TaskQueue")


class TaskExecutionQueue:
    """
    Async priority queue for scheduling and executing plan DAGs sequentially or concurrently.
    """

    def __init__(self, executor: Optional[ExecutionManager] = None):
        self.executor = executor or ExecutionManager()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

    async def enqueue_plan(self, plan: Plan) -> None:
        """Enqueues a plan for execution."""
        await self._queue.put(plan)
        logger.info(f"Enqueued plan '{plan.plan_id}' for execution")

    async def start_worker(self) -> None:
        """Starts background worker consuming tasks from queue."""
        self._is_running = True
        logger.info("Task queue background worker started")
        while self._is_running:
            plan = await self._queue.get()
            try:
                await self.executor.execute_plan(plan)
            except Exception as e:
                logger.error(f"Error processing plan '{plan.plan_id}' from queue: {str(e)}")
            finally:
                self._queue.task_done()

    def stop_worker(self) -> None:
        """Stops queue worker loop."""
        self._is_running = False
        logger.info("Task queue worker stopped")
