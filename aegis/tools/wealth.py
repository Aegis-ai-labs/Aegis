"""Wealth/expense tracking tool functions — direct DB calls, <50ms."""

import calendar
from datetime import datetime, timedelta
from typing import Any

from ..db import get_db


async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    db = await get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
    row_id = await db.track_expense(
        date=date, amount=amount, category=category, description=description
    )
    return {"status": "tracked", "id": row_id, "amount": amount, "category": category, "date": date}


async def get_spending_today() -> dict[str, Any]:
    """Get today's expenses."""
    db = await get_db()
    date = datetime.now().strftime("%Y-%m-%d")
    expenses = await db.get_expenses_by_date(date)
    total = sum(e["amount"] for e in expenses)
    return {
        "status": "ok",
        "date": date,
        "total": round(total, 2),
        "count": len(expenses),
        "expenses": expenses,
    }


async def get_spending_summary(days: int = 30) -> dict[str, Any]:
    """Get spending summary for the last N days."""
    db = await get_db()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    by_category = await db.get_spending_by_category(start_date, end_date)
    total = sum(by_category.values())

    return {
        "status": "ok",
        "days": days,
        "total": round(total, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }


async def get_budget_status(monthly_budget: float = 3000.0) -> dict[str, Any]:
    """Check spending against a monthly budget."""
    db = await get_db()
    now = datetime.now()
    start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    by_category = await db.get_spending_by_category(start_of_month, end_date)
    total_spent = sum(by_category.values())
    remaining = monthly_budget - total_spent
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    days_left = last_day_of_month - now.day

    return {
        "status": "ok",
        "month": now.strftime("%B %Y"),
        "budget": monthly_budget,
        "spent": round(total_spent, 2),
        "remaining": round(remaining, 2),
        "days_left_in_month": days_left,
        "daily_allowance": round(remaining / max(days_left, 1), 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }
