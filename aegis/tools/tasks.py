"""Task management tools for Aegis framework.

Allows Claude to create, query, and manage background tasks.
"""

import json
import logging
from typing import Optional

from aegis.task_manager import TaskManager

logger = logging.getLogger(__name__)


async def create_background_task(
    title: str,
    description: str,
    priority: int = 0,
    task_type: str = "oneshot",
    schedule: Optional[dict] = None,
) -> dict:
    """Create a background task that will be executed autonomously.

    Use this for reminders, recurring actions, scheduled events, or long-running operations.

    Args:
        title: Short task title
        description: Detailed description of what the task should do
        priority: Priority level (0-10, higher = more urgent)
        task_type: "oneshot" (run once), "recurring" (repeat), "scheduled" (run at specific time)
        schedule: For recurring/scheduled tasks, e.g. {"type": "daily", "time": "07:00"}

    Returns:
        {"success": bool, "task_id": int, "status": str, "message": str}
    """
    try:
        manager = TaskManager()
        task_id = await manager.create_task(
            title=title,
            description=description,
            priority=priority,
            task_type=task_type,
            schedule=schedule,
        )

        logger.info(f"Created task {task_id}: {title}")
        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": f"Task '{title}' created successfully and will be executed soon",
        }
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return {"success": False, "error": str(e)}


async def get_task_status(task_id: int) -> dict:
    """Check the status of a background task.

    Args:
        task_id: Task ID to check

    Returns:
        {"success": bool, "task": dict or "error": str}
    """
    try:
        manager = TaskManager()
        task = await manager.get_task(task_id)

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        return {"success": True, "task": task}
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return {"success": False, "error": str(e)}


async def list_all_tasks(status: Optional[str] = None, limit: int = 20) -> dict:
    """List all tasks, optionally filtered by status.

    Args:
        status: Filter by status ("pending", "in_progress", "completed", "failed")
        limit: Maximum number of tasks to return

    Returns:
        {"success": bool, "tasks": list[dict], "count": int} or {"success": False, "error": str}
    """
    try:
        manager = TaskManager()
        tasks = await manager.list_tasks(status=status, limit=limit)

        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
        }
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        return {"success": False, "error": str(e)}
