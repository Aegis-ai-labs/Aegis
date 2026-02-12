"""
AEGIS1 Database Module — SQLite schema, CRUD operations, demo data seeding.
"""

import aiosqlite
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path
import json

from .config import settings


# Schema definitions
HEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sleep_hours REAL,
    steps INTEGER,
    heart_rate_avg INTEGER,
    mood TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

WEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_health_date ON health_logs(date);",
    "CREATE INDEX IF NOT EXISTS idx_expense_date ON expenses(date);",
    "CREATE INDEX IF NOT EXISTS idx_expense_category ON expenses(category);",
]


class Database:
    """Async SQLite database wrapper for AEGIS1."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self):
        """Create tables and indexes."""
        await self._conn.execute(HEALTH_TABLE)
        await self._conn.execute(WEALTH_TABLE)
        for index in INDEXES:
            await self._conn.execute(index)
        await self._conn.commit()

    # Health CRUD Operations

    async def log_health(
        self,
        date: str,
        sleep_hours: Optional[float] = None,
        steps: Optional[int] = None,
        heart_rate_avg: Optional[int] = None,
        mood: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Log health data for a specific date."""
        cursor = await self._conn.execute(
            """
            INSERT INTO health_logs (date, sleep_hours, steps, heart_rate_avg, mood, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (date, sleep_hours, steps, heart_rate_avg, mood, notes),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_health_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """Get health data for a specific date."""
        cursor = await self._conn.execute(
            "SELECT * FROM health_logs WHERE date = ? ORDER BY created_at DESC LIMIT 1",
            (date,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_health_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get health data for a date range."""
        cursor = await self._conn.execute(
            "SELECT * FROM health_logs WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date, end_date),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_recent_health(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get health data for the last N days."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return await self.get_health_range(start_date, end_date)

    # Wealth CRUD Operations

    async def track_expense(
        self, date: str, amount: float, category: str, description: Optional[str] = None
    ) -> int:
        """Log an expense."""
        cursor = await self._conn.execute(
            """
            INSERT INTO expenses (date, amount, category, description)
            VALUES (?, ?, ?, ?)
            """,
            (date, amount, category, description),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def get_expenses_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Get all expenses for a specific date."""
        cursor = await self._conn.execute(
            "SELECT * FROM expenses WHERE date = ? ORDER BY created_at DESC",
            (date,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_expenses_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get expenses for a date range."""
        cursor = await self._conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC",
            (start_date, end_date),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_spending_by_category(
        self, start_date: str, end_date: str
    ) -> Dict[str, float]:
        """Get total spending by category for a date range."""
        cursor = await self._conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (start_date, end_date),
        )
        rows = await cursor.fetchall()
        return {row["category"]: row["total"] for row in rows}

    async def get_recent_expenses(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get expenses for the last N days."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return await self.get_expenses_range(start_date, end_date)


async def seed_demo_data(db: Database, days: int = 30):
    """
    Seed realistic demo data for the last N days.
    Uses random.seed(42) for reproducibility.
    """
    random.seed(42)  # Reproducible random data
    end_date = datetime.now()

    # Demo data parameters
    MOODS = ["great", "good", "okay", "tired", "stressed"]
    CATEGORIES = ["food", "transport", "shopping", "health", "entertainment", "utilities"]

    # Expense descriptions by category
    EXPENSE_DESCRIPTIONS = {
        "food": ["lunch", "dinner", "groceries", "coffee", "snacks"],
        "transport": ["gas", "uber", "parking", "metro card"],
        "shopping": ["clothes", "electronics", "household items"],
        "health": ["pharmacy", "gym membership", "doctor visit"],
        "entertainment": ["movie", "concert", "streaming service"],
        "utilities": ["electricity", "internet", "phone bill"],
    }

    print(f"Seeding {days} days of demo data...")

    for i in range(days):
        date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")

        # Health data: realistic patterns with some variation
        sleep_hours = round(random.gauss(7.2, 0.8), 1)  # Mean 7.2h, std 0.8h
        sleep_hours = max(5.0, min(9.5, sleep_hours))  # Clamp to realistic range

        steps = int(random.gauss(8500, 2500))  # Mean 8500, std 2500
        steps = max(2000, min(18000, steps))

        heart_rate = int(random.gauss(68, 5))  # Resting heart rate
        heart_rate = max(55, min(85, heart_rate))

        mood = random.choices(
            MOODS, weights=[0.2, 0.35, 0.25, 0.15, 0.05]  # Bias toward positive
        )[0]

        # Insert health log
        await db.log_health(
            date=date,
            sleep_hours=sleep_hours,
            steps=steps,
            heart_rate_avg=heart_rate,
            mood=mood,
            notes=None,
        )

        # Expenses: 1-4 per day with realistic amounts
        num_expenses = random.choices([1, 2, 3, 4], weights=[0.2, 0.4, 0.3, 0.1])[0]

        for _ in range(num_expenses):
            category = random.choice(CATEGORIES)

            # Category-specific amount ranges
            if category == "food":
                amount = round(random.uniform(8, 65), 2)
            elif category == "transport":
                amount = round(random.uniform(5, 50), 2)
            elif category == "shopping":
                amount = round(random.uniform(20, 150), 2)
            elif category == "health":
                amount = round(random.uniform(15, 120), 2)
            elif category == "entertainment":
                amount = round(random.uniform(10, 80), 2)
            elif category == "utilities":
                amount = round(random.uniform(50, 200), 2)

            description = random.choice(EXPENSE_DESCRIPTIONS[category])

            await db.track_expense(
                date=date,
                amount=amount,
                category=category,
                description=description,
            )

    print(f"✅ Demo data seeded: {days} days of health + expenses")


# Global database instance
_db_instance: Optional[Database] = None


async def get_db() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        await _db_instance.connect()

        # Check if data exists, seed if empty
        cursor = await _db_instance._conn.execute(
            "SELECT COUNT(*) as count FROM health_logs"
        )
        row = await cursor.fetchone()
        if row["count"] == 0:
            await seed_demo_data(_db_instance, days=30)

    return _db_instance


async def close_db():
    """Close the global database instance."""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None
