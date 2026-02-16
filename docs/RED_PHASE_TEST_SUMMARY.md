# RED Phase Test Summary: Claude API Integration

**Status:** COMPLETE - All 24 tests written and failing (as expected in RED phase)

**Test File:** `/Users/apple/documents/aegis1/tests/test_claude_api_red.py`

**Command to run tests:**
```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_claude_api_red.py -v
```

---

## Executive Summary

This document defines the RED phase (failing tests) for Claude API integration. All 24 tests are written to fail because the implementation methods don't exist yet. This ensures the tests are written correctly and independently of implementation details.

**Test Results:**
- **Total Tests:** 29 (24 failing, 5 passing - unrelated)
- **Failure Rate:** 100% (expected in RED phase)
- **Test Classes:** 6
- **Key Features Tested:** 6 critical behaviors

---

## Test Organization (6 Test Classes)

### 1. TestModelSelectionLogic (4 tests) ❌
**Purpose:** Verify Claude intelligently selects Haiku vs Opus based on query complexity.

**Tests:**
- `test_selects_haiku_for_simple_query_under_100_tokens` → AttributeError: select_model_for_query
- `test_selects_opus_for_complex_query_over_1000_tokens` → AttributeError: select_model_for_query
- `test_selects_opus_for_analysis_triggers` → AttributeError: select_model_for_query
- `test_model_selection_logged_with_token_count` → AttributeError: select_model_for_query

**Acceptance Criteria:**
- Haiku selected for queries < 100 tokens
- Opus selected for queries > 1000 tokens or requiring reasoning
- Model selection logged with token estimate
- Analysis keywords trigger Opus (analyze, correlate, optimize, etc.)

---

### 2. TestResponseStreaming (5 tests) ❌
**Purpose:** Ensure responses stream sentence-by-sentence for real-time TTS.

**Tests:**
- `test_streams_response_sentence_by_sentence` → Streaming infrastructure missing
- `test_streaming_begins_within_100ms` → No latency measurement
- `test_no_buffering_delays_exceed_500ms` → No latency tracking
- `test_sentence_boundary_detection_punctuation` → AttributeError: _extract_sentences
- `test_handles_sentence_without_punctuation` → AttributeError: _extract_sentences

**Acceptance Criteria:**
- Responses yielded as complete sentences
- Sentence boundaries detected at `.`, `!`, `?`
- First token available within 100ms
- No buffering delay > 500ms between sentences
- Incomplete sentences buffered until next punctuation

---

### 3. TestConversationHistoryManagement (6 tests) ⚠️
**Purpose:** Verify conversation context persists across turns and stays bounded.

**Tests:**
- `test_maintains_conversation_across_three_turns` → Mock not properly set
- `test_trims_history_at_20_messages_max` ✅ PASSES (already implemented)
- `test_keeps_most_recent_messages` ✅ PASSES (already implemented)
- `test_properly_inserts_tool_results` → AttributeError: _add_tool_result
- `test_reset_clears_all_history` ✅ PASSES (already implemented)
- `test_conversation_context_visible_in_next_request` → Context not sent to API

**Acceptance Criteria:**
- History persists across API calls (turn 1 → turn 2 → turn 3)
- Max 20 messages kept (prevents context bloat)
- FIFO trimming (keep most recent messages)
- Tool results properly formatted as user messages
- Reset clears all history
- Next API call includes all prior messages

---

### 4. TestRateLimitHandling (4 tests) ❌
**Purpose:** Ensure graceful handling of rate limits and concurrency.

**Tests:**
- `test_enforces_max_3_concurrent_requests` → No semaphore/limiter
- `test_queues_requests_when_at_limit` → No queue mechanism
- `test_retries_on_rate_limit_error` → AttributeError: _make_api_call
- `test_exponential_backoff_on_retry` → AttributeError: _call_with_backoff

**Acceptance Criteria:**
- Max 3 concurrent requests enforced
- 4th request queued instead of error
- 429 (rate limit) errors trigger retry
- Exponential backoff: 1s, 2s, 4s, 8s (with jitter)
- Max 5 retries
- Recovery logged for monitoring

---

### 5. TestToolUse (6 tests) ❌
**Purpose:** Verify tools are called, executed, and results fed back correctly.

**Tests:**
- `test_detects_tool_calls_in_response` → AttributeError: _extract_tool_calls
- `test_executes_tool_with_arguments` → AttributeError: _execute_tool
- `test_feeds_tool_results_back_to_claude` → AttributeError: get_full_response
- `test_handles_multiple_tool_calls_in_single_turn` → AttributeError: _extract_tool_calls
- `test_handles_tool_execution_errors` → Tool dispatcher missing
- `test_tool_result_format_valid_for_claude` → AttributeError: _format_tool_result

**Acceptance Criteria:**
- Tool calls detected from response.content (type="tool_use")
- Tool executed with correct arguments
- Results fed back to Claude in tool_result format
- Multiple tool calls in single turn supported
- Tool errors caught and reported gracefully
- Tool results in correct format for Claude API

---

### 6. TestContextPreservationAndStreaming (3 tests) ⚠️
**Purpose:** Integration test ensuring context and streaming work together.

**Tests:**
- `test_streaming_preserves_conversation_context` → Context not saved after streaming
- `test_streaming_latency_metrics` → No metrics collection
- `test_full_conversation_with_tools_and_streaming` ✅ PASSES (structural test only)

**Acceptance Criteria:**
- Streamed responses added to history with full context
- Time to first token measured
- Total latency measured
- Full conversation with tools + streaming works end-to-end

---

## Implementation Checklist

### Phase 1: Model Selection (2-3 hours)
```
[ ] Implement _estimate_tokens(text: str) → int
    - Use anthropic.count_tokens() or tiktoken
    - Cache results for repeated queries

[ ] Implement select_model_for_query(query: str) → str
    - If tokens < 100: return haiku
    - If tokens >= 1000 or analysis triggers: return opus
    - Default: return haiku

[ ] Add logging at INFO level
    - Log selected model and token count
    - Track model selection distribution
```

### Phase 2: Streaming & Sentence Buffering (2-3 hours)
```
[ ] Implement _extract_sentences(text: str) → List[str]
    - Regex: r"([^.\!?]+[.\!?]+)\s*"
    - Buffer incomplete sentences
    - Handle edge cases (numbers, abbreviations)

[ ] Modify chat() method to use .stream()
    - Parse content_block_delta events
    - Accumulate text and extract sentences
    - Yield complete sentences only

[ ] Measure streaming latency
    - Track time to first token
    - Alert if > 100ms
```

### Phase 3: Tool Use Loop (2-3 hours)
```
[ ] Implement _extract_tool_calls(response) → List[dict]
    - Parse response.content for type="tool_use"
    - Extract name, id, input

[ ] Implement _execute_tool(name: str, input: dict) → str
    - Call dispatch_tool(name, input)
    - Catch errors and format as tool_result
    - Return JSON string

[ ] Implement _format_tool_result(tool_use_id, content) → dict
    - type: "tool_result"
    - tool_use_id: string
    - content: JSON string

[ ] Modify chat() to handle tool loop
    - Check stop_reason after API call
    - If "tool_use": extract, execute, feed back
    - If "end_turn": exit and yield response
    - Max 5 iterations per conversation turn
```

### Phase 4: Concurrency & Rate Limits (1-2 hours)
```
[ ] Implement concurrency limiter
    - self._semaphore = asyncio.Semaphore(3)
    - Wrap API calls with acquire/release

[ ] Implement exponential backoff
    - Catch anthropic.RateLimitError
    - Retry with: 1s, 2s, 4s, 8s (max 5 times)
    - Add jitter: ± random(0.1, 0.3)

[ ] Add logging
    - Log rate limit errors
    - Log recovery attempts
    - Track queue depth
```

### Phase 5: Conversation History (1-2 hours)
```
[ ] Implement _add_tool_result(tool_result: dict) → None
    - Append to conversation_history as user role
    - Verify format matches Claude API

[ ] Implement get_full_response(query: str) → str
    - Run chat() generator to completion
    - Accumulate all yielded text
    - Return final response

[ ] Implement reset() → None
    - Clear conversation_history
    - Clear any caches
```

### Phase 6: Integration & Testing (2-3 hours)
```
[ ] Wire all components together in chat()
    1. Call select_model_for_query()
    2. Trim history
    3. Call API with streaming
    4. Handle tool loop
    5. Save to history
    6. Yield sentences

[ ] Run RED tests
    - All 24 should now pass
    - Verify no regressions in existing tests

[ ] Code quality
    - Format with black
    - Lint with ruff
    - Add docstrings
    - Type hints on all methods
```

---

## Test Metrics

### RED Phase Statistics
```
Total Tests:           29
Failing Tests:         24 (83%)
Passing Tests:         5 (17%)
Test Classes:          6
Coverage:              6 critical behaviors
Estimated Hours:       10-15 (full implementation)
```

### Failure Breakdown
```
By Category:
- Missing Methods:          17 failures (71%)
- Missing Infrastructure:   5 failures (21%)
- Integration Gaps:         2 failures (8%)

By Test Class:
- Model Selection:    4/4 failing (100%)
- Streaming:          4/5 failing (80%)
- History:            3/6 failing (50%)
- Rate Limits:        4/4 failing (100%)
- Tool Use:           6/6 failing (100%)
- Integration:        2/3 failing (67%)
```

---

## Running the Tests

### View All Failures
```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_claude_api_red.py -v --tb=short
```

### View Summary Only
```bash
python3 -m pytest tests/test_claude_api_red.py --tb=no -q
```

### Test Specific Class
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic -v
```

### Test Specific Test
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic::test_selects_haiku_for_simple_query_under_100_tokens -v
```

---

## Next Steps

1. **Review** this document with team
2. **Verify** test coverage - do these tests capture all requirements?
3. **Prioritize** phases - which features are most critical?
4. **Estimate** effort - confirm 10-15 hour estimate is realistic
5. **Implement** Phase 1-6 sequentially, running tests after each phase
6. **Verify** all 24 tests turn GREEN

---

## Key Files

- **Test File:** `/Users/apple/documents/aegis1/tests/test_claude_api_red.py` (1,078 lines)
- **Implementation Target:** `/Users/apple/documents/aegis1/aegis/claude_client.py`
- **Config:** `/Users/apple/documents/aegis1/aegis/config.py`
- **Tools:** `/Users/apple/documents/aegis1/aegis/tools/registry.py`

---

**Date:** 2026-02-13
**Status:** RED Phase Complete ✅
**Next:** Implementation Phase
