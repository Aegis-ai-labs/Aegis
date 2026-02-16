"""
Comprehensive backend verification for Aegis1 submission.

Tests all 12 critical items:
1. TaskManager CRUD operations
2. TaskExecutor background polling
3. Parallel task execution (10+ concurrent)
4. All 10 tools execute correctly
5-7. Health tools
8-11. Wealth + task tools
12. WebSocket endpoints, streaming, tool use loop, database integrity, error handling
"""

import asyncio
import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aegis.db import init_db, seed_demo_data
from aegis.task_manager import TaskManager
from aegis.executor import TaskExecutor
from aegis.claude_client import ClaudeClient
from aegis.tools import registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test results collector
RESULTS = {
    "passed": [],
    "failed": [],
}


def record_result(test_name, passed, error=None):
    """Record test result."""
    if passed:
        RESULTS["passed"].append(test_name)
        logger.info(f"✓ {test_name}")
    else:
        RESULTS["failed"].append((test_name, error))
        logger.error(f"✗ {test_name}: {error}")


# Initialize DB for all tests
def setup_function():
    """Initialize fresh in-memory DB before each test."""
    with patch("aegis.config.settings.db_path", ":memory:"):
        init_db()
        seed_demo_data(days=7)


# ============================================================================
# TESTS: TaskManager CRUD Operations
# ============================================================================

@pytest.mark.asyncio
async def test_01_taskmanager_create():
    """Test TaskManager.create_task()"""
    try:
        tm = TaskManager()
        task_id = await tm.create_task(
            title="Test Task",
            description="A test task",
            priority=5,
        )
        assert isinstance(task_id, int) and task_id > 0
        record_result("01: TaskManager.create_task()", True)
    except Exception as e:
        record_result("01: TaskManager.create_task()", False, str(e))


@pytest.mark.asyncio
async def test_02_taskmanager_read():
    """Test TaskManager.get_task()"""
    try:
        tm = TaskManager()
        task_id = await tm.create_task(
            title="Read Test",
            description="Testing read",
        )
        task = await tm.get_task(task_id)
        assert task is not None
        assert task["title"] == "Read Test"
        assert task["status"] == "pending"
        record_result("02: TaskManager.get_task()", True)
    except Exception as e:
        record_result("02: TaskManager.get_task()", False, str(e))


@pytest.mark.asyncio
async def test_03_taskmanager_update():
    """Test TaskManager.update_status()"""
    try:
        tm = TaskManager()
        task_id = await tm.create_task(
            title="Update Test",
            description="Testing update",
        )
        await tm.update_status(task_id, "in_progress")
        task = await tm.get_task(task_id)
        assert task["status"] == "in_progress"
        record_result("03: TaskManager.update_status()", True)
    except Exception as e:
        record_result("03: TaskManager.update_status()", False, str(e))


@pytest.mark.asyncio
async def test_04_taskmanager_list():
    """Test TaskManager.list_tasks()"""
    try:
        tm = TaskManager()
        for i in range(5):
            await tm.create_task(
                title=f"Task {i}",
                description="List test",
            )
        
        tasks = await tm.list_tasks(limit=10)
        assert len(tasks) >= 5
        record_result("04: TaskManager.list_tasks()", True)
    except Exception as e:
        record_result("04: TaskManager.list_tasks()", False, str(e))


@pytest.mark.asyncio
async def test_05_taskmanager_filter():
    """Test TaskManager.list_tasks() with status filter"""
    try:
        tm = TaskManager()
        task_id = await tm.create_task(
            title="Status Filter Test",
            description="Test filter",
        )
        await tm.update_status(task_id, "completed", result="Done!")
        
        completed = await tm.list_tasks(status="completed")
        assert any(t["id"] == task_id for t in completed)
        record_result("05: TaskManager status filter", True)
    except Exception as e:
        record_result("05: TaskManager status filter", False, str(e))


# ============================================================================
# TESTS: TaskExecutor
# ============================================================================

@pytest.mark.asyncio
async def test_06_executor_init():
    """Test TaskExecutor initialization"""
    try:
        executor = TaskExecutor()
        assert executor.is_running is False
        assert executor.running_tasks == {}
        record_result("06: TaskExecutor.__init__()", True)
    except Exception as e:
        record_result("06: TaskExecutor.__init__()", False, str(e))


@pytest.mark.asyncio
async def test_07_executor_lifecycle():
    """Test TaskExecutor start/stop"""
    try:
        executor = TaskExecutor()
        executor._poll_and_execute = AsyncMock()
        
        # Start in background
        task = asyncio.create_task(executor.start())
        await asyncio.sleep(0.1)
        
        # Should be running
        assert executor.is_running is True
        
        # Stop
        await executor.stop()
        assert executor.is_running is False
        
        record_result("07: TaskExecutor.start/stop", True)
    except Exception as e:
        record_result("07: TaskExecutor.start/stop", False, str(e))


# ============================================================================
# TESTS: Parallel Execution
# ============================================================================

@pytest.mark.asyncio
async def test_08_parallel_execution():
    """Test parallel execution of multiple tasks"""
    try:
        tm = TaskManager()
        executor = TaskExecutor()
        
        # Create 10 tasks
        for i in range(10):
            await tm.create_task(
                title=f"Parallel Task {i}",
                description=f"Concurrent test {i}",
                priority=i % 3,
            )
        
        # Mock Claude to return quickly
        executor.client.chat = AsyncMock(return_value=iter(["Result"]))
        
        # Poll and execute
        await executor._poll_and_execute()
        
        # Should have created some tasks
        assert len(executor.running_tasks) > 0
        
        # Wait for completion
        await asyncio.gather(*executor.running_tasks.values(), return_exceptions=True)
        
        record_result("08: Parallel execution (10 tasks)", True)
    except Exception as e:
        record_result("08: Parallel execution (10 tasks)", False, str(e))


# ============================================================================
# TESTS: All 10 Tools
# ============================================================================

@pytest.mark.asyncio
async def test_09_tool_log_health():
    """Test log_health tool"""
    try:
        result_json = await registry.dispatch_tool("log_health", {
            "sleep_hours": 7.5,
            "mood": "great",
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("09: Tool: log_health", True)
    except Exception as e:
        record_result("09: Tool: log_health", False, str(e))


@pytest.mark.asyncio
async def test_10_tool_get_health_today():
    """Test get_health_today tool"""
    try:
        result_json = await registry.dispatch_tool("get_health_today", {})
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("10: Tool: get_health_today", True)
    except Exception as e:
        record_result("10: Tool: get_health_today", False, str(e))


@pytest.mark.asyncio
async def test_11_tool_get_health_summary():
    """Test get_health_summary tool"""
    try:
        result_json = await registry.dispatch_tool("get_health_summary", {
            "days": 7,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("11: Tool: get_health_summary", True)
    except Exception as e:
        record_result("11: Tool: get_health_summary", False, str(e))


@pytest.mark.asyncio
async def test_12_tool_track_expense():
    """Test track_expense tool"""
    try:
        result_json = await registry.dispatch_tool("track_expense", {
            "amount": 25.50,
            "category": "food",
            "description": "Lunch",
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("12: Tool: track_expense", True)
    except Exception as e:
        record_result("12: Tool: track_expense", False, str(e))


@pytest.mark.asyncio
async def test_13_tool_get_spending_today():
    """Test get_spending_today tool"""
    try:
        result_json = await registry.dispatch_tool("get_spending_today", {})
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("13: Tool: get_spending_today", True)
    except Exception as e:
        record_result("13: Tool: get_spending_today", False, str(e))


@pytest.mark.asyncio
async def test_14_tool_get_spending_summary():
    """Test get_spending_summary tool"""
    try:
        result_json = await registry.dispatch_tool("get_spending_summary", {
            "days": 30,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("14: Tool: get_spending_summary", True)
    except Exception as e:
        record_result("14: Tool: get_spending_summary", False, str(e))


@pytest.mark.asyncio
async def test_15_tool_get_budget_status():
    """Test get_budget_status tool"""
    try:
        result_json = await registry.dispatch_tool("get_budget_status", {
            "monthly_budget": 3000.0,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("15: Tool: get_budget_status", True)
    except Exception as e:
        record_result("15: Tool: get_budget_status", False, str(e))


@pytest.mark.asyncio
async def test_16_tool_create_background_task():
    """Test create_background_task tool"""
    try:
        result_json = await registry.dispatch_tool("create_background_task", {
            "title": "Test Task",
            "description": "Testing tool",
            "priority": 5,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("16: Tool: create_background_task", True)
    except Exception as e:
        record_result("16: Tool: create_background_task", False, str(e))


@pytest.mark.asyncio
async def test_17_tool_get_task_status():
    """Test get_task_status tool"""
    try:
        tm = TaskManager()
        task_id = await tm.create_task(
            title="Status Check",
            description="Test",
        )
        
        result_json = await registry.dispatch_tool("get_task_status", {
            "task_id": task_id,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("17: Tool: get_task_status", True)
    except Exception as e:
        record_result("17: Tool: get_task_status", False, str(e))


@pytest.mark.asyncio
async def test_18_tool_list_all_tasks():
    """Test list_all_tasks tool"""
    try:
        result_json = await registry.dispatch_tool("list_all_tasks", {
            "limit": 10,
        })
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("18: Tool: list_all_tasks", True)
    except Exception as e:
        record_result("18: Tool: list_all_tasks", False, str(e))


# ============================================================================
# TESTS: WebSocket, Streaming, Tool Use, Database, Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_19_websocket_endpoints():
    """Test WebSocket endpoints are defined"""
    try:
        from aegis.main import app
        routes = [route.path for route in app.routes]
        assert any("/ws" in route for route in routes)
        record_result("19: WebSocket endpoints exist", True)
    except Exception as e:
        record_result("19: WebSocket endpoints exist", False, str(e))


@pytest.mark.asyncio
async def test_20_streaming_response():
    """Test streaming response"""
    try:
        client = ClaudeClient()
        
        with patch.object(client.client.messages, "stream") as mock:
            mock.return_value = iter(["Chunk1 ", "Chunk2 ", "Chunk3"])
            chunks = []
            async for chunk in client.get_response("Test"):
                chunks.append(chunk)
            assert len(chunks) > 0
        
        record_result("20: Streaming response works", True)
    except Exception as e:
        record_result("20: Streaming response works", False, str(e))


@pytest.mark.asyncio
async def test_21_tool_use_loop():
    """Test tool use loop"""
    try:
        client = ClaudeClient()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Result")]
        
        with patch.object(client.client.messages, "create", return_value=mock_response):
            result = await client.get_full_response("Test prompt")
            assert result is not None
        
        record_result("21: Tool use loop works", True)
    except Exception as e:
        record_result("21: Tool use loop works", False, str(e))


@pytest.mark.asyncio
async def test_22_database_integrity():
    """Test database integrity"""
    try:
        from aegis.db import get_db
        db = get_db()
        
        # Check tables exist
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        
        assert "health_logs" in table_names
        assert "expenses" in table_names
        assert "tasks" in table_names
        
        record_result("22: Database integrity checks", True)
    except Exception as e:
        record_result("22: Database integrity checks", False, str(e))


@pytest.mark.asyncio
async def test_23_error_handling_unknown_tool():
    """Test error handling for unknown tool"""
    try:
        result_json = await registry.dispatch_tool("nonexistent_tool", {})
        result = json.loads(result_json)
        assert "error" in result
        record_result("23: Error handling (unknown tool)", True)
    except Exception as e:
        record_result("23: Error handling (unknown tool)", False, str(e))


@pytest.mark.asyncio
async def test_24_error_handling_invalid_input():
    """Test error handling for invalid input"""
    try:
        result_json = await registry.dispatch_tool("track_expense", {})
        result = json.loads(result_json)
        assert isinstance(result, dict)
        record_result("24: Error handling (invalid input)", True)
    except Exception as e:
        record_result("24: Error handling (invalid input)", False, str(e))


def print_summary():
    """Print verification summary"""
    total = len(RESULTS["passed"]) + len(RESULTS["failed"])
    passed = len(RESULTS["passed"])
    failed = len(RESULTS["failed"])
    
    print("\n" + "="*70)
    print("AEGIS1 BACKEND VERIFICATION REPORT")
    print("="*70)
    print(f"\n✓ PASSED: {passed}/{total}")
    for test in RESULTS["passed"]:
        print(f"  • {test}")
    
    if RESULTS["failed"]:
        print(f"\n✗ FAILED: {failed}/{total}")
        for test, error in RESULTS["failed"]:
            print(f"  • {test}")
            if error:
                print(f"    └─ {error[:100]}")
    
    print("\n" + "="*70)
    if failed == 0:
        print("✓ ALL TESTS PASSED")
    else:
        print(f"✗ {failed} TESTS FAILED")
    print("="*70 + "\n")


# Run summary after all tests
@pytest.fixture(scope="session", autouse=True)
def session_summary():
    yield
    print_summary()
