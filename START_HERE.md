# RED Phase - Claude API Integration Tests

**Status:** ✅ COMPLETE - Ready for Implementation

**Quick Start:**
```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_claude_api_red.py -v
```

Expected Result: **24 failed, 5 passed** (correct for RED phase)

---

## What You Need to Know

### The Deliverable
- **Test Suite:** 1,078 lines of code, 29 tests across 6 classes
- **Documentation:** 45 KB across 4 comprehensive guides
- **Status:** All tests failing as expected (RED phase)
- **Next Step:** Implementation (6 phases, 10-15 hours estimated)

### Quick Facts
- **6 Critical Behaviors Tested:**
  1. Model Selection (Haiku/Opus routing)
  2. Response Streaming (sentence-by-sentence)
  3. Conversation History (context persistence)
  4. Rate Limiting (concurrency control)
  5. Tool Use (function calling)
  6. Integration (all features together)

- **24 Failing Tests** (100% documented)
- **5 Passing Tests** (existing implementations)
- **11 Methods to Implement**
- **4 Infrastructure Components to Add**

---

## Where to Start

### 1. **Quick Overview (5 min)**
   Read: `/Users/apple/documents/aegis1/RED_PHASE_DELIVERABLES.md`
   - What was built
   - Test breakdown
   - Implementation plan

### 2. **Detailed Test Summary (15 min)**
   Read: `/Users/apple/documents/aegis1/docs/RED_PHASE_TEST_SUMMARY.md`
   - Test organization
   - Acceptance criteria
   - Implementation checklist

### 3. **Why Tests Fail (20 min)**
   Read: `/Users/apple/documents/aegis1/docs/RED_PHASE_EXPECTED_FAILURES.md`
   - Every failure explained
   - Root causes categorized
   - How to fix each type

### 4. **How to Implement (coding reference)**
   Read: `/Users/apple/documents/aegis1/docs/IMPLEMENTATION_QUICK_REFERENCE.md`
   - Method signatures
   - Code examples
   - Phase-by-phase checklist

### 5. **View the Tests**
   Read: `/Users/apple/documents/aegis1/tests/test_claude_api_red.py`
   - Full test code
   - Comments explaining each test
   - Implementation notes embedded

---

## File Organization

```
/Users/apple/documents/aegis1/
├── tests/
│   └── test_claude_api_red.py (1,078 lines - THE TESTS)
│
├── docs/
│   ├── RED_PHASE_TEST_SUMMARY.md (overview)
│   ├── RED_PHASE_EXPECTED_FAILURES.md (detailed analysis)
│   └── IMPLEMENTATION_QUICK_REFERENCE.md (code guide)
│
├── RED_PHASE_DELIVERABLES.md (executive summary)
├── RED_PHASE_COMPLETION_REPORT.txt (full report)
└── START_HERE.md (this file)
```

---

## How to Use

### Run All Tests
```bash
python3 -m pytest tests/test_claude_api_red.py -v
```

### Test One Class
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic -v
```

### Test One Test
```bash
python3 -m pytest tests/test_claude_api_red.py::TestModelSelectionLogic::test_selects_haiku_for_simple_query_under_100_tokens -vv
```

### View Summary Only
```bash
python3 -m pytest tests/test_claude_api_red.py --tb=no -q
```

---

## The 6 Test Classes

### 1. TestModelSelectionLogic (4 tests) ❌
Haiku/Opus routing based on query complexity
- Token-based: < 100 tokens → Haiku
- Opus for large/complex queries
- Analysis keywords trigger Opus
- Logging with estimates

### 2. TestResponseStreaming (5 tests) ❌
Sentence-by-sentence streaming for TTS
- Complete sentences only (., !, ?)
- First token within 100ms
- No buffering delays > 500ms
- Incomplete sentence buffering

### 3. TestConversationHistoryManagement (6 tests) ⚠️
Context persistence across turns
- Persists across API calls
- Max 20 messages (FIFO trimming)
- Tool results as user messages
- Full history sent with each request

### 4. TestRateLimitHandling (4 tests) ❌
Concurrency and graceful degradation
- Max 3 concurrent requests
- Request queuing at limit
- Exponential backoff on 429 errors
- Recovery logging

### 5. TestToolUse (6 tests) ❌
Function calling and tool execution
- Detects tool calls from response
- Executes with correct arguments
- Feeds results back to Claude
- Multiple tools in single turn
- Error handling

### 6. TestContextPreservationAndStreaming (3 tests) ⚠️
Full integration of all features
- Context saved after streaming
- Latency metrics collected
- End-to-end conversation flow

---

## Implementation Plan (6 Phases)

| Phase | Focus | Hours | Tests Fixed |
|-------|-------|-------|------------|
| 1 | Model Selection | 2-3 | 4 |
| 2 | Streaming | 2-3 | 4 |
| 3 | Tool Use | 2-3 | 6 |
| 4 | Rate Limiting | 1-2 | 4 |
| 5 | History | 1-2 | 3 |
| 6 | Metrics & Polish | 1-2 | 2 |
| **TOTAL** | | **10-15** | **24** |

---

## Current Status

**RED Phase:** ✅ COMPLETE
- [x] 24 tests written (all failing as expected)
- [x] 5 tests passing (existing implementations)
- [x] Full documentation provided
- [x] Implementation checklist created

**GREEN Phase:** ⏳ READY TO START
- [ ] Implement Phase 1-6
- [ ] Run tests after each phase
- [ ] All 24 tests should be passing

---

## Key Methods to Implement

```python
# Phase 1: Model Selection
_estimate_tokens(text: str) → int
select_model_for_query(query: str) → str

# Phase 2: Streaming
_extract_sentences(text: str) → List[str]

# Phase 3: Tool Use
_extract_tool_calls(response) → List[dict]
_execute_tool(name: str, input: dict) → str
_format_tool_result(tool_use_id: str, content: str) → dict
get_full_response(query: str) → str

# Phase 4: Rate Limiting
_call_with_backoff() → Any
_make_api_call(**kwargs) → Any

# Phase 5: History
_add_tool_result(tool_result: dict) → None
```

---

## Success Criteria

### RED Phase (Current) ✅
- 24 tests written
- All tests fail as expected
- Failures clearly documented
- Implementation path clear

### GREEN Phase (Next) ⏳
- All 24 tests passing
- No regressions
- Code quality checks passing
- Manual testing complete

---

## Questions?

1. **"What do the tests test?"** → Read `RED_PHASE_TEST_SUMMARY.md`
2. **"Why do they fail?"** → Read `RED_PHASE_EXPECTED_FAILURES.md`
3. **"How do I fix them?"** → Read `IMPLEMENTATION_QUICK_REFERENCE.md`
4. **"Show me the code"** → Read `tests/test_claude_api_red.py`

---

## Next Steps

1. **Review:** Read the summary documents (30 min)
2. **Understand:** Run the tests and see failures (10 min)
3. **Plan:** Decide on implementation order (20 min)
4. **Implement:** Follow Phase 1 → 6 (10-15 hours)
5. **Verify:** All tests GREEN, code reviewed (2-3 hours)

---

**Created:** 2026-02-13  
**Phase:** RED (Failing Tests)  
**Status:** Ready for Implementation  
**Next Phase:** GREEN (Implementation)
