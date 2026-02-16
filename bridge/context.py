"""
Health context builder for dynamic system prompt injection.

Provides a 7-day health snapshot that makes Claude body-aware.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from bridge.db import get_db

logger = logging.getLogger(__name__)


def build_health_context(days: int = 7) -> str:
    """
    Build a concise health snapshot for system prompt injection.

    Returns a ~200 token summary of the user's health patterns
    that makes Claude responses contextually aware.

    Args:
        days: Number of days to look back (default 7)

    Returns:
        Formatted health context string
    """
    db = get_db()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get health data
    health_rows = db.execute(
        """
        SELECT metric, value, timestamp, notes
        FROM health_logs
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        """,
        (start_date.isoformat(),)
    ).fetchall()

    if not health_rows:
        return "No recent health data available."

    # Aggregate by metric
    sleep_data = []
    exercise_data = []
    mood_data = []

    for row in health_rows:
        if row["metric"] == "sleep_hours":
            sleep_data.append(float(row["value"]))
        elif row["metric"] == "exercise_minutes":
            exercise_data.append(float(row["value"]))
        elif row["metric"] == "mood":
            mood_data.append(float(row["value"]))

    # Build context string
    context_parts = []

    # Sleep summary
    if sleep_data:
        avg_sleep = sum(sleep_data) / len(sleep_data)
        min_sleep = min(sleep_data)
        max_sleep = max(sleep_data)
        context_parts.append(
            f"Sleep: avg {avg_sleep:.1f}h/night over {len(sleep_data)} nights "
            f"(range {min_sleep:.1f}-{max_sleep:.1f}h)"
        )

    # Exercise summary
    if exercise_data:
        total_exercise = sum(exercise_data)
        avg_exercise = total_exercise / days
        context_parts.append(
            f"Exercise: {int(total_exercise)} min total, {int(avg_exercise)} min/day avg"
        )

    # Mood summary
    if mood_data:
        avg_mood = sum(mood_data) / len(mood_data)
        mood_trend = "stable"
        if len(mood_data) >= 3:
            recent_avg = sum(mood_data[:3]) / 3
            older_avg = sum(mood_data[3:]) / len(mood_data[3:]) if len(mood_data) > 3 else recent_avg
            if recent_avg > older_avg + 0.5:
                mood_trend = "improving"
            elif recent_avg < older_avg - 0.5:
                mood_trend = "declining"

        context_parts.append(
            f"Mood: avg {avg_mood:.1f}/10, {mood_trend}"
        )

    # Get recent expenses for financial context
    expense_rows = db.execute(
        """
        SELECT SUM(amount) as total, COUNT(*) as count
        FROM expenses
        WHERE timestamp >= ?
        """,
        (start_date.isoformat(),)
    ).fetchone()

    if expense_rows and expense_rows["total"]:
        total = expense_rows["total"]
        count = expense_rows["count"]
        daily_avg = total / days
        context_parts.append(
            f"Spending: ${total:.0f} total, ${daily_avg:.0f}/day avg ({count} transactions)"
        )

    if not context_parts:
        return "No recent health or spending data available."

    return " | ".join(context_parts)


def get_recent_insights(limit: int = 3) -> list[str]:
    """
    Get recent user insights saved by Claude.

    Args:
        limit: Maximum number of insights to return

    Returns:
        List of insight texts
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT insight, created_at
        FROM user_insights
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    return [row["insight"] for row in rows]
