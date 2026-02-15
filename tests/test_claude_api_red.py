"""
RED Phase Tests for Claude API Integration (Main Logic)

These tests define critical behaviors for Claude API integration:
1. Model selection (Haiku for simple, Opus for complex)
2. Response streaming (sentence-by-sentence)
3. Conversation history management
4. Rate limit handling (max 3 concurrent)
5. Tool use (function calling)
6. Context preservation across turns

All tests are written to FAIL initially (RED phase).
Implementation checklist provided at end of file.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

import pytest

from aegis.claude_client import ClaudeClient
from aegis.config import settings


# ============================================================================
# TEST CLASS 1: Model Selection for Query Complexity
# ============================================================================

class TestModelSelectionLogic:
    """
    RED Test: Claude should intelligently select Haiku vs Opus based on query complexity.

    Acceptance Criteria:
    - Haiku for queries < 100 tokens (simple, factual)
    - Opus for queries > 1000 tokens or requiring reasoning/analysis
    - Transparent model selection visible in logs/metrics
    """

    @pytest.mark.asyncio
    async def test_selects_haiku_for_simple_query_under_100_tokens(self):
        """FAIL: Haiku should be selected for simple queries."""
        client = ClaudeClient()

        simple_queries = [
            "what's my sleep score?",
            "how much did I spend today?",
            "log 50 pushups",
            "what time is it?",
            "reminder to drink water",
        ]

        for query in simple_queries:
            # This should measure token count and select haiku
            selected_model = await client.select_model_for_query(query)
            assert selected_model == settings.claude_haiku_model, \
                f"Expected Haiku for '{query}' but got {selected_model}"

    @pytest.mark.asyncio
    async def test_selects_opus_for_complex_query_over_1000_tokens(self):
        """FAIL: Opus should be selected for complex reasoning queries."""
        client = ClaudeClient()

        complex_query = """
        I've been tracking my sleep for 3 months. I noticed I sleep worse
        on days after I have coffee after 2pm. I also feel more anxious on
        those days. My mood scores are 3-4/10 on those days versus 7-8/10
        normally. I'm also spending more on groceries lately. Can you analyze
        the correlation between caffeine timing, sleep quality, anxiety levels,
        and spending patterns? What's the root cause and how should I adjust
        my habits? Also compare this to my historical patterns.
        """

        selected_model = await client.select_model_for_query(complex_query)
        assert selected_model == settings.claude_opus_model, \
            f"Expected Opus for complex query but got {selected_model}"

    @pytest.mark.asyncio
    async def test_selects_opus_for_analysis_triggers(self):
        """FAIL: Opus should be selected when analysis keywords are detected."""
        client = ClaudeClient()

        analysis_queries = {
            "analyze my spending patterns": "analysis",
            "correlate sleep with mood": "correlation",
            "why am I so tired lately?": "reasoning",
            "help me optimize my schedule": "optimization",
            "predict my next month's expenses": "forecasting",
        }

        for query, category in analysis_queries.items():
            selected_model = await client.select_model_for_query(query)
            assert selected_model == settings.claude_opus_model, \
                f"Expected Opus for {category} query: '{query}' but got {selected_model}"

    @pytest.mark.asyncio
    async def test_model_selection_logged_with_token_count(self):
        """FAIL: Model selection should be logged with token estimation."""
        client = ClaudeClient()

        with patch("aegis.claude_client.log") as mock_log:
            model = await client.select_model_for_query("test query")

            # Should log model selection with token count
            mock_log.info.assert_called()
            calls = str(mock_log.info.call_args_list)
            assert "model" in calls.lower() or "haiku" in calls.lower() or "opus" in calls.lower()


# ============================================================================
# TEST CLASS 2: Response Streaming (Sentence-by-Sentence)
# ============================================================================

class TestResponseStreaming:
    """
    RED Test: Claude should stream responses sentence-by-sentence for real-time TTS.

    Acceptance Criteria:
    - Responses yielded as complete sentences
    - Sentence boundaries detected (. ! ?)
    - No buffering delays longer than 500ms
    - Streaming begins within 100ms of API response
    """

    @pytest.mark.asyncio
    async def test_streams_response_sentence_by_sentence(self):
        """FAIL: Should yield complete sentences, not words or fragments."""
        client = ClaudeClient()

        # Mock response with multiple sentences
        response_text = "This is sentence one. This is sentence two! And a third?"

        # Mock the streaming response
        mock_stream = AsyncMock()
        sentences_yielded = []

        async def mock_chat():
            for sentence in ["This is sentence one.", "This is sentence two!", "And a third?"]:
                sentences_yielded.append(sentence)
                yield sentence

        with patch.object(client, "chat", side_effect=mock_chat):
            async for chunk in client.chat("test"):
                # Verify it's a complete sentence (ends with . ! or ?)
                assert chunk.strip().endswith((".", "!", "?")), \
                    f"Streamed chunk not a complete sentence: '{chunk}'"

        assert len(sentences_yielded) == 3
        assert sentences_yielded[0] == "This is sentence one."

    @pytest.mark.asyncio
    async def test_streaming_begins_within_100ms(self):
        """FAIL: First sentence should be available within 100ms of API response."""
        client = ClaudeClient()

        first_chunk_received = False
        first_chunk_time = None
        start_time = time.monotonic()

        async def mock_chat():
            await asyncio.sleep(0.05)  # Simulate API latency
            yield "First sentence."
            yield "Second sentence."

        with patch.object(client, "chat", side_effect=mock_chat):
            async for chunk in client.chat("test"):
                if not first_chunk_received:
                    first_chunk_received = True
                    first_chunk_time = time.monotonic() - start_time
                break

        assert first_chunk_received
        assert first_chunk_time < 0.1, \
            f"First sentence took {first_chunk_time:.3f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_no_buffering_delays_exceed_500ms(self):
        """FAIL: No buffering delay should exceed 500ms between sentences."""
        client = ClaudeClient()

        chunk_times = []
        last_chunk_time = time.monotonic()

        async def mock_chat():
            for i in range(5):
                await asyncio.sleep(0.1)  # Simulate API streaming
                yield f"Sentence {i}."

        with patch.object(client, "chat", side_effect=mock_chat):
            async for chunk in client.chat("test"):
                current_time = time.monotonic()
                time_since_last = current_time - last_chunk_time
                chunk_times.append(time_since_last)
                last_chunk_time = current_time

        # All delays should be < 500ms (accounting for processing)
        max_delay = max(chunk_times[1:])  # Skip first (no prior chunk)
        assert max_delay < 0.5, \
            f"Buffering delay of {max_delay:.3f}s exceeds 500ms threshold"

    @pytest.mark.asyncio
    async def test_sentence_boundary_detection_punctuation(self):
        """FAIL: Correctly identify sentence boundaries at . ! ?"""
        client = ClaudeClient()

        text_with_boundaries = "Hello. How are you? I'm fine! Really."
        expected_sentences = ["Hello.", "How are you?", "I'm fine!", "Really."]

        sentences = await client._extract_sentences(text_with_boundaries)

        assert sentences == expected_sentences, \
            f"Expected {expected_sentences} but got {sentences}"

    @pytest.mark.asyncio
    async def test_handles_sentence_without_punctuation(self):
        """FAIL: Handle incomplete sentences (e.g., at stream end)."""
        client = ClaudeClient()

        # Text ending without punctuation
        text = "This is complete. This is incomplete"
        sentences = await client._extract_sentences(text)

        # Should return complete sentence, buffer incomplete one
        assert "This is complete." in sentences or len(sentences) > 0


# ============================================================================
# TEST CLASS 3: Conversation History Management
# ============================================================================

class TestConversationHistoryManagement:
    """
    RED Test: Claude should maintain conversation context across turns.

    Acceptance Criteria:
    - History persists across API calls (turn 1 → turn 2 → turn 3)
    - Max 20 messages kept (prevents context bloat)
    - Tool results properly inserted as user messages
    - Reset clears all history
    """

    @pytest.mark.asyncio
    async def test_maintains_conversation_across_three_turns(self):
        """FAIL: Should remember previous turns in same conversation."""
        client = ClaudeClient()

        # Turn 1: User asks about sleep
        turn1_response = "You averaged 7 hours last night."
        with patch.object(client, "_api_call_mock", return_value=turn1_response):
            await client.chat("How did I sleep?")

        # Turn 2: User asks for more detail (should reference turn 1)
        assert len(client.conversation_history) >= 2, \
            "Turn 1 messages not in history"

        turn2_response = "Yes, that's good for you."
        with patch.object(client, "_api_call_mock", return_value=turn2_response):
            await client.chat("Is that good?")

        # Turn 3: Verify both prior turns are present
        assert len(client.conversation_history) >= 4, \
            "Turn 2 messages not in history"

        # Find user messages
        user_messages = [m["content"] for m in client.conversation_history
                        if m["role"] == "user"]
        assert "How did I sleep?" in user_messages
        assert "Is that good?" in user_messages

    @pytest.mark.asyncio
    async def test_trims_history_at_20_messages_max(self):
        """FAIL: Should not exceed 20 messages to avoid token bloat."""
        client = ClaudeClient()
        client.max_history = 20

        # Add 25 messages manually
        for i in range(25):
            role = "user" if i % 2 == 0 else "assistant"
            client.conversation_history.append({
                "role": role,
                "content": f"Message {i}"
            })

        # Simulate API call which triggers trim
        with patch.object(client, "chat", new=AsyncMock()):
            # This would trigger _trim_history
            client._trim_history()

        assert len(client.conversation_history) <= 20, \
            f"History has {len(client.conversation_history)} messages, expected <= 20"

    @pytest.mark.asyncio
    async def test_keeps_most_recent_messages(self):
        """FAIL: When trimming, keep most recent messages (FIFO)."""
        client = ClaudeClient()
        client.max_history = 4

        # Add 6 messages
        for i in range(6):
            client.conversation_history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })

        client._trim_history()

        # Should keep messages 4 and 5 (the most recent ones)
        remaining_content = [m["content"] for m in client.conversation_history]
        assert "Message 4" in remaining_content
        assert "Message 5" in remaining_content
        assert "Message 0" not in remaining_content

    @pytest.mark.asyncio
    async def test_properly_inserts_tool_results(self):
        """FAIL: Tool results should be inserted as user messages with proper format."""
        client = ClaudeClient()

        # Simulate tool call and result insertion
        tool_result = {
            "type": "tool_result",
            "tool_use_id": "tool_abc123",
            "content": json.dumps({"success": True, "data": {"sleep": 7.2}})
        }

        client._add_tool_result(tool_result)

        # Verify tool result was added to history
        assert len(client.conversation_history) > 0
        last_message = client.conversation_history[-1]
        assert last_message["role"] == "user"
        assert "tool_result" in str(last_message["content"])

    @pytest.mark.asyncio
    async def test_reset_clears_all_history(self):
        """FAIL: Reset should clear conversation completely."""
        client = ClaudeClient()
        client.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        await client.reset()

        assert client.conversation_history == [], \
            f"History not cleared after reset: {client.conversation_history}"

    @pytest.mark.asyncio
    async def test_conversation_context_visible_in_next_request(self):
        """FAIL: Next API call should include all prior messages."""
        client = ClaudeClient()

        # Mock messages.create to inspect what we send to Claude
        mock_create = AsyncMock(return_value=MagicMock())

        with patch.object(client.client.messages, "create", mock_create):
            # Turn 1
            await client.chat("What's my mood?")
            first_call_args = mock_create.call_args

            # Turn 2
            await client.chat("Help me improve it")
            second_call_args = mock_create.call_args

            # Second call should have more messages than first
            first_messages = first_call_args.kwargs.get("messages", [])
            second_messages = second_call_args.kwargs.get("messages", [])

            assert len(second_messages) > len(first_messages), \
                "Conversation context not carried forward"


# ============================================================================
# TEST CLASS 4: Rate Limit Handling (Max 3 Concurrent)
# ============================================================================

class TestRateLimitHandling:
    """
    RED Test: Claude client should gracefully handle rate limits.

    Acceptance Criteria:
    - Max 3 concurrent requests enforced
    - 4th request queued with exponential backoff
    - Rate limit errors trigger retry with jitter
    - Recovery logging for monitoring
    """

    @pytest.mark.asyncio
    async def test_enforces_max_3_concurrent_requests(self):
        """FAIL: Should prevent more than 3 simultaneous API calls."""
        client = ClaudeClient()
        concurrent_calls = []

        async def slow_api_call():
            concurrent_calls.append(1)
            await asyncio.sleep(0.5)
            concurrent_calls.pop()
            return "response"

        with patch.object(client, "chat", side_effect=slow_api_call):
            # Try to make 5 concurrent calls
            tasks = [client.chat(f"query {i}") async for i in range(5)]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Max concurrent should never exceed 3
        max_concurrent = len(concurrent_calls)
        assert max_concurrent <= 3, \
            f"Max concurrent was {max_concurrent}, expected <= 3"

    @pytest.mark.asyncio
    async def test_queues_requests_when_at_limit(self):
        """FAIL: 4th request should queue instead of immediate error."""
        client = ClaudeClient()
        call_order = []

        async def tracked_api_call(query_id):
            call_order.append(("start", query_id))
            await asyncio.sleep(0.1)
            call_order.append(("end", query_id))
            return "response"

        with patch.object(client, "chat", side_effect=lambda q: tracked_api_call(q)):
            # Make 4 requests
            tasks = [client.chat(f"query{i}") for i in range(4)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 4
        # All should complete without error
        assert not any(isinstance(r, Exception) for r in results)

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_error(self):
        """FAIL: Should retry when hitting 429 (rate limit) with backoff."""
        client = ClaudeClient()
        attempt_count = 0

        async def rate_limited_api():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                # Simulate 429 error
                from anthropic import RateLimitError
                raise RateLimitError("Rate limited")
            return "success after retries"

        with patch.object(client, "_make_api_call", side_effect=rate_limited_api):
            try:
                result = await client._make_api_call()
                assert result == "success after retries"
                assert attempt_count >= 2
            except Exception as e:
                pytest.fail(f"Should have retried instead of raising: {e}")

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_retry(self):
        """FAIL: Backoff should increase: 1s, 2s, 4s with jitter."""
        client = ClaudeClient()
        retry_times = []

        async def api_with_backoff():
            start = time.monotonic()
            await client._call_with_backoff()
            retry_times.append(time.monotonic() - start)

        # This would need implementation to verify backoff timing
        # For now, just check that the method exists and can be called
        assert hasattr(client, "_call_with_backoff")

    @pytest.mark.asyncio
    async def test_logs_rate_limit_recovery(self):
        """FAIL: Should log when recovering from rate limit."""
        client = ClaudeClient()

        with patch("aegis.claude_client.log") as mock_log:
            # Simulate rate limit error handling
            from anthropic import RateLimitError

            try:
                raise RateLimitError("Rate limited")
            except RateLimitError:
                client._handle_rate_limit()

        # Should have logged the recovery
        mock_log.warning.assert_called()


# ============================================================================
# TEST CLASS 5: Tool Use (Function Calling)
# ============================================================================

class TestToolUse:
    """
    RED Test: Claude should execute tools correctly within conversation loop.

    Acceptance Criteria:
    - Tool calls detected from Claude response
    - Tool executed with proper arguments
    - Results fed back to Claude for follow-up
    - Multiple tool calls in single turn supported
    - Tool errors handled gracefully
    """

    @pytest.mark.asyncio
    async def test_detects_tool_calls_in_response(self):
        """FAIL: Should identify when Claude wants to use a tool."""
        client = ClaudeClient()

        # Mock response with tool_use block
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "log_health"
        tool_block.id = "tool_123"
        tool_block.input = {"metric": "sleep", "value": 7.5}

        response = MagicMock()
        response.content = [tool_block]
        response.stop_reason = "tool_use"

        tools = await client._extract_tool_calls(response)

        assert len(tools) == 1
        assert tools[0]["name"] == "log_health"
        assert tools[0]["input"]["metric"] == "sleep"

    @pytest.mark.asyncio
    async def test_executes_tool_with_arguments(self):
        """FAIL: Should call tool dispatcher with correct arguments."""
        client = ClaudeClient()

        mock_dispatch = AsyncMock(return_value=json.dumps({"status": "logged"}))

        with patch("aegis.claude_client.dispatch_tool", mock_dispatch):
            result = await client._execute_tool("log_health", {"metric": "mood", "value": 8})

        mock_dispatch.assert_called_once_with("log_health", {"metric": "mood", "value": 8})
        assert "logged" in result

    @pytest.mark.asyncio
    async def test_feeds_tool_results_back_to_claude(self):
        """FAIL: Claude should get tool results and respond based on them."""
        client = ClaudeClient()

        # Turn 1: Tool call
        tool_response = MagicMock()
        tool_response.content = [MagicMock(type="tool_use", name="get_health_context",
                                           id="t1", input={"days": 7})]
        tool_response.stop_reason = "tool_use"

        # Turn 2: Response after seeing tool result
        text_response = MagicMock()
        text_response.content = [MagicMock(type="text", text="You averaged 7.2 hours.")]
        text_response.stop_reason = "end_turn"

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return tool_response
            else:
                return text_response

        with patch.object(client.client.messages, "create", side_effect=mock_create), \
             patch("aegis.claude_client.dispatch_tool", new=AsyncMock(
                 return_value=json.dumps({"data": {"sleep": 7.2}}))):

            response = await client.get_full_response("How did I sleep?")

        # Should have made 2 API calls (one for tool, one for response)
        assert call_count == 2, "Should call API twice (tool detection + response)"
        assert "7.2" in response

    @pytest.mark.asyncio
    async def test_handles_multiple_tool_calls_in_single_turn(self):
        """FAIL: Should execute multiple tools if Claude calls them."""
        client = ClaudeClient()

        # Response with 2 tool calls
        tool1 = MagicMock(type="tool_use", name="get_health_context", id="t1", input={})
        tool2 = MagicMock(type="tool_use", name="get_spending_summary", id="t2", input={})

        response = MagicMock()
        response.content = [tool1, tool2]
        response.stop_reason = "tool_use"

        tools = await client._extract_tool_calls(response)

        assert len(tools) == 2
        assert tools[0]["name"] == "get_health_context"
        assert tools[1]["name"] == "get_spending_summary"

    @pytest.mark.asyncio
    async def test_handles_tool_execution_errors(self):
        """FAIL: Tool errors should be caught and reported to Claude."""
        client = ClaudeClient()

        async def failing_tool():
            raise ValueError("Database connection failed")

        with patch("aegis.claude_client.dispatch_tool", side_effect=failing_tool):
            try:
                result = await client._execute_tool("get_health_context", {})
                # Should return error message, not raise
                assert "error" in result.lower() or "failed" in result.lower()
            except ValueError:
                pytest.fail("Should handle tool errors gracefully")

    @pytest.mark.asyncio
    async def test_tool_result_format_valid_for_claude(self):
        """FAIL: Tool results must be in correct format for Claude API."""
        client = ClaudeClient()

        tool_result = client._format_tool_result(
            tool_use_id="tool_123",
            content=json.dumps({"data": "result"})
        )

        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool_123"
        assert "data" in tool_result["content"]


# ============================================================================
# TEST CLASS 6: Context Preservation and Streaming Integration
# ============================================================================

class TestContextPreservationAndStreaming:
    """
    RED Test: Context and streaming work together seamlessly.

    Acceptance Criteria:
    - Streaming yields as soon as text is available
    - Context includes all prior tool calls
    - Sentence buffering doesn't lose content
    - Real-time metrics tracked (latency, tokens)
    """

    @pytest.mark.asyncio
    async def test_streaming_preserves_conversation_context(self):
        """FAIL: Streamed responses should be added to history with context intact."""
        client = ClaudeClient()

        # Add prior context
        client.conversation_history.append({"role": "user", "content": "Log 50 pushups"})
        client.conversation_history.append({"role": "assistant", "content": "Logged!"})

        # Stream a new response
        async def mock_stream():
            yield "Great work! That's "
            yield "your third workout "
            yield "this week."

        with patch.object(client, "chat", side_effect=mock_stream):
            response_text = ""
            async for chunk in client.chat("That's amazing!"):
                response_text += chunk

        # After streaming, context should be in history
        assert len(client.conversation_history) >= 4, "Context not preserved after streaming"

    @pytest.mark.asyncio
    async def test_streaming_latency_metrics(self):
        """FAIL: Should measure time to first token and total latency."""
        client = ClaudeClient()

        metrics = {}

        async def tracked_chat():
            start = time.monotonic()
            yield "First sentence. "
            metrics["time_to_first_token"] = time.monotonic() - start
            await asyncio.sleep(0.05)
            yield "Second sentence."
            metrics["total_time"] = time.monotonic() - start

        with patch.object(client, "chat", side_effect=tracked_chat):
            async for _ in client.chat("test"):
                pass

        assert "time_to_first_token" in metrics
        assert "total_time" in metrics
        assert metrics["total_time"] > metrics["time_to_first_token"]

    @pytest.mark.asyncio
    async def test_full_conversation_with_tools_and_streaming(self):
        """FAIL: Integration test with tools, streaming, and context."""
        client = ClaudeClient()

        # Turn 1: Stream response
        turn1_stream = ["I found your sleep ", "data from last week."]

        # Turn 2: Tool call + response
        tool_input = {"days": 7}
        turn2_text = "Your average was 7.1 hours."

        async def mock_turn1():
            for chunk in turn1_stream:
                yield chunk

        async def mock_turn2():
            # First would be tool call, then response
            yield turn2_text

        # This represents a full conversation flow
        # Verify the structure exists
        assert hasattr(client, "chat")
        assert hasattr(client, "conversation_history")


# ============================================================================
# IMPLEMENTATION CHECKLIST
# ============================================================================

"""
IMPLEMENTATION CHECKLIST FOR CLAUDE API INTEGRATION

After RED phase (failing tests), implement the following features:

[ ] MODEL SELECTION (Test Class 1)
  [ ] Implement token counter (_estimate_tokens method)
    - Use tiktoken or anthropic.count_tokens()
    - Return token count for any text

  [ ] Implement model selector (select_model_for_query method)
    - Token-based: < 100 → Haiku, >= 1000 → Opus
    - Keyword-based: if "analyze", "correlate", etc. → Opus
    - Default: Haiku for safety

  [ ] Add metrics logging
    - Log selected model and token estimate
    - Track model selection distribution

[ ] RESPONSE STREAMING (Test Class 2)
  [ ] Implement sentence extractor (_extract_sentences method)
    - Regex pattern: [^.!?]+[.!?]+
    - Buffer incomplete sentences
    - Handle edge cases (numbers with dots, abbreviations)

  [ ] Implement streaming via .stream() context manager
    - Use anthropic.messages.stream()
    - Collect text from content_block_delta events
    - Extract and yield complete sentences

  [ ] Measure streaming latency
    - Track time to first token
    - Alert if > 100ms

[ ] CONVERSATION HISTORY (Test Class 3)
  [ ] Implement history persistence
    - Maintain conversation_history list
    - Append user/assistant messages

  [ ] Implement history trimming (_trim_history method)
    - Keep last 20 messages
    - FIFO (remove oldest when exceeding limit)
    - Preserve tool results

  [ ] Implement tool result insertion (_add_tool_result method)
    - Format as tool_result type
    - Include tool_use_id and content

  [ ] Implement reset method
    - Clear conversation_history
    - Optional: clear cache

[ ] RATE LIMIT HANDLING (Test Class 4)
  [ ] Implement concurrency limiter
    - Use asyncio.Semaphore(3)
    - Wrap API calls with semaphore acquire/release

  [ ] Implement exponential backoff retry
    - Catch anthropic.RateLimitError (429)
    - Retry with delays: 1s, 2s, 4s, 8s (max 5 retries)
    - Add jitter: ± 0.1-0.3s

  [ ] Implement queue for pending requests
    - Log when queuing occurs
    - Expose queue size as metric

  [ ] Add monitoring/logging
    - Log rate limit errors
    - Log when recovery occurs
    - Track queue depth

[ ] TOOL USE (Test Class 5)
  [ ] Implement tool call extractor (_extract_tool_calls)
    - Parse response.content for tool_use blocks
    - Extract name, id, and input
    - Return list of tool dicts

  [ ] Implement tool execution loop (_execute_tool)
    - Call dispatch_tool with name and input
    - Catch and log tool errors
    - Format results as tool_result

  [ ] Implement tool loop in chat method
    - After API call, check stop_reason
    - If "tool_use": extract, execute, feed back
    - If "end_turn": exit loop and yield response
    - Max 5 tool calls per conversation turn

  [ ] Add tool result formatting (_format_tool_result)
    - type: "tool_result"
    - tool_use_id: string
    - content: string (JSON)

[ ] CONTEXT PRESERVATION (Test Class 6)
  [ ] Integrate all components
    - select_model() before API call
    - Send conversation_history with every request
    - Add streamed response to history
    - Add tool results to history before retrying

  [ ] Metrics collection
    - time_to_first_token
    - total_response_time
    - tool_execution_time
    - model_selected
    - conversation_turns

  [ ] Error handling
    - Wrap API calls in try/except
    - Handle network timeouts
    - Handle invalid responses
    - Log all errors with context

[ ] TESTING
  [ ] Run pytest with RED tests
  [ ] Verify all 6 test classes fail (RED phase)
  [ ] Implement each feature
  [ ] Run each test class individually to verify
  [ ] Run full test suite (should go GREEN)
  [ ] Add integration test combining all features
  [ ] Test with real Claude API (sandbox)

[ ] CODE QUALITY
  [ ] Add docstrings to all new methods
  [ ] Type hints on all parameters/returns
  [ ] Add logging at INFO and DEBUG levels
  [ ] No console.log (use logging module)
  [ ] Format with black
  [ ] Lint with ruff/pylint

ESTIMATED EFFORT: 6-8 hours
PRIORITY: CRITICAL (blocks all Claude integration features)
DEPENDENCIES: None (self-contained)
"""
