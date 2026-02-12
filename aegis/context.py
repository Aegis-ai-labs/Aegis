"""Build dynamic context from user health data."""

from typing import Optional
import sqlite3


async def build_health_context(db: Optional[sqlite3.Connection]) -> str:
    """
    Build a health context string from recent 7-day health data.

    Args:
        db: SQLite database connection (optional)

    Returns:
        A formatted string like "User health: Sleep 6.4h, Steps 5200/day, HR 72 bpm"
        Returns empty string if no health data available.
    """
    if not db:
        return ""

    # Get recent health logs from the past 7 days
    cursor = db.execute("""
        SELECT metric, value FROM health_logs
        WHERE datetime(timestamp) >= datetime('now', '-7 days')
        ORDER BY timestamp DESC
    """)
    health_logs = cursor.fetchall()

    if not health_logs:
        return ""

    # Group values by metric
    metrics = {}
    for metric, value in health_logs:
        if metric not in metrics:
            metrics[metric] = []
        metrics[metric].append(value)

    parts = []

    # Format each metric with its average
    for metric, values in sorted(metrics.items()):
        avg_value = sum(values) / len(values)
        if metric.lower() in ("sleep", "sleep_hours"):
            parts.append(f"Sleep {avg_value:.1f}h")
        elif metric.lower() in ("steps", "step_count"):
            parts.append(f"Steps {avg_value:.0f}/day")
        elif metric.lower() in ("heart_rate", "hr", "heart_rate_avg"):
            parts.append(f"HR {avg_value:.0f} bpm")
        elif metric.lower() == "mood":
            # Use most recent mood
            parts.append(f"Mood {values[-1]}")
        else:
            parts.append(f"{metric}: {avg_value:.1f}")

    if not parts:
        return ""

    parts_str = ", ".join(parts)
    return f"User health: {parts_str}"
