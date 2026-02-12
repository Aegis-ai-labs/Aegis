"""Test Claude client — model routing, tool loop, conversation management."""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from bridge.claude_client import ClaudeClient, select_model, SYSTEM_PROMPT, OPUS_TRIGGERS
from bridge.tools.registry import TOOL_DEFINITIONS


# --- Model routing tests ---

def test_select_model_haiku_for_simple():
    assert "haiku" in select_model("hello there")
    assert "haiku" in select_model("how are you")
    assert "haiku" in select_model("I spent $45 on lunch")
    assert "haiku" in select_model("how did I sleep?")


def test_select_model_opus_for_complex():
    assert "opus" in select_model("analyze my sleep patterns")
    assert "opus" in select_model("what's the trend in my exercise?")
    assert "opus" in select_model("help me plan a savings goal")
    assert "opus" in select_model("why am I so tired?")
    assert "opus" in select_model("correlate sleep with mood")


def test_all_opus_triggers_work():
    for trigger in OPUS_TRIGGERS:
        model = select_model(f"test {trigger} query")
        assert "opus" in model, f"Trigger '{trigger}' did not route to Opus"


# --- System prompt tests ---

def test_system_prompt_has_key_elements():
    assert "Aegis" in SYSTEM_PROMPT
    assert "voice" in SYSTEM_PROMPT.lower()
    assert "tool" in SYSTEM_PROMPT.lower()
    assert "concise" in SYSTEM_PROMPT.lower()


# --- Tool definitions tests ---

def test_tool_definitions_count():
    assert len(TOOL_DEFINITIONS) == 6


def test_tool_definitions_have_required_fields():
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"


def test_tool_names():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    expected = {
        "get_health_context", "log_health", "analyze_health_patterns",
        "track_expense", "get_spending_summary", "calculate_savings_goal",
    }
    assert names == expected


# --- Claude client tests with mocked API ---

def _make_text_response(text):
    """Create a mock Claude response with text content."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def _make_tool_response(tool_name, tool_id, tool_input, text_before=""):
    """Create a mock Claude response with tool use."""
    blocks = []
    if text_before:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text_before
        blocks.append(text_block)

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = tool_input
    blocks.append(tool_block)

    response = MagicMock()
    response.content = blocks
    response.stop_reason = "tool_use"
    return response


@pytest.mark.asyncio
async def test_client_simple_response():
    """Test simple text response without tool use."""
    client = ClaudeClient()

    mock_response = _make_text_response("Hello! I'm Aegis, your health and wealth assistant.")

    with patch.object(client.client.messages, "create", return_value=mock_response):
        result = await client.get_full_response("hello")

    assert "Aegis" in result
    assert len(client.conversation_history) == 2  # user + assistant


@pytest.mark.asyncio
async def test_client_tool_use_flow():
    """Test that tool calls are executed and results fed back to Claude."""
    client = ClaudeClient()

    # First call: Claude wants to use a tool
    tool_response = _make_tool_response(
        "get_health_context", "tool_123", {"days": 7}
    )
    # Second call: Claude responds with text after getting tool result
    text_response = _make_text_response("You averaged 6.8 hours of sleep this week.")

    mock_tool_result = json.dumps({"data": {"sleep_hours": {"avg": 6.8, "count": 7}}})

    with patch.object(
        client.client.messages, "create",
        side_effect=[tool_response, text_response]
    ), patch(
        "bridge.claude_client.execute_tool",
        new=AsyncMock(return_value=mock_tool_result)
    ) as mock_exec:
        result = await client.get_full_response("how did I sleep this week?")

    assert "6.8" in result
    mock_exec.assert_called_once_with("get_health_context", {"days": 7})
    assert len(client.conversation_history) == 2


@pytest.mark.asyncio
async def test_client_streaming_yields_chunks():
    """Test that get_response yields text chunks."""
    client = ClaudeClient()

    mock_response = _make_text_response("This is a streamed response.")

    with patch.object(client.client.messages, "create", return_value=mock_response):
        chunks = []
        async for chunk in client.get_response("test"):
            chunks.append(chunk)

    assert len(chunks) > 0
    assert "".join(chunks) == "This is a streamed response."


@pytest.mark.asyncio
async def test_client_conversation_history_management():
    """Test that conversation history is trimmed when too long."""
    client = ClaudeClient()

    # Fill history with 42 messages (> 40 threshold)
    client.conversation_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(42)
    ]

    mock_response = _make_text_response("response")
    with patch.object(client.client.messages, "create", return_value=mock_response):
        await client.get_full_response("new message")

    # Should be trimmed to last 20 + new user/assistant = some manageable size
    assert len(client.conversation_history) <= 22


@pytest.mark.asyncio
async def test_client_reset_conversation():
    """Test conversation reset."""
    client = ClaudeClient()
    client.conversation_history = [{"role": "user", "content": "test"}]
    client.reset_conversation()
    assert client.conversation_history == []
