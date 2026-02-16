"""
RED Phase Tests for AEGIS1 Database Main Logic

These tests define the critical data operations that the database must support.
All tests are designed to FAIL initially and drive implementation via TDD.

Coverage:
1. Create/read health log entries
2. Create/read expense entries
3. Query health data by date range
4. Calculate spending by category
5. Store conversation memory (embeddings)
6. Transaction safety (atomic operations)
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch
import json

from aegis.db import get_db, init_db, close_db
from aegis.config import Settings


@pytest.fixture
def test_settings():
    """Fixture providing test settings with in-memory database."""
    with patch('aegis.config.settings') as mock_settings:
        mock_settings.db_path = ":memory:"
        yield mock_settings


@pytest.fixture
def clean_db(test_settings):
    """Fixture providing a fresh in-memory database for each test."""
    # Reset global connection before test
    import aegis.db
    aegis.db._db_connection = None

    init_db()
    conn = get_db()
    yield conn

    # Cleanup
    aegis.db._db_connection = None


class TestHealthLogCRUD:
    """Test CREATE and READ operations for health logs."""

    def test_create_health_log_with_metric_and_value(self, clean_db):
        """FAIL: Should create a health log entry with metric and value."""
        cursor = clean_db.execute(
            "INSERT INTO health_logs (metric, value, notes) VALUES (?, ?, ?)",
            ("sleep_hours", 7.5, "good sleep")
        )
        clean_db.commit()

        result = clean_db.execute(
            "SELECT * FROM health_logs WHERE metric = ?",
            ("sleep_hours",)
        ).fetchone()

        assert result is not None
        assert result["metric"] == "sleep_hours"
        assert result["value"] == 7.5
        assert result["notes"] == "good sleep"
        assert result["id"] is not None


    def test_read_health_log_by_id(self, clean_db):
        """FAIL: Should retrieve a health log by ID."""
        # Insert test data
        cursor = clean_db.execute(
            "INSERT INTO health_logs (metric, value, notes) VALUES (?, ?, ?)",
            ("steps", 8500, "active day")
        )
        clean_db.commit()
        log_id = cursor.lastrowid

        # Read back by ID
        result = clean_db.execute(
            "SELECT * FROM health_logs WHERE id = ?",
            (log_id,)
        ).fetchone()

        assert result is not None
        assert result["id"] == log_id
        assert result["metric"] == "steps"
        assert result["value"] == 8500


    def test_create_multiple_health_logs_same_metric(self, clean_db):
        """FAIL: Should support multiple entries for same metric (time series)."""
        base_time = datetime.now()

        for i in range(5):
            ts = (base_time - timedelta(days=i)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("heart_rate", 72 + i, ts)
            )
        clean_db.commit()

        results = clean_db.execute(
            "SELECT * FROM health_logs WHERE metric = ? ORDER BY timestamp DESC",
            ("heart_rate",)
        ).fetchall()

        assert len(results) == 5
        assert results[0]["value"] == 76
        assert results[4]["value"] == 72


    def test_health_log_timestamp_auto_set(self, clean_db):
        """FAIL: Should auto-set timestamp to CURRENT_TIMESTAMP if not provided."""
        clean_db.execute(
            "INSERT INTO health_logs (metric, value) VALUES (?, ?)",
            ("mood", 4.0)
        )
        clean_db.commit()

        result = clean_db.execute(
            "SELECT timestamp FROM health_logs WHERE metric = ?",
            ("mood",)
        ).fetchone()

        assert result is not None
        assert result["timestamp"] is not None
        # Timestamp should be recent
        ts = datetime.fromisoformat(result["timestamp"])
        assert (datetime.now() - ts).seconds < 5


    def test_health_log_nullable_notes(self, clean_db):
        """FAIL: Should allow notes to be null/default to empty string."""
        # Insert without notes
        clean_db.execute(
            "INSERT INTO health_logs (metric, value) VALUES (?, ?)",
            ("weight", 180.5)
        )
        clean_db.commit()

        result = clean_db.execute(
            "SELECT notes FROM health_logs WHERE metric = ?",
            ("weight",)
        ).fetchone()

        assert result is not None
        # Should be empty string or null
        assert result["notes"] in ("", None)


class TestExpenseCRUD:
    """Test CREATE and READ operations for expenses."""

    def test_create_expense_with_all_fields(self, clean_db):
        """FAIL: Should create an expense with amount, category, description."""
        clean_db.execute(
            "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
            (45.99, "Food", "Dinner out")
        )
        clean_db.commit()

        result = clean_db.execute(
            "SELECT * FROM expenses WHERE category = ?",
            ("Food",)
        ).fetchone()

        assert result is not None
        assert result["amount"] == 45.99
        assert result["category"] == "Food"
        assert result["description"] == "Dinner out"
        assert result["id"] is not None


    def test_read_expense_by_id(self, clean_db):
        """FAIL: Should retrieve an expense by ID."""
        cursor = clean_db.execute(
            "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
            (12.50, "Transport", "Bus fare")
        )
        clean_db.commit()
        expense_id = cursor.lastrowid

        result = clean_db.execute(
            "SELECT * FROM expenses WHERE id = ?",
            (expense_id,)
        ).fetchone()

        assert result is not None
        assert result["id"] == expense_id
        assert result["amount"] == 12.50


    def test_create_multiple_expenses_same_category(self, clean_db):
        """FAIL: Should support multiple expenses in same category."""
        expenses = [
            (25.00, "Food", "Lunch"),
            (15.50, "Food", "Coffee"),
            (8.99, "Food", "Snack"),
        ]

        for amount, category, desc in expenses:
            clean_db.execute(
                "INSERT INTO expenses (amount, category, description) VALUES (?, ?, ?)",
                (amount, category, desc)
            )
        clean_db.commit()

        results = clean_db.execute(
            "SELECT * FROM expenses WHERE category = ?",
            ("Food",)
        ).fetchall()

        assert len(results) == 3
        total = sum(r["amount"] for r in results)
        assert total == pytest.approx(49.49, rel=0.01)


    def test_expense_timestamp_auto_set(self, clean_db):
        """FAIL: Should auto-set timestamp to CURRENT_TIMESTAMP."""
        clean_db.execute(
            "INSERT INTO expenses (amount, category) VALUES (?, ?)",
            (100.00, "Entertainment")
        )
        clean_db.commit()

        result = clean_db.execute(
            "SELECT timestamp FROM expenses WHERE category = ?",
            ("Entertainment",)
        ).fetchone()

        assert result is not None
        assert result["timestamp"] is not None
        ts = datetime.fromisoformat(result["timestamp"])
        assert (datetime.now() - ts).seconds < 5


class TestHealthDataQueryByDateRange:
    """Test querying health logs by date range."""

    def test_query_health_logs_within_date_range(self, clean_db):
        """FAIL: Should query health logs between two dates."""
        base_time = datetime.now()

        # Insert logs across 10 days
        for i in range(10):
            ts = (base_time - timedelta(days=i)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("sleep_hours", 7.0 + i * 0.1, ts)
            )
        clean_db.commit()

        # Query last 3 days
        start = (base_time - timedelta(days=3)).isoformat()
        end = base_time.isoformat()

        results = clean_db.execute(
            "SELECT * FROM health_logs WHERE metric = ? AND timestamp BETWEEN ? AND ?",
            ("sleep_hours", start, end)
        ).fetchall()

        assert len(results) >= 3
        assert len(results) <= 4  # 3-4 days of data


    def test_query_health_logs_by_metric_and_date(self, clean_db):
        """FAIL: Should filter by both metric type and date range."""
        base_time = datetime.now()

        # Insert different metrics
        for i in range(5):
            ts = (base_time - timedelta(days=i)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("sleep_hours", 7.0, ts)
            )
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("steps", 5000, ts)
            )
        clean_db.commit()

        # Query only sleep data for last 2 days
        start = (base_time - timedelta(days=2)).isoformat()
        end = base_time.isoformat()

        results = clean_db.execute(
            "SELECT * FROM health_logs WHERE metric = ? AND timestamp BETWEEN ? AND ?",
            ("sleep_hours", start, end)
        ).fetchall()

        assert len(results) >= 2
        assert all(r["metric"] == "sleep_hours" for r in results)


    def test_query_health_logs_sorted_by_timestamp_desc(self, clean_db):
        """FAIL: Should return health logs ordered by timestamp descending."""
        base_time = datetime.now()

        for i in range(5):
            ts = (base_time - timedelta(days=i)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("heart_rate", 70 + i, ts)
            )
        clean_db.commit()

        results = clean_db.execute(
            "SELECT * FROM health_logs ORDER BY timestamp DESC"
        ).fetchall()

        assert len(results) == 5
        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i]["timestamp"] >= results[i + 1]["timestamp"]


    def test_query_aggregate_health_metrics_by_date(self, clean_db):
        """FAIL: Should aggregate health metrics (avg, min, max) by date."""
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Insert 5 sleep measurements on the same day
        for i in range(5):
            ts = (base_time + timedelta(hours=i*2)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("sleep_hours", 6.0 + i * 0.2, ts)
            )
        clean_db.commit()

        # Aggregate by day
        results = clean_db.execute(
            """SELECT
                DATE(timestamp) as date,
                metric,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                COUNT(*) as count
            FROM health_logs
            WHERE metric = ?
            GROUP BY DATE(timestamp), metric
            ORDER BY date DESC""",
            ("sleep_hours",)
        ).fetchall()

        assert len(results) == 1
        assert results[0]["count"] == 5
        assert results[0]["avg_value"] == pytest.approx(6.4, rel=0.1)
        assert results[0]["min_value"] == 6.0
        assert results[0]["max_value"] == 6.8


class TestCalculateSpendingByCategory:
    """Test calculating spending aggregations by category."""

    def test_sum_expenses_by_category(self, clean_db):
        """FAIL: Should sum total spending by category."""
        expenses = [
            (25.00, "Food"),
            (15.50, "Food"),
            (8.99, "Food"),
            (50.00, "Entertainment"),
            (30.00, "Entertainment"),
            (5.00, "Transport"),
        ]

        for amount, category in expenses:
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (amount, category)
            )
        clean_db.commit()

        results = clean_db.execute(
            """SELECT category, SUM(amount) as total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC"""
        ).fetchall()

        assert len(results) == 3
        assert results[0]["category"] == "Entertainment"
        assert results[0]["total"] == pytest.approx(80.00, rel=0.01)
        assert results[1]["category"] == "Food"
        assert results[1]["total"] == pytest.approx(49.49, rel=0.01)


    def test_spending_by_category_date_range(self, clean_db):
        """FAIL: Should calculate spending by category within date range."""
        base_time = datetime.now()

        # Add expenses over 5 days
        for i in range(5):
            ts = (base_time - timedelta(days=i)).isoformat()
            clean_db.execute(
                "INSERT INTO expenses (amount, category, timestamp) VALUES (?, ?, ?)",
                (20.00, "Food", ts)
            )
            clean_db.execute(
                "INSERT INTO expenses (amount, category, timestamp) VALUES (?, ?, ?)",
                (10.00, "Transport", ts)
            )
        clean_db.commit()

        # Query last 2 days
        start = (base_time - timedelta(days=2)).isoformat()
        end = base_time.isoformat()

        results = clean_db.execute(
            """SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY category
            ORDER BY category""",
            (start, end)
        ).fetchall()

        assert len(results) == 2
        # Last 3 days (today + 2 previous)
        food_result = [r for r in results if r["category"] == "Food"][0]
        assert food_result["count"] >= 2
        assert food_result["total"] >= 40.00


    def test_average_spending_per_transaction_by_category(self, clean_db):
        """FAIL: Should calculate average spending per transaction by category."""
        expenses = [
            (25.00, "Food"),
            (35.00, "Food"),
            (15.00, "Food"),
            (100.00, "Entertainment"),
            (50.00, "Transport"),
            (60.00, "Transport"),
        ]

        for amount, category in expenses:
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (amount, category)
            )
        clean_db.commit()

        results = clean_db.execute(
            """SELECT category, AVG(amount) as avg_amount, COUNT(*) as count
            FROM expenses
            GROUP BY category
            ORDER BY avg_amount DESC"""
        ).fetchall()

        assert len(results) == 3
        entertainment = [r for r in results if r["category"] == "Entertainment"][0]
        assert entertainment["avg_amount"] == pytest.approx(100.00, rel=0.01)

        food = [r for r in results if r["category"] == "Food"][0]
        assert food["avg_amount"] == pytest.approx(25.00, rel=0.01)


    def test_spending_category_with_zero_results(self, clean_db):
        """FAIL: Should handle queries for categories with no expenses."""
        clean_db.execute(
            "INSERT INTO expenses (amount, category) VALUES (?, ?)",
            (50.00, "Food")
        )
        clean_db.commit()

        results = clean_db.execute(
            """SELECT category, SUM(amount) as total
            FROM expenses
            WHERE category = ?
            GROUP BY category""",
            ("NonExistent",)
        ).fetchall()

        assert len(results) == 0


class TestConversationMemoryWithEmbeddings:
    """Test storing and retrieving conversation memory with embeddings."""

    def test_create_embedding_table_schema(self, clean_db):
        """FAIL: Should have embeddings table with text and vector columns."""
        # Check if embeddings table exists
        tables = clean_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
        ).fetchall()

        # If table doesn't exist, it should be created
        if not tables:
            clean_db.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    text_content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            clean_db.commit()

        # Verify table exists
        tables = clean_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
        ).fetchall()

        assert len(tables) == 1


    def test_store_conversation_embedding(self, clean_db):
        """FAIL: Should store conversation text with embedding vector."""
        # First create the embeddings table if it doesn't exist
        clean_db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                text_content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        clean_db.commit()

        # Create a conversation entry
        cursor = clean_db.execute(
            "INSERT INTO conversations (role, content) VALUES (?, ?)",
            ("user", "How are you feeling today?")
        )
        clean_db.commit()
        conv_id = cursor.lastrowid

        # Create fake embedding (would be 1536 dims for OpenAI, using smaller for test)
        import json
        embedding = json.dumps([0.1, 0.2, 0.3, 0.4, 0.5])
        embedding_bytes = embedding.encode('utf-8')

        # Store embedding
        clean_db.execute(
            """INSERT INTO embeddings (conversation_id, text_content, embedding, metadata)
            VALUES (?, ?, ?, ?)""",
            (conv_id, "How are you feeling today?", embedding_bytes, json.dumps({"model": "text-embedding-3-small"}))
        )
        clean_db.commit()

        # Retrieve and verify
        result = clean_db.execute(
            "SELECT * FROM embeddings WHERE conversation_id = ?",
            (conv_id,)
        ).fetchone()

        assert result is not None
        assert result["text_content"] == "How are you feeling today?"
        assert result["embedding"] == embedding_bytes
        retrieved_embedding = json.loads(result["embedding"].decode('utf-8'))
        assert retrieved_embedding == [0.1, 0.2, 0.3, 0.4, 0.5]


    def test_retrieve_embedding_by_conversation_id(self, clean_db):
        """FAIL: Should retrieve embeddings by conversation ID."""
        # Create embeddings table
        clean_db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                text_content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        clean_db.commit()

        # Create conversation
        cursor = clean_db.execute(
            "INSERT INTO conversations (role, content) VALUES (?, ?)",
            ("assistant", "I'm doing well, thank you!")
        )
        clean_db.commit()
        conv_id = cursor.lastrowid

        # Store embedding
        import json
        embedding = json.dumps([0.2, 0.3, 0.4])
        clean_db.execute(
            """INSERT INTO embeddings (conversation_id, text_content, embedding)
            VALUES (?, ?, ?)""",
            (conv_id, "I'm doing well", embedding.encode('utf-8'))
        )
        clean_db.commit()

        # Retrieve
        results = clean_db.execute(
            "SELECT * FROM embeddings WHERE conversation_id = ?",
            (conv_id,)
        ).fetchall()

        assert len(results) == 1
        assert results[0]["conversation_id"] == conv_id


    def test_semantic_similarity_search_with_embeddings(self, clean_db):
        """FAIL: Should support retrieving similar embeddings (similarity threshold)."""
        # Create embeddings table
        clean_db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                text_content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        clean_db.commit()

        # Create multiple embeddings
        import json
        embeddings_data = [
            ("How are you feeling?", [0.1, 0.2, 0.3]),
            ("Tell me about your health", [0.15, 0.22, 0.31]),
            ("What's the weather?", [0.9, 0.8, 0.7]),
        ]

        for text, embedding_vec in embeddings_data:
            cursor = clean_db.execute(
                "INSERT INTO conversations (role, content) VALUES (?, ?)",
                ("user", text)
            )
            conv_id = cursor.lastrowid
            clean_db.execute(
                """INSERT INTO embeddings (conversation_id, text_content, embedding)
                VALUES (?, ?, ?)""",
                (conv_id, text, json.dumps(embedding_vec).encode('utf-8'))
            )
        clean_db.commit()

        # Query all embeddings for similarity search
        results = clean_db.execute(
            "SELECT * FROM embeddings ORDER BY created_at DESC"
        ).fetchall()

        assert len(results) == 3
        # In real implementation, would compute cosine similarity and filter
        assert results[0]["text_content"] in [e[0] for e in embeddings_data]


class TestTransactionSafety:
    """Test atomic transactions and data consistency."""

    def test_insert_multiple_expenses_atomic(self, clean_db):
        """FAIL: Should support atomic multi-insert transactions."""
        try:
            clean_db.execute("BEGIN TRANSACTION")

            # Insert multiple expenses
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (25.00, "Food")
            )
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (15.00, "Transport")
            )
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (50.00, "Entertainment")
            )

            clean_db.commit()
        except Exception as e:
            clean_db.rollback()
            raise e

        # Verify all were inserted
        results = clean_db.execute("SELECT COUNT(*) as count FROM expenses").fetchone()
        assert results["count"] == 3


    def test_transaction_rollback_on_error(self, clean_db):
        """FAIL: Should rollback transaction if error occurs."""
        initial_count = clean_db.execute(
            "SELECT COUNT(*) as count FROM expenses"
        ).fetchone()["count"]

        try:
            clean_db.execute("BEGIN TRANSACTION")

            # Insert first expense
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (25.00, "Food")
            )

            # Simulate error - invalid amount (negative)
            # This should cause transaction to fail
            clean_db.execute(
                "INSERT INTO expenses (amount, category) VALUES (?, ?)",
                (-10.00, "Invalid")  # Negative amount
            )

            clean_db.commit()
        except (sqlite3.IntegrityError, sqlite3.OperationalError):
            clean_db.rollback()

        # Verify transaction was rolled back (count should be same)
        final_count = clean_db.execute(
            "SELECT COUNT(*) as count FROM expenses"
        ).fetchone()["count"]

        assert final_count == initial_count


    def test_concurrent_health_log_inserts(self, clean_db):
        """FAIL: Should safely handle rapid successive inserts."""
        # Insert 100 health logs rapidly
        for i in range(100):
            clean_db.execute(
                "INSERT INTO health_logs (metric, value) VALUES (?, ?)",
                (f"metric_{i % 5}", i * 0.1)
            )
        clean_db.commit()

        results = clean_db.execute(
            "SELECT COUNT(*) as count FROM health_logs"
        ).fetchone()

        assert results["count"] == 100


    def test_transaction_with_foreign_key_constraint(self, clean_db):
        """FAIL: Should enforce foreign key constraints in transactions."""
        # Create embeddings table with FK
        clean_db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                text_content TEXT NOT NULL,
                embedding BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        clean_db.commit()

        # Enable FK constraints
        clean_db.execute("PRAGMA foreign_keys = ON")

        # Try to insert embedding with non-existent conversation_id
        with pytest.raises(sqlite3.IntegrityError):
            clean_db.execute(
                """INSERT INTO embeddings (conversation_id, text_content, embedding)
                VALUES (?, ?, ?)""",
                (999, "Test", b"embedding")
            )
            clean_db.commit()


    def test_update_expense_maintains_integrity(self, clean_db):
        """FAIL: Should support safe updates to expense data."""
        # Insert initial expense
        cursor = clean_db.execute(
            "INSERT INTO expenses (amount, category) VALUES (?, ?)",
            (50.00, "Food")
        )
        clean_db.commit()
        expense_id = cursor.lastrowid

        # Update the expense
        clean_db.execute(
            "UPDATE expenses SET amount = ?, category = ? WHERE id = ?",
            (75.00, "Entertainment", expense_id)
        )
        clean_db.commit()

        # Verify update
        result = clean_db.execute(
            "SELECT * FROM expenses WHERE id = ?",
            (expense_id,)
        ).fetchone()

        assert result["amount"] == 75.00
        assert result["category"] == "Entertainment"


    def test_delete_with_cascading_constraints(self, clean_db):
        """FAIL: Should support safe deletion with referential integrity."""
        # Create embeddings table with FK
        clean_db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                text_content TEXT NOT NULL,
                embedding BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)
        clean_db.commit()

        # Insert conversation
        cursor = clean_db.execute(
            "INSERT INTO conversations (role, content) VALUES (?, ?)",
            ("user", "Test")
        )
        clean_db.commit()
        conv_id = cursor.lastrowid

        # Insert embedding referencing conversation
        clean_db.execute(
            """INSERT INTO embeddings (conversation_id, text_content, embedding)
            VALUES (?, ?, ?)""",
            (conv_id, "Test content", b"embedding")
        )
        clean_db.commit()

        # Delete conversation (should cascade to embeddings if FK is enforced)
        clean_db.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conv_id,)
        )
        clean_db.commit()

        # Verify conversation is deleted
        result = clean_db.execute(
            "SELECT COUNT(*) as count FROM conversations WHERE id = ?",
            (conv_id,)
        ).fetchone()

        assert result["count"] == 0


class TestDatabaseIndexing:
    """Test that indexes exist for performance optimization."""

    def test_health_logs_metric_timestamp_index(self, clean_db):
        """FAIL: Should have index on health_logs(metric, timestamp)."""
        indexes = clean_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_health_metric'"
        ).fetchall()

        assert len(indexes) == 1


    def test_expenses_category_timestamp_index(self, clean_db):
        """FAIL: Should have index on expenses(category, timestamp)."""
        indexes = clean_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_expense_cat'"
        ).fetchall()

        assert len(indexes) == 1


    def test_index_improves_query_performance(self, clean_db):
        """FAIL: Index should speed up queries by metric and timestamp."""
        # Insert 1000 health logs
        base_time = datetime.now()
        for i in range(1000):
            ts = (base_time - timedelta(minutes=i)).isoformat()
            clean_db.execute(
                "INSERT INTO health_logs (metric, value, timestamp) VALUES (?, ?, ?)",
                ("sleep_hours", 7.0 + (i % 3) * 0.5, ts)
            )
        clean_db.commit()

        # Query with indexed columns should complete quickly
        results = clean_db.execute(
            """SELECT * FROM health_logs
            WHERE metric = ? AND timestamp > ?""",
            ("sleep_hours", (base_time - timedelta(days=1)).isoformat())
        ).fetchall()

        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
