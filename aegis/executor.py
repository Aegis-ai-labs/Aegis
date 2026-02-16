"""Background task executor for Aegis framework.

Polls for pending tasks and executes them via Claude.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from aegis.task_manager import TaskManager
from aegis.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Background executor that polls for pending tasks and executes them.

    Uses asyncio.create_task() for concurrent execution.
    Each task runs in its own async context via ClaudeClient.
    """

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        self.manager = TaskManager()
        self.client = claude_client or ClaudeClient()
        self.running_tasks: dict[int, asyncio.Task] = {}
        self.is_running = False
        self._poll_interval = 5  # seconds

    async def start(self):
        """Start the executor background loop."""
        self.is_running = True
        logger.info("✓ TaskExecutor started, polling every %ds", self._poll_interval)

        try:
            while self.is_running:
                try:
                    await self._poll_and_execute()
                    await asyncio.sleep(self._poll_interval)
                except Exception as e:
                    logger.error(f"Executor poll error: {e}", exc_info=True)
                    await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            logger.info("TaskExecutor cancelled")
            await self.stop()

    async def stop(self):
        """Stop the executor and cancel running tasks."""
        self.is_running = False

        # Cancel all running tasks
        for task_id, task in list(self.running_tasks.items()):
            logger.info(f"Cancelling task {task_id}")
            task.cancel()

        # Wait for cancellations
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        self.running_tasks.clear()

        logger.info("✓ TaskExecutor stopped")

    async def _poll_and_execute(self):
        """Poll for pending tasks and execute them."""
        # Get pending tasks
        pending_tasks = await self.manager.list_tasks(status="pending", limit=10)

        for task in pending_tasks:
            task_id = task["id"]

            # Skip if already running
            if task_id in self.running_tasks:
                continue

            # Check if scheduled task should run now
            if task["task_type"] in ["scheduled", "recurring"]:
                if not self._should_run_now(task):
                    continue

            # Create background task
            logger.info(f"Executing task {task_id}: {task['title']}")
            bg_task = asyncio.create_task(self._execute_task(task_id, task))
            self.running_tasks[task_id] = bg_task

            # Add cleanup callback
            bg_task.add_done_callback(lambda t, tid=task_id: self._cleanup_task(tid))

    def _should_run_now(self, task: dict) -> bool:
        """Check if scheduled task should run now."""
        if not task["schedule"]:
            return False

        schedule = task["schedule"]
        now = datetime.utcnow()

        # Simple daily schedule check
        if schedule.get("type") == "daily":
            target_time = schedule.get("time", "00:00")  # "HH:MM"
            try:
                hour, minute = map(int, target_time.split(":"))

                # Check if current time matches (within 5-minute window)
                if now.hour == hour and abs(now.minute - minute) <= 5:
                    return True
            except (ValueError, IndexError):
                logger.warning(f"Invalid schedule time format: {target_time}")

        return False

    async def _execute_task(self, task_id: int, task: dict):
        """
        Execute a single task via ClaudeClient.

        The task description is sent to Claude with context,
        and Claude executes it using available tools.
        """
        try:
            # Update status to in_progress
            await self.manager.update_status(task_id, "in_progress")

            # Build task execution prompt
            prompt = self._build_task_prompt(task)

            # Execute via Claude (streaming)
            result_chunks = []
            async for chunk in self.client.chat(prompt):
                result_chunks.append(chunk)

            result = "".join(result_chunks)

            # Mark as completed
            await self.manager.update_status(task_id, "completed", result=result)
            logger.info(f"✓ Task {task_id} completed successfully")

        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
            await self.manager.update_status(
                task_id, "failed", error="Task was cancelled"
            )
        except Exception as e:
            logger.error(f"✗ Task {task_id} failed: {e}", exc_info=True)
            await self.manager.update_status(task_id, "failed", error=str(e))

    def _build_task_prompt(self, task: dict) -> str:
        """Build execution prompt for Claude."""
        return f"""You are executing a background task autonomously.

Task Title: {task['title']}
Task Description: {task['description']}
Priority: {task['priority']}
Task Type: {task['task_type']}

Execute this task using available tools. Report what you accomplished.
Keep your response concise and factual."""

    def _cleanup_task(self, task_id: int):
        """Clean up completed task from running_tasks dict."""
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
            logger.debug(f"Cleaned up task {task_id}")
