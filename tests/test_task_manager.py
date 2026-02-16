"""Unit tests for TaskManager."""

import asyncio
import pytest
from datetime import datetime

# Temporarily add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aegis.task_manager import TaskManager
from aegis.db import get_db, init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up in-memory test database."""
    import sqlite3
    from unittest.mock import patch

    # Use in-memory database for tests
    test_db = sqlite3.connect(":memory:")
    test_db.row_factory = sqlite3.Row

    with patch("aegis.db.get_db", return_value=test_db):
        init_db()
        yield test_db

    test_db.close()


@pytest.mark.asyncio
async def test_create_task():
    """Test creating a task."""
    manager = TaskManager()
    task_id = await manager.create_task("Test Task", "Test description")

    assert task_id > 0
    task = await manager.get_task(task_id)
    assert task is not None
    assert task["title"] == "Test Task"
    assert task["description"] == "Test description"
    assert task["status"] == "pending"
    assert task["priority"] == 0


@pytest.mark.asyncio
async def test_create_task_with_priority():
    """Test creating a task with priority."""
    manager = TaskManager()
    task_id = await manager.create_task(
        "Urgent Task", "High priority", priority=9
    )

    task = await manager.get_task(task_id)
    assert task["priority"] == 9


@pytest.mark.asyncio
async def test_create_task_with_schedule():
    """Test creating a scheduled task."""
    manager = TaskManager()
    schedule = {"type": "daily", "time": "07:00"}
    task_id = await manager.create_task(
        "Daily Reminder",
        "Remind at 7am",
        task_type="scheduled",
        schedule=schedule,
    )

    task = await manager.get_task(task_id)
    assert task["task_type"] == "scheduled"
    assert task["schedule"] == schedule


@pytest.mark.asyncio
async def test_update_task_status_to_in_progress():
    """Test updating task status to in_progress."""
    manager = TaskManager()
    task_id = await manager.create_task("Test", "Test")

    await manager.update_status(task_id, "in_progress")
    task = await manager.get_task(task_id)

    assert task["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_task_status_to_completed():
    """Test updating task status to completed."""
    manager = TaskManager()
    task_id = await manager.create_task("Test", "Test")

    result = "Task completed successfully"
    await manager.update_status(task_id, "completed", result=result)
    task = await manager.get_task(task_id)

    assert task["status"] == "completed"
    assert task["result"] == result
    assert task["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_task_status_to_failed():
    """Test updating task status to failed."""
    manager = TaskManager()
    task_id = await manager.create_task("Test", "Test")

    error = "Connection timeout"
    await manager.update_status(task_id, "failed", error=error)
    task = await manager.get_task(task_id)

    assert task["status"] == "failed"
    assert task["error"] == error


@pytest.mark.asyncio
async def test_get_nonexistent_task():
    """Test getting a nonexistent task returns None."""
    manager = TaskManager()
    task = await manager.get_task(9999)

    assert task is None


@pytest.mark.asyncio
async def test_list_all_tasks():
    """Test listing all tasks."""
    manager = TaskManager()

    # Create multiple tasks
    await manager.create_task("Task 1", "Desc 1")
    await manager.create_task("Task 2", "Desc 2")
    await manager.create_task("Task 3", "Desc 3")

    tasks = await manager.list_tasks()
    assert len(tasks) >= 3


@pytest.mark.asyncio
async def test_list_tasks_filtered_by_status():
    """Test listing tasks filtered by status."""
    manager = TaskManager()

    # Create and complete some tasks
    id1 = await manager.create_task("Task 1", "Desc 1")
    id2 = await manager.create_task("Task 2", "Desc 2")
    id3 = await manager.create_task("Task 3", "Desc 3")

    # Complete one task
    await manager.update_status(id1, "completed", result="Done")

    pending = await manager.list_tasks(status="pending")
    completed = await manager.list_tasks(status="completed")

    assert len(pending) >= 2
    assert len(completed) >= 1
    assert all(t["status"] == "pending" for t in pending)
    assert all(t["status"] == "completed" for t in completed)


@pytest.mark.asyncio
async def test_list_tasks_respects_limit():
    """Test that list_tasks respects the limit parameter."""
    manager = TaskManager()

    # Create many tasks
    for i in range(10):
        await manager.create_task(f"Task {i}", f"Desc {i}")

    # List with limit=3
    tasks = await manager.list_tasks(limit=3)
    assert len(tasks) <= 3


@pytest.mark.asyncio
async def test_task_priority_ordering():
    """Test that tasks are ordered by priority."""
    manager = TaskManager()

    id1 = await manager.create_task("Low priority", "Desc", priority=1)
    id2 = await manager.create_task("High priority", "Desc", priority=9)
    id3 = await manager.create_task("Medium priority", "Desc", priority=5)

    tasks = await manager.list_tasks()
    # First three tasks should be ordered by priority (high to low)
    assert tasks[0]["priority"] == 9
    assert tasks[1]["priority"] == 5
    assert tasks[2]["priority"] == 1


@pytest.mark.asyncio
async def test_task_metadata():
    """Test storing and retrieving task metadata."""
    manager = TaskManager()
    metadata = {"user_id": 123, "context": "health_tracking"}

    task_id = await manager.create_task(
        "Test", "Test", metadata=metadata
    )

    task = await manager.get_task(task_id)
    assert task["metadata"] == metadata
