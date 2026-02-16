# Implementation Quick Reference Guide

## Quick Links

- **Test File:** `/Users/apple/documents/aegis1/tests/test_claude_api_red.py`
- **Test Results:** 24 failing, 5 passing (RED phase)
- **Target File:** `/Users/apple/documents/aegis1/aegis/claude_client.py`
- **Summary:** `docs/RED_PHASE_TEST_SUMMARY.md`
- **Failures:** `docs/RED_PHASE_EXPECTED_FAILURES.md`

## Run Tests

```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_claude_api_red.py -v
```

---

## Implementation Checklist

Copy this into your implementation workflow:

### ✓ Phase 1: Model Selection (2-3 hours)
```python
# In ClaudeClient.__init__
self._token_cache = {}

# New methods to implement:
async def _estimate_tokens(self, text: str) -> int:
    """Estimate tokens in text using anthropic.count_tokens()"""
    # Implementation

async def select_model_for_query(self, query: str) -> str:
    """Select Haiku or Opus based on complexity"""
    # Implementation
    # < 100 tokens → Haiku
    # >= 1000 tokens OR analysis keywords → Opus
    # Default → Haiku
```

**Tests Fixed:** 4
**Methods Added:** 2
**Dependencies:** anthropic.count_tokens()

---

### ✓ Phase 2: Sentence Extraction (2-3 hours)
```python
# New method to implement:
async def _extract_sentences(self, text: str) -> List[str]:
    """Extract complete sentences from text"""
    # Regex: r"([^.\!?]+[.\!?]+)\s*"
    # Return list of complete sentences
    # Buffer incomplete sentences

# Modify existing chat() method:
async def chat(self, user_text: str) -> AsyncGenerator[str, None]:
    # ... existing code ...
    
    # Add sentence extraction:
    buffer = ""
    async for event in stream:
        if has_text(event):
            buffer += event.text
            while True:
                match = SENTENCE_RE.match(buffer)
                if not match:
                    break
                sentence = match.group(1).strip()
                if sentence:
                    yield sentence
                buffer = buffer[match.end():]
    
    # Yield remaining
    if buffer.strip():
        yield buffer.strip()
```

**Tests Fixed:** 3
**Methods Added:** 1
**Methods Modified:** 1

---

### ✓ Phase 3: Tool Loop (2-3 hours)
```python
# New methods to implement:
async def _extract_tool_calls(self, response) -> List[dict]:
    """Parse tool calls from Claude response"""
    # Loop response.content
    # If type="tool_use": extract name, id, input
    # Return list of dicts

async def _execute_tool(self, name: str, input_: dict) -> str:
    """Execute a tool and return result as JSON"""
    # Call dispatch_tool(name, input_)
    # Catch exceptions
    # Return JSON string

def _format_tool_result(self, tool_use_id: str, content: str) -> dict:
    """Format tool result for Claude API"""
    # Return:
    # {
    #     "type": "tool_result",
    #     "tool_use_id": tool_use_id,
    #     "content": content
    # }

async def get_full_response(self, query: str) -> str:
    """Run chat() to completion, handle tool loops"""
    # Accumulate all yields from chat()
    # If tool calls detected: execute and loop back
    # Return final text

# Modify chat() for tool loop:
# After API response:
# if stop_reason == "tool_use":
#     extract tools
#     execute each
#     add results to history
#     loop back to API
```

**Tests Fixed:** 6
**Methods Added:** 4
**Methods Modified:** 1

---

### ✓ Phase 4: Rate Limiting (1-2 hours)
```python
# In ClaudeClient.__init__:
self._semaphore = asyncio.Semaphore(3)

# New methods to implement:
async def _call_with_backoff(self):
    """Retry with exponential backoff"""
    # Retry delays: [1, 2, 4, 8] seconds
    # Add jitter: ± random(0.1, 0.3)
    # Max 5 retries
    # Catch RateLimitError and retry

async def _make_api_call(self, **kwargs):
    """Centralized API call with rate limit handling"""
    # async with self._semaphore:
    #     try: API call
    #     except RateLimitError: _call_with_backoff()

def _handle_rate_limit(self):
    """Log rate limit recovery"""
    # log.warning("Rate limit hit, retrying...")
```

**Tests Fixed:** 4
**Methods Added:** 3
**Concurrency:** Semaphore(3)

---

### ✓ Phase 5: History & Tool Results (1-2 hours)
```python
# New methods to implement:
def _add_tool_result(self, tool_result: dict) -> None:
    """Add tool result to conversation history"""
    # Append {"role": "user", "content": [tool_result]}

# Modify existing methods:
async def reset(self) -> None:
    """Clear conversation history"""
    # Already exists - just verify it works

# Verify chat() integration:
# After API response:
# - Add assistant message to history
# - Add tool results as user message
# - Pass full history in next API call
```

**Tests Fixed:** 3
**Methods Added:** 1
**Methods Modified:** 1

---

### ✓ Phase 6: Integration & Metrics (2-3 hours)
```python
# Add metrics collection:
self._metrics = {
    "time_to_first_token": None,
    "total_response_time": None,
    "tool_execution_time": None,
    "model_selected": None,
    "conversation_turns": 0
}

# In chat() method:
# - Track latency of first yield
# - Track total response time
# - Log metrics after response

# Verify full flow:
# 1. select_model_for_query()
# 2. trim_history()
# 3. Stream with sentence buffering
# 4. Handle tool loop
# 5. Add to history
# 6. Yield sentences
# 7. Collect metrics
```

**Tests Fixed:** 2
**Metrics Added:** 4

---

## Method Signature Reference

All methods to implement:

```python
class ClaudeClient:
    # Phase 1: Model Selection
    async def _estimate_tokens(self, text: str) -> int
    async def select_model_for_query(self, query: str) -> str
    
    # Phase 2: Streaming
    async def _extract_sentences(self, text: str) -> List[str]
    # Modify: chat() method
    
    # Phase 3: Tool Use
    async def _extract_tool_calls(self, response: Any) -> List[dict]
    async def _execute_tool(self, name: str, input_: dict) -> str
    def _format_tool_result(self, tool_use_id: str, content: str) -> dict
    async def get_full_response(self, query: str) -> str
    # Modify: chat() method
    
    # Phase 4: Rate Limiting
    async def _call_with_backoff(self) -> Any
    async def _make_api_call(self, **kwargs) -> Any
    def _handle_rate_limit(self) -> None
    
    # Phase 5: History
    def _add_tool_result(self, tool_result: dict) -> None
    # Modify: reset() method (already exists)
    # Modify: chat() method
    
    # Phase 6: Metrics
    # Add: self._metrics dict
    # Modify: chat() method
```

---

## Dependencies by Phase

| Phase | Dependencies | New External Packages |
|-------|-------------|---------------------|
| 1 | anthropic, config | None (already have anthropic) |
| 2 | asyncio, re, logging | None |
| 3 | tools.registry, json | None |
| 4 | asyncio, anthropic.RateLimitError | None |
| 5 | (none) | None |
| 6 | time, logging | None |

**No new external packages needed!** All dependencies already in project.

---

## Testing Workflow

### After Phase 1:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic -v
```
Expected: 4 PASSED ✅

### After Phase 2:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestResponseStreaming -v
```
Expected: 4-5 PASSED ✅ (1 may need minor adjustment)

### After Phase 3:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestToolUse -v
```
Expected: 6 PASSED ✅

### After Phase 4:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestRateLimitHandling -v
```
Expected: 4 PASSED ✅

### After Phase 5:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestConversationHistoryManagement -v
```
Expected: 6 PASSED ✅ (3 already passing)

### After Phase 6:
```bash
python3 -m pytest tests/test_claude_api_red.py::TestContextPreservationAndStreaming -v
```
Expected: 3 PASSED ✅

### Full Test Suite:
```bash
python3 -m pytest tests/test_claude_api_red.py -v
```
Expected: 24 PASSED ✅

---

## Common Pitfalls

1. **Forgetting to wire methods into chat()**
   - Build methods first ✓
   - Then integrate into chat() flow ✓
   - Test each integration ✓

2. **Not handling async properly**
   - All I/O operations must be async
   - Use `async with` for context managers
   - Use `await` for async calls

3. **Tool result format**
   - Must be dict with type, tool_use_id, content
   - Content should be JSON string
   - Wrap in list when adding to history

4. **Rate limit handling**
   - Catch `anthropic.RateLimitError` not `Exception`
   - Semaphore should wrap actual API call
   - Backoff includes jitter (not just fixed delays)

5. **Sentence buffering**
   - Test with multiple sentence types: . ! ?
   - Test with abbreviations (Dr. Ph.D.)
   - Test with numbers (3.14)

---

## Code Examples

### Example: Model Selection
```python
async def select_model_for_query(self, query: str) -> str:
    tokens = await self._estimate_tokens(query)
    log.info(f"Query tokens: {tokens}")
    
    analysis_keywords = ["analyze", "correlate", "optimize", "forecast"]
    has_keyword = any(kw in query.lower() for kw in analysis_keywords)
    
    if tokens >= 1000 or has_keyword:
        log.info(f"Selected {settings.claude_opus_model}")
        return settings.claude_opus_model
    else:
        log.info(f"Selected {settings.claude_haiku_model}")
        return settings.claude_haiku_model
```

### Example: Sentence Extraction
```python
async def _extract_sentences(self, text: str) -> List[str]:
    sentences = []
    buffer = text
    
    while buffer:
        match = SENTENCE_RE.match(buffer)
        if not match:
            break
        sentence = match.group(1).strip()
        if sentence:
            sentences.append(sentence)
        buffer = buffer[match.end():]
    
    return sentences
```

### Example: Tool Result Formatting
```python
def _format_tool_result(self, tool_use_id: str, content: str) -> dict:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }
```

### Example: Rate Limiting with Semaphore
```python
async def _make_api_call(self, **kwargs):
    async with self._semaphore:
        return await self.client.messages.create(**kwargs)
```

---

## Status Tracking

Use this to track your progress:

```
Phase 1: Model Selection
  [ ] _estimate_tokens() implemented
  [ ] select_model_for_query() implemented
  [ ] Logging added
  [ ] Tests: 4/4 passing

Phase 2: Streaming
  [ ] _extract_sentences() implemented
  [ ] chat() modified for sentence buffering
  [ ] Latency tracking added
  [ ] Tests: 4/5 passing

Phase 3: Tool Use
  [ ] _extract_tool_calls() implemented
  [ ] _execute_tool() implemented
  [ ] _format_tool_result() implemented
  [ ] get_full_response() implemented
  [ ] chat() modified for tool loop
  [ ] Tests: 6/6 passing

Phase 4: Rate Limiting
  [ ] Semaphore added to __init__
  [ ] _call_with_backoff() implemented
  [ ] _make_api_call() implemented
  [ ] Error handling for RateLimitError
  [ ] Tests: 4/4 passing

Phase 5: History
  [ ] _add_tool_result() implemented
  [ ] Tool results wired into chat()
  [ ] History passed to API calls
  [ ] Tests: 6/6 passing

Phase 6: Integration
  [ ] Metrics collection added
  [ ] Full flow tested
  [ ] Code formatted with black
  [ ] Type hints complete
  [ ] Tests: 3/3 passing

FINAL:
  [ ] All 24 tests passing ✅
  [ ] No regressions in existing tests
  [ ] Code reviewed
  [ ] Ready for merge
```

---

**Last Updated:** 2026-02-13
**Quick Ref Version:** 1.0
