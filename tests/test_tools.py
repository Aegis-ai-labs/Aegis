"""Test health and wealth tools."""

import json
import os

import pytest

from aegis.db import init_db, seed_demo_data, get_db
from aegis.tools import health, wealth
from aegis.tools.registry import dispatch_tool


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initialize database once for all tests in this module."""
    init_db()  # Create tables
    seed_demo_data(days=7)  # Seed demo data
    yield


@pytest.mark.asyncio
async def test_get_health_context():
    result = await health.get_health_context(days=7)
    assert "data" in result
    assert "sleep_hours" in result["data"]
    assert result["data"]["sleep_hours"]["count"] > 0


@pytest.mark.asyncio
async def test_get_health_context_filtered():
    result = await health.get_health_context(days=7, metrics=["mood", "sleep_hours"])
    assert "mood" in result["data"]
    assert "sleep_hours" in result["data"]


@pytest.mark.asyncio
async def test_log_health():
    result = await health.log_health(metric="sleep_hours", value=7.5, notes="good sleep")
    assert result["status"] == "logged"
    assert result["value"] == 7.5


@pytest.mark.asyncio
async def test_analyze_health_patterns():
    result = await health.analyze_health_patterns(query="sleep vs mood correlation", days=7)
    assert "daily_data" in result
    assert len(result["daily_data"]) > 0


@pytest.mark.asyncio
async def test_track_expense():
    result = await wealth.track_expense(amount=45.00, category="food", description="lunch")
    assert result["status"] == "recorded"
    assert result["amount"] == 45.00


@pytest.mark.asyncio
async def test_get_spending_summary():
    result = await wealth.get_spending_summary(days=7)
    assert "total_spent" in result
    assert "by_category" in result
    assert result["total_spent"] > 0


@pytest.mark.asyncio
async def test_get_spending_summary_filtered():
    result = await wealth.get_spending_summary(days=7, category="food")
    assert "total_spent" in result


@pytest.mark.asyncio
async def test_calculate_savings_goal():
    result = await wealth.calculate_savings_goal(
        target_amount=5000, target_months=6, monthly_income=4000
    )
    assert "monthly_savings_needed" in result
    assert result["monthly_savings_needed"] > 0
    assert "feasible" in result


@pytest.mark.asyncio
async def test_execute_tool_dispatch():
    result_json = await dispatch_tool("get_health_context", {"days": 3})
    result = json.loads(result_json)
    assert "data" in result


@pytest.mark.asyncio
async def test_execute_tool_unknown():
    result_json = await dispatch_tool("nonexistent_tool", {})
    result = json.loads(result_json)
    assert "error" in result
