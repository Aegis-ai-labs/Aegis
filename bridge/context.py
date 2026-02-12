"""Build dynamic context from user health data."""

from typing import Optional
from .db import Database


async def build_health_context(db: Database) -> str:
    """
    Build a health context string from recent 7-day health data.
    
    Args:
        db: Database instance with connected async connection
        
    Returns:
        A formatted string like "User health: Sleep 6.4h, Steps 5200/day, HR 72 bpm"
        Returns empty string if no health data available.
    """
    health_logs = await db.get_recent_health(days=7)
    
    if not health_logs:
        return ""
    
    # Calculate averages
    sleep_values = [log["sleep_hours"] for log in health_logs if log["sleep_hours"] is not None]
    steps_values = [log["steps"] for log in health_logs if log["steps"] is not None]
    hr_values = [log["heart_rate_avg"] for log in health_logs if log["heart_rate_avg"] is not None]
    mood_values = [log["mood"] for log in health_logs if log["mood"] is not None]
    
    parts = []
    
    if sleep_values:
        avg_sleep = sum(sleep_values) / len(sleep_values)
        parts.append(f"Sleep {avg_sleep:.1f}h")
    
    if steps_values:
        avg_steps = sum(steps_values) / len(steps_values)
        parts.append(f"Steps {avg_steps:.0f}/day")
    
    if hr_values:
        avg_hr = sum(hr_values) / len(hr_values)
        parts.append(f"HR {avg_hr:.0f} bpm")
    
    if mood_values:
        # Use most recent mood as representative
        mood = mood_values[-1]
        parts.append(f"Mood {mood}")
    
    if not parts:
        return ""
    
    return f"User health: {", ".join(parts)}"
