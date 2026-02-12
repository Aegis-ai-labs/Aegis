"""Test configuration and fixtures for AEGIS1."""

import os
import sys
import pytest

# Set test environment variables BEFORE any bridge imports
os.environ.setdefault("DB_PATH", ":memory:")  # Use in-memory DB for tests
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

# Ensure bridge package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
