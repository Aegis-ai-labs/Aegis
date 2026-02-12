"""Test configuration and fixtures for AEGIS1."""

import os
import sys
import pytest

# Set test environment variables BEFORE any bridge imports
os.environ.setdefault("DB_PATH", "test_aegis1.db")  # Use file-based DB for tests
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

# Ensure bridge package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Initialize test database before running any tests."""
    from aegis.db import init_db

    # Remove any existing test database
    test_db_path = "test_aegis1.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    init_db()  # Create tables in the test database
    yield

    # Cleanup: Remove test database after all tests complete
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
