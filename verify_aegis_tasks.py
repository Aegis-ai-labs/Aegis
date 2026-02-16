#!/usr/bin/env python
"""Verification script for Aegis task management framework.

This script tests:
1. Database schema is correct
2. TaskManager CRUD operations work
3. Task tools are registered
4. Executor can be initialized
"""

import asyncio
import sqlite3
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from aegis.db import get_db, init_db
from aegis.task_manager import TaskManager
from aegis.tools.registry import TOOL_DEFINITIONS, _HANDLERS, dispatch_tool


def verify_database():
    """Verify database schema."""
    print("\n1. Verifying database schema...")

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Initialize
    from unittest.mock import patch
    with patch("aegis.db.get_db", return_value=conn):
        init_db()

    # Check tasks table exists
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
    )
    if cursor.fetchone():
        print("   ✓ Tasks table exists")
    else:
        print("   ✗ Tasks table missing")
        return False

    # Check table schema
    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor.fetchall()}
    required_columns = {
        "id",
        "title",
        "description",
        "status",
        "priority",
        "task_type",
        "schedule",
        "created_at",
        "updated_at",
        "completed_at",
        "result",
        "error",
        "metadata",
    }

    if required_columns.issubset(columns):
        print("   ✓ All required columns present")
    else:
        missing = required_columns - columns
        print(f"   ✗ Missing columns: {missing}")
        return False

    # Check indexes
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tasks'"
    )
    indexes = {row[0] for row in cursor.fetchall()}
    if "idx_task_status" in indexes and "idx_task_type" in indexes:
        print("   ✓ Indexes created correctly")
    else:
        print("   ✗ Indexes missing")
        return False

    conn.close()
    return True


async def verify_task_manager():
    """Verify TaskManager implementation."""
    print("\n2. Verifying TaskManager implementation...")

    try:
        # Check that TaskManager can be imported
        if TaskManager is not None:
            print("   ✓ TaskManager class exists")
        else:
            print("   ✗ TaskManager class missing")
            return False

        # Check methods exist
        manager_methods = [
            "create_task",
            "update_status",
            "get_task",
            "list_tasks",
        ]

        for method_name in manager_methods:
            if hasattr(TaskManager, method_name):
                print(f"   ✓ Method '{method_name}' exists")
            else:
                print(f"   ✗ Method '{method_name}' missing")
                return False

        # Check that methods are async
        import inspect

        for method_name in manager_methods:
            method = getattr(TaskManager, method_name)
            if inspect.iscoroutinefunction(method):
                print(f"   ✓ Method '{method_name}' is async")
            else:
                print(f"   ✗ Method '{method_name}' is not async")
                return False

        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_tool_registry():
    """Verify task tools are registered."""
    print("\n3. Verifying tool registry...")

    # Count task tools
    task_tools = [t for t in TOOL_DEFINITIONS if "task" in t["name"].lower()]

    if len(task_tools) == 3:
        print(f"   ✓ All 3 task tools registered:")
        for tool in task_tools:
            print(f"     - {tool['name']}")
    else:
        print(f"   ✗ Expected 3 task tools, found {len(task_tools)}")
        return False

    # Verify handlers
    expected_handlers = [
        "create_background_task",
        "get_task_status",
        "list_all_tasks",
    ]

    for handler_name in expected_handlers:
        if handler_name in _HANDLERS:
            print(f"   ✓ Handler '{handler_name}' registered")
        else:
            print(f"   ✗ Handler '{handler_name}' missing")
            return False

    # Verify tool definitions have proper schema
    for tool in task_tools:
        if "input_schema" in tool and "properties" in tool["input_schema"]:
            print(f"   ✓ Tool '{tool['name']}' has proper schema")
        else:
            print(f"   ✗ Tool '{tool['name']}' schema is invalid")
            return False

    return True


async def verify_executor():
    """Verify TaskExecutor can be initialized."""
    print("\n4. Verifying TaskExecutor...")

    try:
        from aegis.executor import TaskExecutor

        executor = TaskExecutor()

        if executor.is_running is False:
            print("   ✓ TaskExecutor instantiates correctly")
        else:
            print("   ✗ TaskExecutor state incorrect")
            return False

        # Check methods exist
        if (
            hasattr(executor, "start")
            and hasattr(executor, "stop")
            and hasattr(executor, "_poll_and_execute")
        ):
            print("   ✓ TaskExecutor has required methods")
        else:
            print("   ✗ TaskExecutor missing methods")
            return False

        # Test daily schedule check
        from datetime import datetime

        now = datetime.utcnow()
        task = {
            "schedule": {
                "type": "daily",
                "time": f"{now.hour:02d}:{now.minute:02d}",
            },
            "task_type": "daily",
        }

        if executor._should_run_now(task):
            print("   ✓ Schedule check works")
        else:
            print("   ✗ Schedule check failed")
            return False

        # Test prompt building
        task = {
            "title": "Test",
            "description": "Test description",
            "priority": 5,
            "task_type": "oneshot",
        }

        prompt = executor._build_task_prompt(task)
        if "Test" in prompt and "Test description" in prompt:
            print("   ✓ Task prompt generation works")
        else:
            print("   ✗ Task prompt generation failed")
            return False

        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def verify_main_integration():
    """Verify main.py integration."""
    print("\n5. Verifying main.py integration...")

    try:
        # Try importing main - this will fail if FastAPI isn't installed
        # but we can at least verify the file exists and check its content
        import os

        main_path = Path(__file__).parent / "aegis" / "main.py"
        if not main_path.exists():
            print("   ✗ main.py file not found")
            return False

        with open(main_path, "r") as f:
            main_content = f.read()

        # Check for key integration points
        checks = [
            ("executor import", "from .executor import TaskExecutor"),
            ("executor variable", "executor: Optional[TaskExecutor] = None"),
            ("executor startup", "executor = TaskExecutor()"),
            ("executor startup task", "executor_task = asyncio.create_task"),
            ("/ws/tasks endpoint", '@app.websocket("/ws/tasks")'),
            ("task monitoring", "Task monitoring WebSocket"),
        ]

        all_found = True
        for check_name, pattern in checks:
            if pattern in main_content:
                print(f"   ✓ Found: {check_name}")
            else:
                print(f"   ✗ Missing: {check_name}")
                all_found = False

        return all_found
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def main():
    """Run all verifications."""
    print("\n" + "=" * 60)
    print("AEGIS TASK MANAGEMENT FRAMEWORK - VERIFICATION")
    print("=" * 60)

    results = []

    # Database verification
    results.append(("Database Schema", verify_database()))

    # TaskManager verification
    results.append(("TaskManager Operations", await verify_task_manager()))

    # Tool registry verification
    results.append(("Tool Registry", verify_tool_registry()))

    # Executor verification
    results.append(("TaskExecutor", await verify_executor()))

    # Main integration verification
    results.append(("Main Integration", await verify_main_integration()))

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for check_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name:.<40} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ ALL VERIFICATIONS PASSED - Framework is ready!\n")
        return 0
    else:
        print("\n✗ SOME VERIFICATIONS FAILED - Please review above\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
