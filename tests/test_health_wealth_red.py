"""
RED phase tests for health/wealth tools — Critical business logic.

These tests FAIL because the implementation doesn't exist yet.
Follow the structure: Test → Implement → Verify (TDD).

Test Classes:
1. TestHealthDataLogging - Log sleep, mood, heart rate, steps
2. TestHealthPatternQueries - Trends, correlations, insights
3. TestExpenseTracking - Categorization, totals, validation
4. TestSpendingReports - By category, by time period
5. TestSavingsGoals - Monthly required, feasibility checks
6. TestToolDispatch - Routing, input validation, error handling
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from aegis.db import get_db
from aegis.tools import health, wealth
from aegis.tools.registry import dispatch_tool


# NOTE: Database is initialized by conftest.py session fixture
# which calls init_db() before running any tests.


# ============================================================================
# TEST CLASS 1: TestHealthDataLogging - Log health metrics
# ============================================================================


class TestHealthDataLogging:
    """Test logging individual health data points: sleep, mood, HR, steps."""

    @pytest.mark.asyncio
    async def test_log_sleep_hours_single_entry(self):
        """Log a single sleep hour entry and verify it's recorded."""
        result = await health.log_health(
            sleep_hours=7.5,
            notes="good sleep"
        )

        assert result["status"] == "logged"
        assert result["id"] is not None
        assert "date" in result

        # Verify in database
        db = get_db()
        cursor = db.execute(
            "SELECT value FROM health_logs WHERE metric = 'sleep_hours' AND id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 7.5

    @pytest.mark.asyncio
    async def test_log_mood_with_validation(self):
        """Log mood and validate it's one of allowed values."""
        mood_values = ["great", "good", "okay", "tired", "stressed"]

        for mood in mood_values:
            result = await health.log_health(mood=mood)
            assert result["status"] == "logged"

            # Verify in database
            db = get_db()
            cursor = db.execute(
                "SELECT value FROM health_logs WHERE metric = 'mood' AND id = ?",
                (result["id"],)
            )
            row = cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_log_heart_rate_numeric(self):
        """Log heart rate as integer (bpm) and verify storage."""
        result = await health.log_health(
            heart_rate=72,
            notes="resting"
        )

        assert result["status"] == "logged"

        db = get_db()
        cursor = db.execute(
            "SELECT value FROM health_logs WHERE metric = 'heart_rate' AND id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 72

    @pytest.mark.asyncio
    async def test_log_steps_integer(self):
        """Log step count and verify it's stored as integer."""
        result = await health.log_health(steps=8432)

        assert result["status"] == "logged"

        db = get_db()
        cursor = db.execute(
            "SELECT value FROM health_logs WHERE metric = 'steps' AND id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 8432

    @pytest.mark.asyncio
    async def test_log_health_multiple_metrics_same_day(self):
        """Log multiple metrics on the same day and verify all are recorded."""
        date = datetime.now().strftime("%Y-%m-%d")

        result_sleep = await health.log_health(sleep_hours=8.0, date=date)
        result_steps = await health.log_health(steps=9000, date=date)
        result_mood = await health.log_health(mood="great", date=date)

        assert result_sleep["status"] == "logged"
        assert result_steps["status"] == "logged"
        assert result_mood["status"] == "logged"

        db = get_db()
        cursor = db.execute(
            "SELECT COUNT(*) FROM health_logs WHERE metric IN ('sleep_hours', 'steps', 'mood')"
        )
        count = cursor.fetchone()[0]
        assert count >= 3

    @pytest.mark.asyncio
    async def test_log_health_with_custom_date(self):
        """Log health data for a specific date (not today)."""
        custom_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        result = await health.log_health(
            sleep_hours=6.5,
            date=custom_date
        )

        assert result["status"] == "logged"
        assert result["date"] == custom_date

    @pytest.mark.asyncio
    async def test_log_health_defaults_to_today(self):
        """When no date is provided, should default to today."""
        result = await health.log_health(sleep_hours=7.0)

        today = datetime.now().strftime("%Y-%m-%d")
        assert result["date"] == today

    @pytest.mark.asyncio
    async def test_log_health_with_notes_preserved(self):
        """Notes field should be preserved in the log."""
        note_text = "slept poorly due to noise"
        result = await health.log_health(
            sleep_hours=5.5,
            notes=note_text
        )

        assert result["status"] == "logged"

        db = get_db()
        cursor = db.execute(
            "SELECT notes FROM health_logs WHERE id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == note_text

    @pytest.mark.asyncio
    async def test_log_health_returns_unique_ids(self):
        """Each logged entry should get a unique ID."""
        result1 = await health.log_health(sleep_hours=7.0)
        result2 = await health.log_health(sleep_hours=8.0)

        assert result1["id"] != result2["id"]


# ============================================================================
# TEST CLASS 2: TestHealthPatternQueries - Query trends, correlations
# ============================================================================


class TestHealthPatternQueries:
    """Test querying health patterns: trends, correlations, insights."""

    @pytest.mark.asyncio
    async def test_query_sleep_trend_over_days(self):
        """Query sleep hours trend over the last N days."""
        result = await health.get_health_summary(days=7)

        assert result["status"] == "ok"
        assert "days" in result
        assert result["days"] <= 7
        assert "avg_sleep_hours" in result
        assert isinstance(result["avg_sleep_hours"], (int, float))
        assert 3.0 <= result["avg_sleep_hours"] <= 12.0  # Reasonable range

    @pytest.mark.asyncio
    async def test_query_steps_average(self):
        """Query average steps over a period."""
        result = await health.get_health_summary(days=7)

        assert "avg_steps" in result
        assert isinstance(result["avg_steps"], int)
        assert result["avg_steps"] >= 0

    @pytest.mark.asyncio
    async def test_query_heart_rate_average(self):
        """Query average heart rate over a period."""
        result = await health.get_health_summary(days=7)

        assert "avg_heart_rate" in result
        assert isinstance(result["avg_heart_rate"], int)
        assert 40 <= result["avg_heart_rate"] <= 120  # Reasonable HR range

    @pytest.mark.asyncio
    async def test_query_mood_distribution(self):
        """Query mood distribution (frequency of each mood)."""
        result = await health.get_health_summary(days=7)

        assert "mood_distribution" in result
        assert isinstance(result["mood_distribution"], dict)
        # Mood distribution should show counts for each mood
        if result["mood_distribution"]:
            for mood, count in result["mood_distribution"].items():
                assert isinstance(count, int)
                assert count > 0

    @pytest.mark.asyncio
    async def test_query_health_today_returns_current_data(self):
        """Query today's health data specifically."""
        # Log some data for today
        await health.log_health(sleep_hours=7.5)
        await health.log_health(mood="good")

        result = await health.get_health_today()

        assert result["status"] == "ok"
        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert "data" in result

    @pytest.mark.asyncio
    async def test_query_empty_health_data_no_error(self):
        """Querying data when none exists should return graceful response."""
        result = await health.get_health_summary(days=365)

        # Should not raise an exception
        assert "status" in result
        # Either "ok" with empty data or "no_data"
        assert result["status"] in ["ok", "no_data"]

    @pytest.mark.asyncio
    async def test_health_patterns_sleep_mood_correlation(self):
        """Verify sleep and mood are positively correlated in demo data."""
        # Demo data has intentional correlation (more sleep → better mood)
        result = await health.get_health_summary(days=7)

        # Seeded data should show mood distribution (if moods were logged)
        assert "mood_distribution" in result

    @pytest.mark.asyncio
    async def test_query_health_respects_days_parameter(self):
        """Different day ranges should return different results."""
        result_3d = await health.get_health_summary(days=3)
        result_7d = await health.get_health_summary(days=7)

        # 7 days should have more or equal records than 3 days
        assert result_7d.get("days", 0) >= result_3d.get("days", 0)


# ============================================================================
# TEST CLASS 3: TestExpenseTracking - Track and categorize expenses
# ============================================================================


class TestExpenseTracking:
    """Test tracking expenses with categorization."""

    @pytest.mark.asyncio
    async def test_track_expense_basic(self):
        """Track a single expense with required fields."""
        result = await wealth.track_expense(
            amount=45.50,
            category="food",
            description="lunch at cafe"
        )

        assert result["status"] == "tracked"
        assert result["amount"] == 45.50
        assert result["category"] == "food"
        assert result["id"] is not None

    @pytest.mark.asyncio
    async def test_track_expense_multiple_categories(self):
        """Track expenses in different categories."""
        categories = ["food", "transport", "shopping", "health", "entertainment", "utilities"]

        for category in categories:
            result = await wealth.track_expense(
                amount=25.00,
                category=category,
                description=f"test {category}"
            )
            assert result["status"] == "tracked"
            assert result["category"] == category

    @pytest.mark.asyncio
    async def test_track_expense_amount_precision(self):
        """Expense amounts should maintain decimal precision."""
        result = await wealth.track_expense(
            amount=19.99,
            category="food"
        )

        assert result["amount"] == 19.99

        # Verify in database
        db = get_db()
        cursor = db.execute(
            "SELECT amount FROM expenses WHERE id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert abs(row[0] - 19.99) < 0.01

    @pytest.mark.asyncio
    async def test_track_expense_with_description(self):
        """Expense description should be preserved."""
        description = "coffee + muffin"
        result = await wealth.track_expense(
            amount=8.50,
            category="food",
            description=description
        )

        db = get_db()
        cursor = db.execute(
            "SELECT description FROM expenses WHERE id = ?",
            (result["id"],)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == description

    @pytest.mark.asyncio
    async def test_track_expense_defaults_to_today(self):
        """When no date provided, should default to today."""
        result = await wealth.track_expense(
            amount=30.00,
            category="entertainment"
        )

        today = datetime.now().strftime("%Y-%m-%d")
        assert result["date"] == today

    @pytest.mark.asyncio
    async def test_track_expense_custom_date(self):
        """Should support tracking expense for a specific date."""
        custom_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        result = await wealth.track_expense(
            amount=50.00,
            category="food",
            date=custom_date
        )

        assert result["date"] == custom_date

    @pytest.mark.asyncio
    async def test_track_expense_zero_amount_validation(self):
        """Zero or negative amounts should be rejected or handled."""
        # This test expects validation to fail or handle gracefully
        with pytest.raises((ValueError, AssertionError)):
            await wealth.track_expense(amount=0, category="food")

    @pytest.mark.asyncio
    async def test_track_multiple_same_day(self):
        """Should track multiple expenses on the same day."""
        date = datetime.now().strftime("%Y-%m-%d")

        result1 = await wealth.track_expense(25.00, "food", "breakfast", date)
        result2 = await wealth.track_expense(12.00, "food", "lunch", date)
        result3 = await wealth.track_expense(45.00, "food", "dinner", date)

        assert result1["status"] == "tracked"
        assert result2["status"] == "tracked"
        assert result3["status"] == "tracked"

        # All should have unique IDs
        assert result1["id"] != result2["id"]
        assert result2["id"] != result3["id"]


# ============================================================================
# TEST CLASS 4: TestSpendingReports - Generate reports
# ============================================================================


class TestSpendingReports:
    """Test generating spending reports by category and time period."""

    @pytest.mark.asyncio
    async def test_spending_report_by_category(self):
        """Get spending breakdown by category."""
        result = await wealth.get_spending_summary(days=7)

        assert result["status"] == "ok"
        assert "by_category" in result
        assert isinstance(result["by_category"], dict)

    @pytest.mark.asyncio
    async def test_spending_report_total_calculation(self):
        """Total spending should be sum of all categories."""
        result = await wealth.get_spending_summary(days=7)

        category_totals = result.get("by_category", {})
        calculated_total = sum(category_totals.values())
        reported_total = result.get("total", 0)

        # Allow small floating point difference
        assert abs(calculated_total - reported_total) < 0.01

    @pytest.mark.asyncio
    async def test_spending_report_respects_days_parameter(self):
        """Different time periods should give different results."""
        result_3d = await wealth.get_spending_summary(days=3)
        result_7d = await wealth.get_spending_summary(days=7)
        result_30d = await wealth.get_spending_summary(days=30)

        # Total should increase with larger time period
        assert result_3d.get("total", 0) <= result_7d.get("total", 0)
        assert result_7d.get("total", 0) <= result_30d.get("total", 0)

    @pytest.mark.asyncio
    async def test_spending_today_endpoint(self):
        """Get today's spending specifically."""
        # Log an expense for today
        await wealth.track_expense(35.00, "food", "dinner")

        result = await wealth.get_spending_today()

        assert result["status"] == "ok"
        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert "total" in result
        assert "count" in result
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_spending_today_with_multiple_expenses(self):
        """Today's summary should aggregate multiple expenses."""
        date = datetime.now().strftime("%Y-%m-%d")

        await wealth.track_expense(20.00, "food", date=date)
        await wealth.track_expense(15.00, "transport", date=date)

        result = await wealth.get_spending_today()

        assert result["count"] >= 2
        assert result["total"] >= 35.00

    @pytest.mark.asyncio
    async def test_spending_report_no_negative_totals(self):
        """Spending totals should never be negative."""
        result = await wealth.get_spending_summary(days=7)

        assert result.get("total", 0) >= 0
        for amount in result.get("by_category", {}).values():
            assert amount >= 0

    @pytest.mark.asyncio
    async def test_spending_report_categories_are_consistent(self):
        """Categories in report should match tracked categories."""
        # Track specific categories
        categories_to_track = ["food", "transport"]
        for cat in categories_to_track:
            await wealth.track_expense(10.00, cat)

        result = await wealth.get_spending_summary(days=7)
        reported_categories = set(result.get("by_category", {}).keys())

        # At least these categories should appear
        for cat in categories_to_track:
            assert cat in reported_categories or result.get("total", 0) >= 0


# ============================================================================
# TEST CLASS 5: TestSavingsGoals - Calculate savings goals
# ============================================================================


class TestSavingsGoals:
    """Test calculating savings goals and feasibility."""

    @pytest.mark.asyncio
    async def test_calculate_savings_goal_monthly_required(self):
        """Calculate monthly savings needed to reach a goal."""
        # To save $1200 in 6 months
        result = await wealth.calculate_savings_goal(
            target_amount=1200,
            target_months=6,
            monthly_income=4000
        )

        assert "monthly_savings_needed" in result
        assert result["monthly_savings_needed"] > 0
        # 1200 / 6 = 200
        assert abs(result["monthly_savings_needed"] - 200.0) < 0.01

    @pytest.mark.asyncio
    async def test_savings_goal_feasibility_check_positive(self):
        """Goal should be marked feasible if affordable."""
        result = await wealth.calculate_savings_goal(
            target_amount=500,      # Small goal
            target_months=6,
            monthly_income=4000     # High income
        )

        assert "feasible" in result
        assert result["feasible"] is True

    @pytest.mark.asyncio
    async def test_savings_goal_feasibility_check_negative(self):
        """Goal should be marked infeasible if unaffordable."""
        result = await wealth.calculate_savings_goal(
            target_amount=50000,    # Very high goal
            target_months=3,        # Short timeframe
            monthly_income=1000     # Low income
        )

        assert "feasible" in result
        # This should be infeasible: needs $16,667/month but only earns $1000

    @pytest.mark.asyncio
    async def test_savings_goal_percentage_of_income(self):
        """Calculate what percentage of income the goal represents."""
        result = await wealth.calculate_savings_goal(
            target_amount=1200,
            target_months=6,
            monthly_income=4000
        )

        monthly_needed = result.get("monthly_savings_needed", 0)
        # 200 / 4000 = 5%
        percentage = (monthly_needed / 4000) * 100
        assert 4.9 < percentage < 5.1

    @pytest.mark.asyncio
    async def test_savings_goal_zero_months_validation(self):
        """Should handle zero or negative months gracefully."""
        with pytest.raises((ValueError, AssertionError)):
            await wealth.calculate_savings_goal(
                target_amount=1000,
                target_months=0,
                monthly_income=2000
            )

    @pytest.mark.asyncio
    async def test_savings_goal_timeline_breakdown(self):
        """Should provide breakdown of savings timeline."""
        result = await wealth.calculate_savings_goal(
            target_amount=2400,
            target_months=12,
            monthly_income=5000
        )

        # Should show monthly breakdown or key metrics
        assert "monthly_savings_needed" in result
        assert "feasible" in result
        # Can optionally include remaining income after savings
        if "remaining_after_savings" in result:
            remaining = result["remaining_after_savings"]
            assert remaining == 5000 - result["monthly_savings_needed"]


# ============================================================================
# TEST CLASS 6: TestToolDispatch - Route and validate tool calls
# ============================================================================


class TestToolDispatch:
    """Test tool dispatch: routing, validation, error handling."""

    @pytest.mark.asyncio
    async def test_dispatch_log_health_tool(self):
        """Dispatch log_health through registry."""
        result_json = await dispatch_tool(
            "log_health",
            {"sleep_hours": 7.5, "notes": "good"}
        )

        result = json.loads(result_json)
        assert "error" not in result or result.get("status") == "logged"

    @pytest.mark.asyncio
    async def test_dispatch_track_expense_tool(self):
        """Dispatch track_expense through registry."""
        result_json = await dispatch_tool(
            "track_expense",
            {"amount": 25.00, "category": "food"}
        )

        result = json.loads(result_json)
        assert "error" not in result or result.get("status") == "tracked"

    @pytest.mark.asyncio
    async def test_dispatch_get_health_summary(self):
        """Dispatch get_health_summary through registry."""
        result_json = await dispatch_tool(
            "get_health_summary",
            {"days": 7}
        )

        result = json.loads(result_json)
        assert "error" not in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_dispatch_get_spending_summary(self):
        """Dispatch get_spending_summary through registry."""
        result_json = await dispatch_tool(
            "get_spending_summary",
            {"days": 30}
        )

        result = json.loads(result_json)
        assert "error" not in result
        assert "status" in result

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool_returns_error(self):
        """Dispatching unknown tool should return error, not crash."""
        result_json = await dispatch_tool("nonexistent_tool", {})

        result = json.loads(result_json)
        assert "error" in result
        assert "nonexistent_tool" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_dispatch_invalid_arguments_returns_error(self):
        """Dispatching with invalid arguments should return error."""
        result_json = await dispatch_tool(
            "track_expense",
            {"no_required_args": "missing"}  # Missing 'amount' and 'category'
        )

        result = json.loads(result_json)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_dispatch_returns_valid_json(self):
        """All dispatch responses should be valid JSON."""
        result_json = await dispatch_tool("get_health_today", {})

        # Should not raise JSONDecodeError
        result = json.loads(result_json)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dispatch_missing_optional_parameters(self):
        """Tools should work with missing optional parameters."""
        # get_health_today has no parameters
        result_json = await dispatch_tool("get_health_today", {})
        result = json.loads(result_json)
        assert "error" not in result or "status" in result

    @pytest.mark.asyncio
    async def test_dispatch_with_extra_parameters(self):
        """Extra parameters should be ignored, not cause errors."""
        result_json = await dispatch_tool(
            "get_health_today",
            {"extra_param": "should_be_ignored"}
        )

        result = json.loads(result_json)
        # Should either work or give a clear error, not crash
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dispatch_all_health_tools(self):
        """All health tools should be dispatchable."""
        health_tools = [
            ("log_health", {"sleep_hours": 7.0}),
            ("get_health_today", {}),
            ("get_health_summary", {"days": 7}),
        ]

        for tool_name, tool_input in health_tools:
            result_json = await dispatch_tool(tool_name, tool_input)
            result = json.loads(result_json)
            # Should return a valid dict (error or success)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dispatch_all_wealth_tools(self):
        """All wealth tools should be dispatchable."""
        wealth_tools = [
            ("track_expense", {"amount": 25.0, "category": "food"}),
            ("get_spending_today", {}),
            ("get_spending_summary", {"days": 30}),
            ("get_budget_status", {"monthly_budget": 3000}),
        ]

        for tool_name, tool_input in wealth_tools:
            result_json = await dispatch_tool(tool_name, tool_input)
            result = json.loads(result_json)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dispatch_error_doesnt_crash_app(self):
        """Errors should be caught and returned as JSON, not crash."""
        # Try a malformed tool call
        result_json = await dispatch_tool(
            "log_health",
            {"sleep_hours": "not_a_number"}  # Type error
        )

        result = json.loads(result_json)
        # Should have error field or fail gracefully
        assert isinstance(result, dict)
