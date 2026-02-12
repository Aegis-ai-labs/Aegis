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
    """Log health data. Defaults to today if no date provided."""
    db = await get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
    row_id = await db.log_health(
        date=date,
        sleep_hours=sleep_hours,
        steps=steps,
        heart_rate_avg=heart_rate,
        mood=mood,
        notes=notes,
    )
    return {"status": "logged", "id": row_id, "date": date}


async def get_health_today() -> dict[str, Any]:
    """Get today's health data."""
    db = await get_db()
    date = datetime.now().strftime("%Y-%m-%d")
    data = await db.get_health_by_date(date)
    if not data:
        return {"status": "no_data", "date": date, "message": "No health data logged today."}
    return {"status": "ok", "data": data}


async def get_health_summary(days: int = 7) -> dict[str, Any]:
    """Get health summary for the last N days."""
    db = await get_db()
    records = await db.get_recent_health(days=days)
    if not records:
        return {"status": "no_data", "message": f"No health data for the last {days} days."}

    avg_sleep = sum(r["sleep_hours"] for r in records if r["sleep_hours"]) / max(
        sum(1 for r in records if r["sleep_hours"]), 1
    )
    avg_steps = sum(r["steps"] for r in records if r["steps"]) // max(
        sum(1 for r in records if r["steps"]), 1
    )
    avg_hr = sum(r["heart_rate_avg"] for r in records if r["heart_rate_avg"]) // max(
        sum(1 for r in records if r["heart_rate_avg"]), 1
    )
    moods = [r["mood"] for r in records if r["mood"]]

    return {
        "status": "ok",
        "days": len(records),
        "avg_sleep_hours": round(avg_sleep, 1),
        "avg_steps": avg_steps,
        "avg_heart_rate": avg_hr,
        "mood_distribution": {m: moods.count(m) for m in set(moods)},
    }
