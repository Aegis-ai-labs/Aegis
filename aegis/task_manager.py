"""Task manager for Aegis framework.

Handles CRUD operations for persistent task storage using SQLite.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from aegis.db import get_db

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task lifecycle in SQLite."""

    def __init__(self):
        self.db = get_db()

    async def create_task(
        self,
        title: str,
        description: str,
        priority: int = 0,
        task_type: str = "oneshot",
        schedule: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Create a new task.

        Args:
            title: Short task title
            description: Detailed description
            priority: Priority level (0-10, higher = more urgent)
            task_type: "oneshot", "recurring", or "scheduled"
            schedule: Schedule config for recurring/scheduled tasks
            metadata: Additional context

        Returns:
            task_id: Integer ID of created task
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, description, priority, task_type, schedule, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                title,
                description,
                priority,
                task_type,
                json.dumps(schedule) if schedule else None,
                json.dumps(metadata) if metadata else None,
            ),
        )
        self.db.commit()
        task_id = cursor.lastrowid
        logger.info(f"Created task {task_id}: {title}")
        return task_id

    async def update_status(
        self,
        task_id: int,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Update task status and optional result/error.

        Args:
            task_id: Task ID to update
            status: New status ("pending", "in_progress", "completed", "failed")
            result: Result string if completed
            error: Error message if failed
        """
        now = datetime.utcnow().isoformat()
        cursor = self.db.cursor()

        if status == "completed":
            cursor.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (status, result, now, now, task_id),
            )
        elif status == "failed":
            cursor.execute(
                """
                UPDATE tasks
                SET status = ?, error = ?, updated_at = ?
                WHERE id = ?
            """,
                (status, error, now, task_id),
            )
        else:
            cursor.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?
                WHERE id = ?
            """,
                (status, now, task_id),
            )

        self.db.commit()
        logger.debug(f"Updated task {task_id} status to {status}")

    async def get_task(self, task_id: int) -> Optional[dict]:
        """Get task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task dict or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_dict(row)

    async def list_tasks(
        self, status: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        """List tasks, optionally filtered by status.

        Args:
            status: Filter by status ("pending", "in_progress", "completed", "failed")
            limit: Maximum number of tasks to return

        Returns:
            List of task dicts
        """
        cursor = self.db.cursor()
        if status:
            cursor.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
            """,
                (status, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM tasks
                ORDER BY priority DESC, created_at DESC
                LIMIT ?
            """,
                (limit,),
            )

        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert SQLite row to dict."""
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "status": row[3],
            "priority": row[4],
            "task_type": row[5],
            "schedule": json.loads(row[6]) if row[6] else None,
            "created_at": row[7],
            "updated_at": row[8],
            "completed_at": row[9],
            "result": row[10],
            "error": row[11],
            "metadata": json.loads(row[12]) if row[12] else None,
        }
