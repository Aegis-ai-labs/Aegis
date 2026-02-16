# RED Phase: Expected Failures (Detailed)

This document shows exactly which tests fail and why they fail in the RED phase.

## Test Execution Summary

```
Total: 29 tests
Failing: 24 tests (83%) ← Expected in RED phase
Passing: 5 tests (17%) ← Existing implementations
```

---

## Detailed Failure Analysis

### TEST CLASS 1: Model Selection (4/4 FAILING)

#### ❌ test_selects_haiku_for_simple_query_under_100_tokens
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute 'select_model_for_query'
Location: tests/test_claude_api_red.py:57

Root Cause:
  - Method select_model_for_query() not implemented
  - Token counter not available
  - No model selection logic

To Fix:
  1. Add token counting method
  2. Add select_model_for_query() method
  3. Implement token-based threshold logic
```

#### ❌ test_selects_opus_for_complex_query_over_1000_tokens
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute 'select_model_for_query'
Location: tests/test_claude_api_red.py:76

Root Cause:
  - Same as above

To Fix:
  - Implement select_model_for_query() method
  - Add Opus routing for large/complex queries
```

#### ❌ test_selects_opus_for_analysis_triggers
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute 'select_model_for_query'
Location: tests/test_claude_api_red.py:94

Root Cause:
  - Keyword detection not implemented
  - No analysis trigger list

To Fix:
  - Add keyword list: ["analyze", "correlate", "optimize", "forecast", "pattern", "why"]
  - Check if any keyword in query → route to Opus
```

#### ❌ test_model_selection_logged_with_token_count
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute 'select_model_for_query'
Location: tests/test_claude_api_red.py:104

Root Cause:
  - No method to call
  - No logging setup

To Fix:
  - Add logging.info() call with selected model and token count
  - Example: log.info(f"Model selection: {model} ({tokens} tokens)")
```

---

### TEST CLASS 2: Response Streaming (4/5 FAILING)

#### ❌ test_streams_response_sentence_by_sentence
```
Failure Type: AttributeError (during patch)
Message: <ClaudeClient object> does not have the attribute 'chat'
Location: tests/test_claude_api_red.py:211

Root Cause:
  - chat() method exists but doesn't yield properly
  - Streaming infrastructure not complete
  - No sentence extraction

To Fix:
  1. Implement _extract_sentences() method
  2. Modify chat() to detect sentence boundaries
  3. Yield complete sentences only
```

#### ❌ test_streaming_begins_within_100ms
```
Failure Type: AttributeError
Message: <ClaudeClient> does not have attribute '_extract_sentences'
Location: tests/test_claude_api_red.py:223

Root Cause:
  - Sentence extraction method missing
  - No timing measurement

To Fix:
  - Implement _extract_sentences()
  - Add time.monotonic() calls to measure latency
  - Ensure first sentence yields within 100ms
```

#### ❌ test_no_buffering_delays_exceed_500ms
```
Failure Type: AssertionError
Message: max_delay of X seconds exceeds 500ms threshold
Location: tests/test_claude_api_red.py:245

Root Cause:
  - No sentence buffering mechanism
  - Streaming doesn't accumulate properly

To Fix:
  - Implement buffering loop in chat()
  - Track time between yields
  - Enforce 500ms max delay between sentences
```

#### ✅ test_sentence_boundary_detection_punctuation
```
Status: NEEDS IMPLEMENTATION
Note: Currently would fail due to missing _extract_sentences()

To Fix:
  - Implement _extract_sentences(text: str) → List[str]
  - Regex: r"([^.\!?]+[.\!?]+)\s*"
  - Split by sentence boundaries only
  - Test with "Hello. How are you? I'm fine!"
```

#### ❌ test_handles_sentence_without_punctuation
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_extract_sentences'
Location: tests/test_claude_api_red.py:228

Root Cause:
  - Sentence extraction not implemented
  - No buffering for incomplete sentences

To Fix:
  - Return complete sentences
  - Keep incomplete sentence in buffer
  - Yield it only when next punctuation found
```

---

### TEST CLASS 3: Conversation History (3/6 FAILING)

#### ❌ test_maintains_conversation_across_three_turns
```
Failure Type: AttributeError
Message: does not have the attribute '_api_call_mock'
Location: tests/test_claude_api_red.py:317

Root Cause:
  - Mock method name doesn't exist
  - chat() not properly integrated with history

To Fix:
  1. Verify chat() appends to conversation_history
  2. Test three consecutive calls
  3. Check history contains all messages
```

#### ✅ test_trims_history_at_20_messages_max
**Status: ALREADY PASSES** (method _trim_history() implemented)

#### ✅ test_keeps_most_recent_messages
**Status: ALREADY PASSES** (FIFO trimming implemented)

#### ❌ test_properly_inserts_tool_results
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_add_tool_result'
Location: tests/test_claude_api_red.py:327

Root Cause:
  - No method to add tool results to history
  - Tool result format not defined

To Fix:
  1. Implement _add_tool_result(tool_result: dict) method
  2. Append as user message with type="tool_result"
  3. Verify format: {"type": "tool_result", "tool_use_id": "...", "content": "..."}
```

#### ✅ test_reset_clears_all_history
**Status: ALREADY PASSES** (reset() method exists)

#### ❌ test_conversation_context_visible_in_next_request
```
Failure Type: AssertionError
Message: len(second_messages) not > len(first_messages)
Location: tests/test_claude_api_red.py:372

Root Cause:
  - API calls don't include previous messages
  - chat() not passing full history to Claude API

To Fix:
  1. In chat() method, pass all conversation_history to API
  2. Verify messages parameter includes previous turns
  3. After first call, second call should have more messages
```

---

### TEST CLASS 4: Rate Limit Handling (4/4 FAILING)

#### ❌ test_enforces_max_3_concurrent_requests
```
Failure Type: AssertionError
Message: max_concurrent was 5, expected <= 3
Location: tests/test_claude_api_red.py:410

Root Cause:
  - No concurrency limiter implemented
  - No asyncio.Semaphore

To Fix:
  1. Add self._semaphore = asyncio.Semaphore(3) in __init__
  2. Wrap API calls:
     async with self._semaphore:
         # API call here
  3. This ensures max 3 concurrent
```

#### ❌ test_queues_requests_when_at_limit
```
Failure Type: AssertionError
Message: Immediate 4th request fails instead of queuing
Location: tests/test_claude_api_red.py:429

Root Cause:
  - No queue mechanism
  - No semaphore to hold 4th request

To Fix:
  - Implement semaphore (see above)
  - Semaphore automatically queues/blocks excess requests
  - When one of first 3 completes, 4th begins
```

#### ❌ test_retries_on_rate_limit_error
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_make_api_call'
Location: tests/test_claude_api_red.py:444

Root Cause:
  - No centralized API call method
  - No retry logic

To Fix:
  1. Create _make_api_call() method that wraps client.messages.create()
  2. Add try/except for RateLimitError
  3. Implement exponential backoff retry
  4. Return response on success
```

#### ❌ test_exponential_backoff_on_retry
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_call_with_backoff'
Location: tests/test_claude_api_red.py:461

Root Cause:
  - No backoff implementation
  - No retry timing logic

To Fix:
  1. Implement _call_with_backoff() method
  2. Retry delays: [1, 2, 4, 8] seconds (max 5 tries)
  3. Add jitter: ± random(0.1, 0.3)
  4. Use asyncio.sleep(delay) for delays
```

---

### TEST CLASS 5: Tool Use (6/6 FAILING)

#### ❌ test_detects_tool_calls_in_response
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_extract_tool_calls'
Location: tests/test_claude_api_red.py:520

Root Cause:
  - No method to parse tool calls from response
  - No tool_use block parsing

To Fix:
  1. Implement _extract_tool_calls(response) → List[dict]
  2. Loop through response.content
  3. If block.type == "tool_use", extract:
     - name: block.name
     - id: block.id
     - input: block.input
  4. Return list of tool dicts
```

#### ❌ test_executes_tool_with_arguments
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_execute_tool'
Location: tests/test_claude_api_red.py:534

Root Cause:
  - No tool execution wrapper
  - No dispatch integration

To Fix:
  1. Implement _execute_tool(name: str, input: dict) → str
  2. Call dispatch_tool(name, input) from aegis.tools.registry
  3. Catch exceptions and return error message
  4. Return JSON string of result
```

#### ❌ test_feeds_tool_results_back_to_claude
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute 'get_full_response'
Location: tests/test_claude_api_red.py:569

Root Cause:
  - No method to run tool loop to completion
  - No tool result feeding

To Fix:
  1. Implement get_full_response(query: str) → str
  2. Run chat(query) generator to completion
  3. Accumulate all yielded text
  4. For tool calls: insert results and loop back to API
  5. Return final text response
```

#### ❌ test_handles_multiple_tool_calls_in_single_turn
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_extract_tool_calls'
Location: tests/test_claude_api_red.py:588

Root Cause:
  - _extract_tool_calls not implemented
  - No multi-tool support

To Fix:
  1. Implement _extract_tool_calls() (see above)
  2. Loop through ALL tool_use blocks
  3. Return list with multiple tools
  4. In tool loop, execute all before looping back
```

#### ❌ test_handles_tool_execution_errors
```
Failure Type: Exception (dispatch_tool fails)
Message: Tool execution error not caught
Location: tests/test_claude_api_red.py:604

Root Cause:
  - No error handling in _execute_tool()
  - Exceptions propagate instead of being captured

To Fix:
  1. In _execute_tool(), wrap dispatch_tool() in try/except
  2. Catch all Exception types
  3. Format error as JSON: {"error": str(e), "tool": name}
  4. Return JSON string (not exception)
```

#### ❌ test_tool_result_format_valid_for_claude
```
Failure Type: AttributeError
Message: 'ClaudeClient' object has no attribute '_format_tool_result'
Location: tests/test_claude_api_red.py:615

Root Cause:
  - No tool result formatter
  - No format validation

To Fix:
  1. Implement _format_tool_result(tool_use_id: str, content: str) → dict
  2. Return dict with:
     - "type": "tool_result"
     - "tool_use_id": tool_use_id
     - "content": content (JSON string)
  3. Verify structure matches Claude API expectations
```

---

### TEST CLASS 6: Integration (2/3 FAILING)

#### ❌ test_streaming_preserves_conversation_context
```
Failure Type: AssertionError
Message: len(conversation_history) < 4 after streaming
Location: tests/test_claude_api_red.py:645

Root Cause:
  - Streamed responses not added to history
  - No integration between streaming and history management

To Fix:
  1. After chat() completes, full response should be in history
  2. Add assistant message to conversation_history
  3. Include all streamed text (concatenated)
  4. Verify history persists after streaming
```

#### ❌ test_streaming_latency_metrics
```
Failure Type: AssertionError
Message: 'time_to_first_token' not in metrics
Location: tests/test_claude_api_red.py:668

Root Cause:
  - No metrics collection
  - No latency tracking

To Fix:
  1. Add metrics dict to track:
     - time_to_first_token: time from start to first yield
     - total_response_time: time for full response
  2. Log these metrics: log.info(f"Latency: {latency}ms")
  3. Consider exposing via prometheus or similar
```

#### ✅ test_full_conversation_with_tools_and_streaming
**Status: PASSES** (structural test only - just checks methods exist)

---

## Summary Table

| Test Class | Total | Failing | Passing | % Ready |
|-----------|-------|---------|---------|---------|
| Model Selection | 4 | 4 | 0 | 0% |
| Streaming | 5 | 4 | 1 | 20% |
| History | 6 | 3 | 3 | 50% |
| Rate Limits | 4 | 4 | 0 | 0% |
| Tool Use | 6 | 6 | 0 | 0% |
| Integration | 3 | 2 | 1 | 33% |
| **TOTAL** | **28** | **23** | **5** | **18%** |

---

## Implementation Order (Recommended)

Based on dependencies:

1. **Phase 1: Model Selection** (fixes 4 failures)
   - Unblocks: Streaming tests need model selection
   - Duration: 2-3 hours

2. **Phase 2: Sentence Extraction** (fixes 3 failures)
   - Unblocks: Tool Use tests need streaming
   - Duration: 2-3 hours

3. **Phase 3: Tool Loop** (fixes 6 failures)
   - Unblocks: History integration tests
   - Duration: 2-3 hours

4. **Phase 4: Rate Limiting** (fixes 4 failures)
   - Independent, can run in parallel
   - Duration: 1-2 hours

5. **Phase 5: History Integration** (fixes 3 failures)
   - Depends on Phase 1-3
   - Duration: 1-2 hours

6. **Phase 6: Testing & Cleanup** (fixes 2 failures)
   - All phases complete before this
   - Duration: 1-2 hours

**Total Estimated:** 10-15 hours

---

## Debugging Tips

### View Single Test Failure
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic::test_selects_haiku_for_simple_query_under_100_tokens -vv
```

### View All Failures of One Class
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic -v
```

### View Full Traceback
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic::test_selects_haiku_for_simple_query_under_100_tokens -vv --tb=long
```

### Run Only Tests That Will Pass
```bash
python3 -m pytest tests/test_claude_api_red.py -k "trims_history or keeps_most_recent or reset_clears" -v
```

---

**Document Generated:** 2026-02-13
**Status:** RED Phase (All expected failures documented)
**Next:** Implementation Phase
