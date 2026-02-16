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
    db = get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
    ts = f"{date} {datetime.now().strftime('%H:%M:%S')}"
    cursor = db.execute(
        "INSERT INTO expenses (amount, category, description, timestamp) VALUES (?, ?, ?, ?)",
        (amount, category, description or "", ts),
    )
    db.commit()
    return {
        "status": "tracked",
        "id": cursor.lastrowid,
        "amount": amount,
        "category": category,
        "date": date,
    }


async def get_spending_today() -> dict[str, Any]:
    """Get today's expenses."""
    db = get_db()
    date = datetime.now().strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT amount, category, description FROM expenses WHERE date(timestamp) = ?",
        (date,),
    ).fetchall()

    expenses = [{"amount": r["amount"], "category": r["category"], "description": r["description"]} for r in rows]
    total = sum(e["amount"] for e in expenses)

    return {
        "status": "ok",
        "date": date,
        "total": round(total, 2),
        "count": len(expenses),
        "expenses": expenses,
    }


async def get_spending_summary(days: int = 30) -> dict[str, Any]:
    """Get spending summary grouped by category for the last N days."""
    db = get_db()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE date(timestamp) >= ? GROUP BY category",
        (cutoff,),
    ).fetchall()

    by_category = {r["category"]: round(r["total"], 2) for r in rows}
    total = sum(by_category.values())

    return {
        "status": "ok",
        "days": days,
        "total": round(total, 2),
        "by_category": by_category,
    }


async def get_budget_status(monthly_budget: float = 3000.0) -> dict[str, Any]:
    """Check spending against a monthly budget."""
    db = get_db()
    now = datetime.now()
    start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE date(timestamp) >= ? GROUP BY category",
        (start_of_month,),
    ).fetchall()

    by_category = {r["category"]: round(r["total"], 2) for r in rows}
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
        "by_category": by_category,
    }
