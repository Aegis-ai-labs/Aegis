"""Test configuration and fixtures for AEGIS1 testing."""

import os
import sys
import pytest

# Add both bridge-dev and current worktree to path so imports work
bridge_dev_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "bridge-dev"
)
current_path = os.path.dirname(os.path.dirname(__file__))

for path in [bridge_dev_path, current_path]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# Set environment variables for testing
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
