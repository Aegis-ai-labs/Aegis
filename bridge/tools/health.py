"""Health tracking tools — called by Claude via function calling."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from bridge.db import get_db


async def get_health_context(days: int = 7, metrics: Optional[list[str]] = None) -> dict:
    """Get user's recent health data."""
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if metrics:
        placeholders = ",".join("?" for _ in metrics)
        rows = conn.execute(
            f"SELECT metric, value, notes, timestamp FROM health_logs "
            f"WHERE metric IN ({placeholders}) AND timestamp >= ? ORDER BY timestamp DESC",
            (*metrics, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT metric, value, notes, timestamp FROM health_logs "
            "WHERE timestamp >= ? ORDER BY timestamp DESC",
            (since,),
        ).fetchall()
    conn.close()

    # Group by metric
    grouped: dict[str, list] = {}
    for row in rows:
        metric = row["metric"]
        grouped.setdefault(metric, []).append({
            "value": row["value"],
            "notes": row["notes"],
            "date": row["timestamp"][:10],
        })

    # Add summary stats per metric
    summary = {}
    for metric, entries in grouped.items():
        values = [e["value"] for e in entries]
        summary[metric] = {
            "entries": entries[:10],  # Last 10 entries
            "count": len(entries),
            "avg": round(sum(values) / len(values), 1) if values else 0,
            "min": round(min(values), 1) if values else 0,
            "max": round(max(values), 1) if values else 0,
        }

    return {"days": days, "data": summary}


async def log_health(metric: str, value: float, notes: str = "") -> dict:
    """Log a health data point."""
    conn = get_db()
    conn.execute(
        "INSERT INTO health_logs (metric, value, notes) VALUES (?, ?, ?)",
        (metric, value, notes),
    )
    conn.commit()
    conn.close()
    return {"status": "logged", "metric": metric, "value": value}


async def analyze_health_patterns(query: str, days: int = 30) -> dict:
    """Return raw health data for Claude to analyze patterns."""
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT metric, value, notes, timestamp FROM health_logs "
        "WHERE timestamp >= ? ORDER BY timestamp ASC",
        (since,),
    ).fetchall()
    conn.close()

    # Group by date for correlation analysis
    by_date: dict[str, dict] = {}
    for row in rows:
        date = row["timestamp"][:10]
        by_date.setdefault(date, {})[row["metric"]] = row["value"]

    # Calculate daily correlations (sleep vs mood, exercise vs sleep, etc.)
    daily_records = [{"date": d, **metrics} for d, metrics in sorted(by_date.items())]

    return {
        "query": query,
        "days_analyzed": days,
        "total_records": len(rows),
        "daily_data": daily_records,
    }
