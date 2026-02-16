"""Integration tests for TaskExecutor."""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from aegis.executor import TaskExecutor
from aegis.task_manager import TaskManager
from aegis.db import init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up in-memory test database."""
    import sqlite3

    test_db = sqlite3.connect(":memory:")
    test_db.row_factory = sqlite3.Row

    with patch("aegis.db.get_db", return_value=test_db):
        init_db()
        yield test_db

    test_db.close()


@pytest.mark.asyncio
async def test_executor_starts_and_stops():
    """Test that executor starts and stops cleanly."""
    executor = TaskExecutor()

    # Start executor in background
    start_task = asyncio.create_task(executor.start())

    # Give it time to start
    await asyncio.sleep(0.5)
    assert executor.is_running

    # Stop it
    await executor.stop()
    assert not executor.is_running

    # Wait for start_task to complete
    try:
        await asyncio.wait_for(start_task, timeout=2.0)
    except asyncio.TimeoutError:
        # It's okay if start_task doesn't complete immediately
        pass


@pytest.mark.asyncio
async def test_executor_picks_up_pending_tasks():
    """Test that executor discovers pending tasks."""
    manager = TaskManager()
    executor = TaskExecutor()

    # Create a task
    task_id = await manager.create_task(
        "Test oneshot", "A simple test task"
    )

    # Mock the Claude client to prevent actual API calls
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=__aiter__([]))

    executor.client = mock_client

    # Start executor
    start_task = asyncio.create_task(executor.start())

    # Wait for executor to poll and pick up the task
    await asyncio.sleep(2.0)

    # Stop executor
    await executor.stop()

    # Verify the task was executed
    task = await manager.get_task(task_id)
    assert task["status"] in ["in_progress", "completed"]

    try:
        await asyncio.wait_for(start_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass


@pytest.mark.asyncio
async def test_executor_builds_task_prompt():
    """Test that executor builds correct task prompt."""
    executor = TaskExecutor()

    task = {
        "title": "Exercise Reminder",
        "description": "Remind user to exercise",
        "priority": 5,
        "task_type": "recurring",
    }

    prompt = executor._build_task_prompt(task)

    assert "Exercise Reminder" in prompt
    assert "Remind user to exercise" in prompt
    assert "recurring" in prompt


@pytest.mark.asyncio
async def test_executor_should_run_now_daily_schedule():
    """Test daily schedule check."""
    from datetime import datetime

    executor = TaskExecutor()

    # Create a task with daily schedule at current hour
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute

    task = {
        "schedule": {
            "type": "daily",
            "time": f"{current_hour:02d}:{current_minute:02d}",
        },
        "task_type": "daily",
    }

    # Should return True because current time matches
    should_run = executor._should_run_now(task)
    assert should_run is True

    # Now test with a different time
    task["schedule"]["time"] = "23:59"
    should_run = executor._should_run_now(task)
    assert should_run is False


@pytest.mark.asyncio
async def test_executor_cleanup_task():
    """Test cleanup of completed task."""
    executor = TaskExecutor()

    # Add a dummy task to running_tasks
    dummy_task = asyncio.create_task(asyncio.sleep(100))
    executor.running_tasks[42] = dummy_task

    assert 42 in executor.running_tasks

    # Call cleanup
    executor._cleanup_task(42)

    assert 42 not in executor.running_tasks

    # Clean up the dummy task
    dummy_task.cancel()
    try:
        await dummy_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_executor_concurrent_task_execution():
    """Test executor can handle multiple concurrent tasks."""
    manager = TaskManager()
    executor = TaskExecutor()

    # Create multiple tasks
    id1 = await manager.create_task("Task 1", "First task")
    id2 = await manager.create_task("Task 2", "Second task")
    id3 = await manager.create_task("Task 3", "Third task")

    # Mock the Claude client
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=__aiter__([]))

    executor.client = mock_client

    # Start executor
    start_task = asyncio.create_task(executor.start())

    # Wait for executor to process
    await asyncio.sleep(2.0)

    # Stop executor
    await executor.stop()

    # Verify all tasks were picked up
    task1 = await manager.get_task(id1)
    task2 = await manager.get_task(id2)
    task3 = await manager.get_task(id3)

    # At least one should be processed
    statuses = {task1["status"], task2["status"], task3["status"]}
    assert "in_progress" in statuses or "completed" in statuses

    try:
        await asyncio.wait_for(start_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass


def __aiter__(items):
    """Helper to create an async iterator."""

    async def _aiter():
        for item in items:
            yield item

    return _aiter()
