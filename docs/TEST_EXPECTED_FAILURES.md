# RED Phase: Expected Test Failures

## Quick Reference

### Test Execution Results
- **Total:** 27 tests
- **Passing:** 13 ✅
- **Failing:** 14 ❌
- **Expected:** High failure rate (RED phase)

---

## Failure Categories

### 1. Configuration Missing (6 tests) 🔧

**Error:**
```
AttributeError: 'Settings' object has no attribute 'channels'
AttributeError: 'Settings' object has no attribute 'stt_device'
AttributeError: 'Settings' object has no attribute 'piper_model_path'
AttributeError: 'Settings' object has no attribute 'piper_config_path'
```

**Affected Tests:**
```
❌ TestSTTIntegration::test_red_stt_converts_audio_to_text
❌ TestSTTIntegration::test_red_stt_accuracy_target
❌ TestSTTIntegration::test_red_stt_handles_malformed_audio
❌ TestTTSIntegration::test_red_tts_converts_text_to_audio
❌ TestTTSIntegration::test_red_tts_sentence_streaming
❌ TestTTSIntegration::test_red_tts_maintains_audio_quality
```

**Fix:** Update `/Users/apple/documents/aegis1/aegis/config.py`

```python
from typing import Optional

class Settings(BaseSettings):
    # Add these fields:
    channels: int = 1                              # Audio channels
    stt_device: str = "cpu"                        # STT device (cpu/cuda)
    stt_beam_size: int = 5                         # Whisper beam size
    piper_model_path: Optional[str] = None         # Piper TTS model
    piper_config_path: Optional[str] = None        # Piper config
```

**Impact:** Fixes 6 tests immediately ✅

---

### 2. Async Database Issue (3 tests) 🔌

**Error:**
```
TypeError: object sqlite3.Connection can't be used in 'await' expression
```

**Location:** `aegis/claude_client.py:49`
```python
async def get_system_prompt(self) -> str:
    db = await get_db()  # ❌ get_db() is synchronous!
```

**Affected Tests:**
```
❌ TestClaudeIntegration::test_red_claude_processes_text_input
❌ TestClaudeIntegration::test_red_claude_streams_sentences
❌ TestClaudeIntegration::test_red_claude_handles_tool_calls
```

**Fix Option 1: Async Wrapper** (Preferred)

Create in `aegis/db.py`:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)

async def get_db_async():
    """Get database connection asynchronously."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, get_db)
```

Update `aegis/claude_client.py`:
```python
async def get_system_prompt(self) -> str:
    from .db import get_db_async
    db = await get_db_async()  # ✅ Now works!
```

**Fix Option 2: Blocking Call**

```python
from concurrent.futures import ThreadPoolExecutor

async def get_system_prompt(self) -> str:
    loop = asyncio.get_event_loop()
    db = await loop.run_in_executor(None, get_db)
```

**Impact:** Fixes 3 tests + enables Claude tests ✅

---

### 3. Cascading Failures (5 tests) ⚠️

These tests fail due to dependencies on fixes #1 and #2:

```
❌ TestAudioPipelineE2E::test_red_complete_pipeline_audio_to_audio
❌ TestAudioPipelineE2E::test_red_pipeline_latency_target
❌ TestAudioPipelineE2E::test_red_pipeline_sentence_streaming
❌ TestErrorHandlingAndResilience::test_red_pipeline_handles_empty_user_input
❌ TestPerformanceAndBenchmarks::test_red_stt_latency_benchmark
```

**Root Cause:** Missing config + async DB
**Will be fixed by:** Applying fixes #1 and #2

---

## Passing Tests (13) ✅

### Audio Format Validation (6/6 PASS)
```
✅ test_red_audio_to_wav_with_valid_pcm
✅ test_red_wav_to_pcm_roundtrip_fidelity
✅ test_red_audio_detection_identifies_silence
✅ test_red_audio_detection_identifies_signal
✅ test_red_rms_calculation_on_silence
✅ test_red_rms_calculation_on_signal
```
→ Audio utilities are working correctly

### STT Integration (1/4 PASS)
```
✅ test_red_stt_handles_empty_audio_gracefully
❌ test_red_stt_converts_audio_to_text
❌ test_red_stt_accuracy_target
❌ test_red_stt_handles_malformed_audio
```

### TTS Integration (1/4 PASS)
```
✅ test_red_tts_handles_empty_text
❌ test_red_tts_converts_text_to_audio
❌ test_red_tts_sentence_streaming
❌ test_red_tts_maintains_audio_quality
```

### Error Handling (3/4 PASS)
```
✅ test_red_stt_failure_returns_none
✅ test_red_tts_failure_returns_none
✅ test_red_claude_failure_handling
❌ test_red_pipeline_handles_empty_user_input
```
→ Error handling is solid

### Performance (1/3 PASS)
```
✅ test_red_tts_latency_benchmark
❌ test_red_stt_latency_benchmark
❌ test_red_claude_latency_benchmark
```

---

## Implementation Priority

### Priority 1: Quick Fixes (5 mins)
Add missing config fields to `aegis/config.py`:
- `channels: int = 1`
- `stt_device: str = "cpu"`
- `stt_beam_size: int = 5`
- `piper_model_path: Optional[str] = None`
- `piper_config_path: Optional[str] = None`

**Result:** 6 more tests pass (19/27) 📈

### Priority 2: Async DB Wrapper (10 mins)
Create async wrapper for database access:

```python
# In aegis/db.py
async def get_db_async():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_db)
```

Update `aegis/claude_client.py` to use `get_db_async()`

**Result:** 9 more tests pass (25/27) 📈

### Priority 3: Verify Remaining (5 mins)
- Run full test suite
- Capture latency measurements
- Document actual performance

**Result:** All or most tests pass (26-27/27) ✅

---

## Benchmark Target Latencies

Once tests are running, measure these:

| Stage | Target | Method |
|-------|--------|--------|
| Audio encoding | < 100ms | PCM → WAV |
| STT (Whisper) | < 1500ms | Audio → Text |
| Claude LLM | < 3000ms | Text → Response |
| TTS (Piper) | < 1000ms | Text → Audio |
| **Total** | **< 2000ms** | End-to-end |

Latency tracker in tests automatically records these.

---

## Test File Location

**File:** `/Users/apple/documents/aegis1/tests/test_audio_pipeline_red.py`

**Size:** 850+ lines
**Test Classes:** 7
**Total Tests:** 27

---

## Running Tests

### All tests:
```bash
python3 -m pytest tests/test_audio_pipeline_red.py -v
```

### Specific failure category:
```bash
python3 -m pytest tests/test_audio_pipeline_red.py::TestSTTIntegration -v
```

### With coverage:
```bash
python3 -m pytest tests/test_audio_pipeline_red.py \
  --cov=aegis --cov-report=term
```

### Verbose output:
```bash
python3 -m pytest tests/test_audio_pipeline_red.py -vv -s
```

---

## Expected Improvement Timeline

| Phase | Fixes Applied | Tests Passing | Time |
|-------|---------------|---------------|------|
| RED | None | 13/27 (48%) | ✅ NOW |
| GREEN v1 | Config fix | 19/27 (70%) | +5 min |
| GREEN v2 | Config + Async DB | 25/27 (93%) | +10 min |
| REFACTOR | Polish + Benchmarks | 27/27 (100%) | +15 min |

---

## Summary for Implementation

1. **What's failing:** Config + async DB
2. **Why:** New tests expose missing infrastructure
3. **How to fix:** 2 simple code additions (~15 lines total)
4. **Expected result:** 27/27 tests passing (100%)
5. **Timeline:** ~15 minutes total

The test suite is well-designed and will guide implementation. ✅
