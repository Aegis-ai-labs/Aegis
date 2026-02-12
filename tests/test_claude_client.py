"""Unit tests for Claude client (bridge/claude_client.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bridge.claude_client import ClaudeClient
from bridge.context import build_health_context


class TestClaudeClient:
    """Test the ClaudeClient class."""

    def test_init(self):
        """Test ClaudeClient initialization."""
        with patch("bridge.claude_client.settings"):
            client = ClaudeClient()
            assert client.conversation_history == []
            assert client.max_history == 20

    @pytest.mark.asyncio
    async def test_get_system_prompt_with_health_context(self):
        """Test get_system_prompt includes health context when available."""
        with patch("bridge.claude_client.settings"):
            client = ClaudeClient()
            with patch("bridge.claude_client.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value = mock_db
                with patch("bridge.claude_client.build_health_context") as mock_health:
                    mock_health.return_value = "User health: Sleep 6.5h, Steps 5000/day"
                    prompt = await client.get_system_prompt()
                    assert "User health:" in prompt
                    assert "Sleep 6.5h" in prompt

    @pytest.mark.asyncio
    async def test_get_system_prompt_without_health_context(self):
        """Test get_system_prompt returns base prompt when no health context."""
        with patch("bridge.claude_client.settings"):
            client = ClaudeClient()
            with patch("bridge.claude_client.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value = mock_db
                with patch("bridge.claude_client.build_health_context") as mock_health:
                    mock_health.return_value = ""
                    prompt = await client.get_system_prompt()
                    assert "AEGIS" in prompt
                    assert "Keep responses under 2 sentences" in prompt
