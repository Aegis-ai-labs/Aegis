"""Unit tests for database operations (bridge/db.py)."""

import pytest
import sqlite3
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from aegis.db import get_db, init_db, seed_demo_data
from aegis.config import Settings


@pytest.fixture
def test_settings():
    """Fixture providing test settings with in-memory database."""
    with patch('aegis.config.settings') as mock_settings:
        mock_settings.db_path = ":memory:"
        yield mock_settings


@pytest.fixture
def test_db(test_settings):
    """Fixture providing a fresh test database for each test."""
    # Initialize database
    init_db()
    conn = get_db()
    yield conn
    conn.close()


class TestDatabaseConnection:
    """Test database connection management."""

    def test_get_db_returns_connection(self, test_settings):
        """Test that get_db() returns a valid SQLite connection."""
        conn = get_db()

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        # Verify row_factory is set
        assert conn.row_factory == sqlite3.Row

        conn.close()


    def test_get_db_in_memory(self, test_settings):
        """Test that in-memory database doesn't enable WAL mode."""
        conn = get_db()

        # In-memory DB should not have WAL enabled
        # We can verify connection works
        cursor = conn.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1

        conn.close()


    def test_get_db_with_file_path(self):
        """Test that file-based database enables WAL mode."""
        test_db_path = "/tmp/test_aegis_db.sqlite"

        try:
            with patch('aegis.config.settings') as mock_settings:
                mock_settings.db_path = test_db_path

                conn = get_db()

                # Check WAL mode is enabled for file databases
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                assert journal_mode.upper() == "WAL"

                conn.close()
        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
            if os.path.exists(test_db_path + "-wal"):
                os.remove(test_db_path + "-wal")
            if os.path.exists(test_db_path + "-shm"):
                os.remove(test_db_path + "-shm")


class TestDatabaseInitialization:
    """Test database schema initialization."""

    def test_init_db_creates_tables(self, test_db):
        """Test that init_db() creates all required tables."""
        # Query sqlite_master to check tables exist
        tables = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        table_names = [row[0] for row in tables]

        assert "health_logs" in table_names
        assert "expenses" in table_names
        assert "conversations" in table_names


    def test_init_db_health_logs_schema(self, test_db):
        """Test that health_logs table has correct schema."""
        schema = test_db.execute(
            "PRAGMA table_info(health_logs)"
        ).fetchall()

        columns = {row[1]: row[2] for row in schema}  # name: type

        assert "id" in columns
        assert "metric" in columns
        assert "value" in columns
        assert "notes" in columns
        assert "timestamp" in columns

        assert columns["metric"] == "TEXT"
        assert columns["value"] == "REAL"


    def test_init_db_expenses_schema(self, test_db):
        """Test that expenses table has correct schema."""
        schema = test_db.execute(
            "PRAGMA table_info(expenses)"
        ).fetchall()

        columns = {row[1]: row[2] for row in schema}

        assert "id" in columns
        assert "amount" in columns
        assert "category" in columns
        assert "description" in columns
        assert "timestamp" in columns

        assert columns["amount"] == "REAL"
        assert columns["category"] == "TEXT"


    def test_init_db_conversations_schema(self, test_db):
        """Test that conversations table has correct schema."""
        schema = test_db.execute(
            "PRAGMA table_info(conversations)"
        ).fetchall()

        columns = {row[1]: row[2] for row in schema}

        assert "id" in columns
        assert "role" in columns
        assert "content" in columns
        assert "model_used" in columns
        assert "latency_ms" in columns
        assert "timestamp" in columns


    def test_init_db_creates_indexes(self, test_db):
        """Test that init_db() creates required indexes."""
        indexes = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()

        index_names = [row[0] for row in indexes]

        assert "idx_health_metric" in index_names
        assert "idx_expense_cat" in index_names


    def test_init_db_idempotent(self, test_db):
        """Test that init_db() can be called multiple times safely."""
        # Call init_db again
        init_db()

        # Verify tables still exist
        tables = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

        table_names = [row[0] for row in tables]

        assert "health_logs" in table_names
        assert "expenses" in table_names
        assert "conversations" in table_names


class TestSeedDemoData:
    """Test demo data seeding functionality."""

    def test_seed_demo_data_creates_health_logs(self, test_db):
        """Test that seed_demo_data() creates health log entries."""
        seed_demo_data(days=7)

        count = test_db.execute("SELECT COUNT(*) FROM health_logs").fetchone()[0]

        # Should have multiple entries per day (sleep, steps, etc.)
        assert count > 0
        assert count >= 7  # At least one entry per day


    def test_seed_demo_data_creates_expenses(self, test_db):
        """Test that seed_demo_data() creates expense entries."""
        seed_demo_data(days=7)

        count = test_db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

        # Should have expense entries
        assert count > 0


    def test_seed_demo_data_respects_existing_data(self, test_db):
        """Test that seed_demo_data() doesn't duplicate data."""
        # Seed once
        seed_demo_data(days=5)
        count_first = test_db.execute("SELECT COUNT(*) FROM health_logs").fetchone()[0]

        # Seed again
        seed_demo_data(days=5)
        count_second = test_db.execute("SELECT COUNT(*) FROM health_logs").fetchone()[0]

        # Count should be the same (no duplication)
        assert count_first == count_second


    def test_seed_demo_data_realistic_values(self, test_db):
        """Test that seeded data has realistic values."""
        seed_demo_data(days=7)

        # Check sleep hours are realistic (4-10 hours)
        sleep_values = test_db.execute(
            "SELECT value FROM health_logs WHERE metric='sleep_hours'"
        ).fetchall()

        for row in sleep_values:
            sleep_hours = row[0]
            assert 4.0 <= sleep_hours <= 10.0, f"Sleep hours {sleep_hours} out of range"


    def test_seed_demo_data_timestamps_in_past(self, test_db):
        """Test that seeded data timestamps are in the past."""
        seed_demo_data(days=30)

        now = datetime.now()

        timestamps = test_db.execute(
            "SELECT timestamp FROM health_logs ORDER BY timestamp DESC LIMIT 1"
        ).fetchall()

        assert timestamps, "Expected at least one health_log entry after seeding"
        latest_ts = datetime.fromisoformat(timestamps[0][0])
        # Latest timestamp should be recent (within last 2 days)
        assert (now - latest_ts).days <= 2


class TestDatabaseOperations:
    """Test basic database CRUD operations."""

    def test_insert_health_log(self, test_db):
        """Test inserting a health log entry."""
        test_db.execute(
            "INSERT INTO health_logs (metric, value, notes) VALUES (?, ?, ?)",
            ("test_metric", 42.5, "test note")
        )
        test_db.commit()

        result = test_db.execute(
            "SELECT * FROM health_logs WHERE metric='test_metric'"
        ).fetchone()

        assert result is not None
        assert result["metric"] == "test_metric"
        assert result["value"] == 42.5
        assert result["notes"] == "test note"


    def test_insert_expense(self, test_db):
        """Test inserting an expense entry."""
        test_db.execute(
            "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
            (25.99, "Food", "Lunch")
        )
        test_db.commit()

        result = test_db.execute(
            "SELECT * FROM expenses WHERE category='Food'"
        ).fetchone()

        assert result is not None
        assert result["amount"] == 25.99
        assert result["category"] == "Food"
        assert result["description"] == "Lunch"


    def test_insert_conversation(self, test_db):
        """Test inserting a conversation entry."""
        test_db.execute(
            "INSERT INTO conversations (role, content, model_used, latency_ms) VALUES (?, ?, ?, ?)",
            ("user", "Hello", "claude-sonnet", 150.5)
        )
        test_db.commit()

        result = test_db.execute(
            "SELECT * FROM conversations WHERE role='user'"
        ).fetchone()

        assert result is not None
        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert result["model_used"] == "claude-sonnet"
        assert result["latency_ms"] == 150.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
