"""Test configuration and fixtures."""

import os
import sys

# Set test env BEFORE any bridge imports
os.environ["DB_PATH"] = "test_aegis1.db"
os.environ["ANTHROPIC_API_KEY"] = "test-key"

# Ensure bridge package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
