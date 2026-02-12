"""AEGIS1 SQLite storage — health logs, expenses, conversations."""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

from bridge.config import settings

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    if settings.db_path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            notes TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model_used TEXT DEFAULT '',
            latency_ms REAL DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_health_metric ON health_logs(metric, timestamp);
        CREATE INDEX IF NOT EXISTS idx_expense_cat ON expenses(category, timestamp);
        CREATE INDEX IF NOT EXISTS idx_insights_created ON user_insights(created_at);
    """)
    conn.commit()
    conn.close()


def seed_demo_data(days: int = 30):
    """Seed 30 days of realistic demo data for health + expenses."""
    conn = get_db()

    # Check if data already exists
    count = conn.execute("SELECT COUNT(*) FROM health_logs").fetchone()[0]
    if count > 0:
        conn.close()
        return

    now = datetime.now()
    random.seed(42)  # Reproducible demo data

    for day_offset in range(days, 0, -1):
        ts = now - timedelta(days=day_offset)
        date_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        # Sleep hours: 5.5-8.5, trending worse on weekdays
        is_weekend = ts.weekday() >= 5
        base_sleep = 7.5 if is_weekend else 6.5
        sleep = round(base_sleep + random.gauss(0, 0.8), 1)
        sleep = max(4.0, min(10.0, sleep))
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("sleep_hours", sleep, "", date_str),
        )

        # Steps: 3000-12000
        steps = int(random.gauss(7000 if is_weekend else 5500, 2000))
        steps = max(1000, min(15000, steps))
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("steps", steps, "", date_str),
        )

        # Heart rate: 60-85 resting
        hr = int(random.gauss(72, 6))
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("heart_rate", hr, "resting", date_str),
        )

        # Mood: 1-5, correlates with sleep
        mood_base = 3.0 + (sleep - 6.5) * 0.5
        mood = round(max(1, min(5, mood_base + random.gauss(0, 0.5))), 1)
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("mood", mood, "", date_str),
        )

        # Weight: gradual trend 180-182 lbs
        weight = round(181.0 + (day_offset - 15) * 0.03 + random.gauss(0, 0.3), 1)
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("weight", weight, "lbs", date_str),
        )

        # Water: 4-10 glasses
        water = int(random.gauss(7, 1.5))
        water = max(3, min(12, water))
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("water", water, "glasses", date_str),
        )

        # Exercise: 0-60 minutes, more on weekends
        exercise = int(random.gauss(30 if is_weekend else 15, 15))
        exercise = max(0, min(90, exercise))
        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("exercise_minutes", exercise, "", date_str),
        )

        # Daily expenses (1-3 per day)
        n_expenses = random.randint(1, 3)
        expense_templates = [
            (12.50, "food", "lunch"),
            (45.00, "food", "dinner out"),
            (5.00, "food", "coffee"),
            (3.50, "transport", "bus fare"),
            (25.00, "transport", "uber"),
            (15.00, "entertainment", "movie ticket"),
            (30.00, "shopping", "online order"),
            (8.00, "food", "breakfast"),
            (60.00, "utilities", "phone bill"),
            (20.00, "health", "supplements"),
        ]
        for _ in range(n_expenses):
            amt, cat, desc = random.choice(expense_templates)
            amt = round(amt * random.uniform(0.8, 1.3), 2)
            conn.execute(
                "INSERT INTO expenses (amount, category, description, timestamp) VALUES (?, ?, ?, ?)",
                (amt, cat, desc, date_str),
            )

    conn.commit()
    conn.close()


def ensure_db():
    """Initialize DB and seed demo data if needed. Call at app startup."""
    init_db()
    seed_demo_data()
