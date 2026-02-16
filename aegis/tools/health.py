"""Health tracking tool functions — direct DB calls, <50ms."""

from datetime import datetime, timedelta
from typing import Any

from ..db import get_db


async def log_health(
    sleep_hours: float = None,
    steps: int = None,
    heart_rate: int = None,
    mood: str = None,
    notes: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Log health data. Inserts one row per metric into health_logs."""
    db = get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
    ts = f"{date} {datetime.now().strftime('%H:%M:%S')}"
    logged = []

    if sleep_hours is not None:
        db.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("sleep_hours", sleep_hours, notes or "", ts),
        )
        logged.append(f"sleep: {sleep_hours}h")

    if steps is not None:
        db.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("steps", steps, notes or "", ts),
        )
        logged.append(f"steps: {steps}")

    if heart_rate is not None:
        db.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("heart_rate", heart_rate, notes or "", ts),
        )
        logged.append(f"heart rate: {heart_rate} bpm")

    if mood is not None:
        # Map mood string to numeric value for storage
        mood_map = {"great": 5, "good": 4, "okay": 3, "tired": 2, "stressed": 1}
        mood_val = mood_map.get(mood, 3)
        db.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("mood", mood_val, mood, ts),
        )
        logged.append(f"mood: {mood}")

    db.commit()

    if not logged:
        return {"status": "no_data", "message": "No health metrics provided."}

    return {"status": "logged", "date": date, "logged": logged}


async def get_health_today() -> dict[str, Any]:
    """Get today's health data from health_logs."""
    db = get_db()
    date = datetime.now().strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT metric, value, notes FROM health_logs WHERE date(timestamp) = ?",
        (date,),
    ).fetchall()

    if not rows:
        return {"status": "no_data", "date": date, "message": "No health data logged today."}

    data = {}
    for row in rows:
        metric, value, notes = row["metric"], row["value"], row["notes"]
        data[metric] = {"value": value, "notes": notes}

    return {"status": "ok", "date": date, "data": data}


async def get_health_summary(days: int = 7) -> dict[str, Any]:
    """Get health summary for the last N days."""
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT metric, value FROM health_logs WHERE date(timestamp) >= ?",
        (cutoff,),
    ).fetchall()

    if not rows:
        return {"status": "no_data", "message": f"No health data for the last {days} days."}

    # Group by metric
    metrics: dict[str, list[float]] = {}
    for row in rows:
        metrics.setdefault(row["metric"], []).append(row["value"])

    summary = {}
    for metric, values in metrics.items():
        avg = sum(values) / len(values)
        summary[metric] = {"avg": round(avg, 1), "count": len(values)}

    return {
        "status": "ok",
        "days": days,
        "metrics": summary,
    }
