"""Wealth management tools — called by Claude via function calling."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from bridge.db import get_db


async def track_expense(amount: float, category: str, description: str = "") -> dict:
    """Record an expense."""
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
        (amount, category, description),
    )

    # Get context: this week's spending in same category
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses "
        "WHERE category = ? AND timestamp >= ?",
        (category, week_ago),
    ).fetchone()["total"]

    conn.commit()
    conn.close()

    return {
        "status": "recorded",
        "amount": amount,
        "category": category,
        "description": description,
        "week_total_in_category": round(week_total, 2),
    }


async def get_spending_summary(days: int = 30, category: Optional[str] = None) -> dict:
    """Get spending summary for a time period."""
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if category:
        rows = conn.execute(
            "SELECT amount, category, description, timestamp FROM expenses "
            "WHERE category = ? AND timestamp >= ? ORDER BY timestamp DESC",
            (category, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT amount, category, description, timestamp FROM expenses "
            "WHERE timestamp >= ? ORDER BY timestamp DESC",
            (since,),
        ).fetchall()

    # Aggregate by category
    by_category: dict[str, float] = {}
    for row in rows:
        cat = row["category"]
        by_category[cat] = by_category.get(cat, 0) + row["amount"]

    total = sum(by_category.values())
    daily_avg = round(total / max(days, 1), 2)

    conn.close()

    return {
        "days": days,
        "total_spent": round(total, 2),
        "daily_average": daily_avg,
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
        "transaction_count": len(rows),
        "recent": [
            {"amount": r["amount"], "category": r["category"], "description": r["description"], "date": r["timestamp"][:10]}
            for r in rows[:5]
        ],
    }


async def calculate_savings_goal(
    target_amount: float, target_months: int, monthly_income: Optional[float] = None
) -> dict:
    """Calculate how to reach a savings target."""
    conn = get_db()

    # Get last 30 days spending to estimate monthly
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    monthly_spending = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE timestamp >= ?",
        (month_ago,),
    ).fetchone()["total"]

    # Category breakdown
    by_category = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses "
        "WHERE timestamp >= ? GROUP BY category ORDER BY total DESC",
        (month_ago,),
    ).fetchall()

    conn.close()

    monthly_needed = target_amount / max(target_months, 1)

    result = {
        "target_amount": target_amount,
        "target_months": target_months,
        "monthly_savings_needed": round(monthly_needed, 2),
        "current_monthly_spending": round(monthly_spending, 2),
        "spending_by_category": {row["category"]: round(row["total"], 2) for row in by_category},
    }

    if monthly_income:
        current_savings = monthly_income - monthly_spending
        result["monthly_income"] = monthly_income
        result["current_monthly_savings"] = round(current_savings, 2)
        result["gap"] = round(monthly_needed - current_savings, 2)
        result["feasible"] = current_savings >= monthly_needed

    return result
