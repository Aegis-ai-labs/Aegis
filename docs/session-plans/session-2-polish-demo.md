# Session 2: Polish & Demo Preparation — Phase 4

**Date:** Feb 15, 2026
**Status:** Ready to begin
**Prerequisites:** Phase 3 complete ✅ (ESP32 integration working end-to-end)

## Current Status

**Completed:**
- ✅ Phase 1 (Foundation): Bridge server with Claude streaming + 7 tools working
- ✅ Phase 2 (Audio Pipeline): Full speech-to-speech via WebSocket operational
- ✅ Phase 3 (ESP32 Integration): Hardware connected, end-to-end testing complete
- ✅ Custom Ultra-Light Framework: 23+ files, 1956+ lines, 26+ tests passing
- ✅ Sentence-level streaming achieving <2s perceived latency
- ✅ ESP32 pendant operational with 4-state machine and LED patterns

**Architecture:**
- Direct Anthropic SDK (no Pipecat)
- FastAPI + WebSocket
- Haiku 4.5 / Opus 4.6 smart routing
- faster-whisper (STT) + Piper (TTS)
- SQLite with 30 days seeded demo data

**What's Left:**
- Comprehensive test coverage
- Edge case handling
- Final latency optimization
- Demo preparation and recording

---

## Session Objectives

1. **Complete comprehensive test suite** for all components
2. **Handle edge cases** (network drops, empty responses, tool errors)
3. **Optimize latency** to meet or exceed targets
4. **Prepare compelling demo** with script and video
5. **Pre-seed impactful demo data** for maximum wow factor

---

## Task Checklist

### Task 1: Complete Test Suite

**Goal:** Achieve 80%+ coverage on critical paths

**Files to create/update:**
- `tests/test_tools.py` — Unit tests for all 7 tools
- `tests/test_claude_client.py` — Claude streaming + tool use loop
- `tests/test_audio.py` — Audio processing, silence detection
- `tests/test_stt_tts.py` — STT and TTS integration
- `tests/test_orchestrator.py` — Full pipeline integration tests
- `tests/test_websocket.py` — WebSocket connection and streaming

**Test categories:**

1. **Tool tests** (tests/test_tools.py):
```python
def test_get_health_context():
    # Test retrieving health data for various date ranges
    # Test with missing data (empty database)
    # Test with various metric types

def test_log_health():
    # Test logging valid health metrics
    # Test handling invalid metric types
    # Test timestamp handling

def test_analyze_health_patterns():
    # Test pattern analysis with sufficient data
    # Test with insufficient data
    # Test correlation detection

def test_track_expense():
    # Test logging valid expenses
    # Test category validation
    # Test amount handling (negative, zero)

def test_get_spending_summary():
    # Test various time ranges
    # Test category filtering
    # Test empty results

def test_calculate_savings_goal():
    # Test achievable goals
    # Test unachievable goals
    # Test edge cases (zero income, negative spending)

def test_get_user_profile():
    # Test profile retrieval
    # Test with missing data
```

2. **Claude client tests** (tests/test_claude_client.py):
```python
def test_model_routing():
    # Test Opus triggers
    # Test Haiku default path
    # Test edge cases

def test_tool_use_loop():
    # Test single tool call
    # Test multiple tool rounds
    # Test max_tool_rounds limit
    # Test tool errors

def test_conversation_history():
    # Test history management
    # Test history truncation (40 message limit)
    # Test context preservation

def test_streaming():
    # Test text streaming
    # Test with tool calls
    # Test with thinking blocks
```

3. **Audio tests** (tests/test_audio.py):
```python
def test_silence_detection():
    # Test with silent audio
    # Test with speech audio
    # Test threshold tuning

def test_pcm_conversion():
    # Test PCM to WAV conversion
    # Test WAV to PCM conversion
    # Test format validation
```

4. **Integration tests** (tests/test_orchestrator.py):
```python
def test_full_pipeline():
    # Test speak → transcribe → Claude → TTS → audio
    # Test with tool calls
    # Test latency targets

def test_websocket_flow():
    # Test connection lifecycle
    # Test audio streaming
    # Test control messages
```

**Commands:**
```bash
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev

# Run tests with coverage
pytest --cov=bridge --cov-report=html tests/

# Check coverage report
open htmlcov/index.html

# Run specific test files
pytest tests/test_tools.py -v
pytest tests/test_claude_client.py -v
```

**Success criteria:**
- [ ] All tests pass
- [ ] Coverage ≥80% on bridge/tools/, bridge/claude_client.py, bridge/audio.py
- [ ] No flaky tests (run 10 times, all pass)

---

### Task 2: Edge Case Handling

**Goal:** System remains stable under adverse conditions

**Edge cases to handle:**

1. **Network issues:**
```python
# bridge/main.py - Add WebSocket reconnection logic
async def handle_websocket_disconnect(websocket):
    logger.warning("WebSocket disconnected, attempting reconnect...")
    # Graceful degradation
    # Clear audio buffers
    # Reset state machine
```

2. **Empty/invalid responses:**
```python
# bridge/claude_client.py - Handle empty Claude responses
if not full_response.strip():
    logger.error("Empty Claude response")
    full_response = "I'm having trouble processing that. Could you try again?"
```

3. **Tool errors:**
```python
# bridge/tools/registry.py - Add error handling
async def execute_tool(tool_name: str, tool_input: dict) -> str:
    try:
        result = await TOOL_REGISTRY[tool_name](**tool_input)
        return result
    except KeyError:
        logger.error(f"Unknown tool: {tool_name}")
        return f"Error: Unknown tool '{tool_name}'"
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return f"Error executing {tool_name}: {str(e)}"
```

4. **Audio quality issues:**
```python
# bridge/audio.py - Add noise filtering
def apply_noise_gate(audio_data: bytes, threshold: int = 500) -> bytes:
    """Remove low-amplitude noise from audio."""
    # Implement high-pass filter
    # Apply RMS threshold
    return filtered_audio

# bridge/stt.py - Handle transcription failures
if not segments:
    logger.warning("No speech detected in audio")
    return ""  # Empty string instead of error
```

5. **Database errors:**
```python
# bridge/db.py - Add connection pooling and retry logic
def get_db() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(settings.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        raise
```

**Testing commands:**
```bash
# Test network disconnection
# (Manually disconnect WiFi during WebSocket session)

# Test with silent audio
python -c "
import wave
import numpy as np
# Create 3 seconds of silence
silent = np.zeros(48000, dtype=np.int16)
with wave.open('silent.wav', 'wb') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    f.writeframes(silent.tobytes())
"
# Send to bridge and verify graceful handling

# Test with corrupted audio
dd if=/dev/urandom of=corrupt.pcm bs=1024 count=10
# Send to bridge and verify error handling
```

**Success criteria:**
- [ ] System recovers from network disconnections without crashing
- [ ] Empty/silent audio handled gracefully
- [ ] Tool errors logged and reported to user in natural language
- [ ] Database errors don't crash the server
- [ ] User receives helpful error messages, not stack traces

---

### Task 3: Final Latency Optimization

**Goal:** Meet or exceed latency targets consistently

**Current targets:**
- STT: <300ms
- Claude first token: <200ms (Haiku)
- TTS first chunk: <150ms
- Perceived latency: <750ms
- Full pipeline: <2.0s

**Optimization tasks:**

1. **Profile current latency:**
```bash
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev

# Add detailed latency logging
grep "latency" logs/bridge.log | tail -50

# Expected output:
# STT latency: 245ms
# Claude first token: 180ms
# TTS first chunk: 120ms
# Perceived latency: 650ms
# Full pipeline: 1.8s
```

2. **Optimize STT (if needed):**
```python
# bridge/stt.py - Tune faster-whisper parameters
model = WhisperModel(
    model_size_or_path="base",
    device="cpu",
    compute_type="int8",
    num_workers=2,  # Adjust based on CPU cores
)

# Use aggressive VAD filtering
segments, info = model.transcribe(
    audio_path,
    beam_size=1,  # Faster, slight accuracy tradeoff
    vad_filter=True,
    vad_parameters={
        "threshold": 0.5,
        "min_speech_duration_ms": 250,
        "min_silence_duration_ms": 500,
    },
)
```

3. **Optimize Claude streaming:**
```python
# bridge/claude_client.py - Ensure streaming starts immediately
response = self.client.messages.stream(
    model=model,
    max_tokens=settings.claude_max_tokens,
    system=SYSTEM_PROMPT,
    messages=messages,
    tools=TOOL_DEFINITIONS,
)

# Stream text as it arrives (already implemented)
with response as stream:
    for text in stream.text_stream:
        yield text
```

4. **Optimize TTS:**
```python
# bridge/tts.py - Ensure Piper streams audio
# Verify Piper is outputting raw PCM immediately
# Test with different Piper models (quality vs speed tradeoff)

# Benchmark different Piper voices
for voice in ["en_US-lessac-medium", "en_US-ryan-medium"]:
    start = time.monotonic()
    synthesize_speech("Test sentence", voice)
    latency = (time.monotonic() - start) * 1000
    print(f"{voice}: {latency:.0f}ms")
```

5. **Optimize sentence buffering:**
```python
# bridge/main.py - Fine-tune sentence boundary detection
import re

SENTENCE_BOUNDARY = re.compile(r'[.!?]\s+')

def split_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries."""
    return SENTENCE_BOUNDARY.split(text)
```

**Benchmark commands:**
```bash
# Run latency benchmark suite
python tests/test_latency.py

# Expected output:
# === Latency Benchmark Results ===
# STT (base model, beam_size=1):     245ms ± 15ms
# Claude first token (Haiku):        180ms ± 20ms
# TTS first chunk (Piper medium):    120ms ± 10ms
# Perceived latency:                 650ms ± 25ms
# Full pipeline (simple query):      1.8s ± 0.2s
# Full pipeline (Opus complex):      4.2s ± 0.5s
```

**Success criteria:**
- [ ] STT latency <300ms consistently
- [ ] Claude first token <200ms for Haiku queries
- [ ] TTS first chunk <150ms
- [ ] Perceived latency <750ms (user hears first sentence)
- [ ] Full pipeline <2.0s for simple queries
- [ ] Full pipeline <5.0s for Opus complex queries

---

### Task 4: Prepare Compelling Demo

**Goal:** 3-minute video demonstrating wow factor

**Demo script structure:**

1. **Opening (0:00-0:30):**
   - "Meet Aegis, your AI health and wealth coach in a pendant"
   - Show hardware: ESP32 pendant with LED
   - Quick architecture diagram overlay

2. **Simple health query (0:30-1:00):**
   - Press button (LED solid)
   - Ask: "How did I sleep last night?"
   - LED pulse (processing)
   - LED fast-blink (speaking)
   - Aegis responds: "You slept 6.2 hours last night. That's a bit below your 7-hour average. You might feel more energized with 30 more minutes of rest."

3. **Expense logging (1:00-1:30):**
   - Press button
   - Say: "I spent 45 dollars on lunch"
   - Aegis responds: "Got it! I logged a $45 food expense. That brings your food spending this week to $180, which is 20% higher than last week."

4. **Complex analysis - Opus 4.6 showcase (1:30-2:30):**
   - Press button
   - Ask: "Analyze my sleep patterns over the past week"
   - LED pulse (longer — Opus extended thinking)
   - Aegis responds: "Looking at your sleep data, I notice a clear weekday-weekend pattern. You're averaging 6.1 hours on weekdays but 8.2 hours on weekends. Your mood scores correlate strongly with sleep — days with less than 6 hours of sleep consistently show mood ratings of 2-3 out of 5, while days with 7+ hours show 4-5 ratings. I'd recommend trying to shift your weekday bedtime 30 minutes earlier."

5. **Closing (2:30-3:00):**
   - Architecture highlights: Custom Ultra-Light Framework
   - Latency metrics: <2s simple, <5s complex (Opus)
   - Impact statement: "Aegis empowers you to optimize health and wealth through conversational AI"

**Demo script file:**
```bash
# Create docs/demo-script.md
cat > docs/demo-script.md << 'EOF'
# AEGIS1 Demo Script

## Setup
- ESP32 pendant charged and on
- Bridge server running on laptop
- Screen recording software ready
- Test queries prepared

## Script

### Opening (30s)
**Visual:** Hardware close-up, LED breathing (idle state)
**Voiceover:** "Meet Aegis, your AI health and wealth coach in a pendant. Built with the Custom Ultra-Light Framework, Aegis achieves sub-2-second latency using Claude Haiku 4.5 and Opus 4.6 with sentence-level streaming."

### Demo 1: Simple Health Query (30s)
**Action:** Press button → LED solid → speak
**Query:** "How did I sleep last night?"
**Expected:** LED pulse → fast-blink → response in <2s
**Response:** "You slept 6.2 hours last night..."

### Demo 2: Expense Logging (30s)
**Action:** Press button
**Query:** "I spent 45 dollars on lunch"
**Expected:** Immediate confirmation + context
**Response:** "Got it! I logged a $45 food expense..."

### Demo 3: Complex Analysis (60s)
**Action:** Press button
**Query:** "Analyze my sleep patterns over the past week"
**Expected:** Longer processing (Opus extended thinking)
**Response:** Detailed correlation analysis with actionable advice

### Closing (30s)
**Visual:** Architecture diagram
**Voiceover:** "Aegis combines health tracking and wealth management in a wearable AI assistant. With smart model routing, it delivers fast responses for simple queries and deep insights for complex analysis."

## Technical Highlights
- Custom Ultra-Light Framework (23 files, 1956 lines)
- Sentence-level streaming (<2s perceived latency)
- Smart model routing (Haiku 80% / Opus 20%)
- 7 tools for health and wealth management
- 30 days of demo data with clear patterns
EOF
```

**Recording setup:**
```bash
# Use screen recording software
# Recommended: QuickTime (macOS), OBS Studio (cross-platform)

# Prepare demo environment
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev

# Start bridge with production config
python -m bridge.main

# Verify ESP32 connection
# Check serial monitor shows: "WebSocket connected"

# Run through script 2-3 times for best take
```

**Success criteria:**
- [ ] Demo video recorded (3 minutes)
- [ ] All queries work flawlessly
- [ ] Latency visible and impressive (<2s)
- [ ] Opus extended thinking demonstrated (>3s processing)
- [ ] LED states clearly visible
- [ ] Audio quality clear and understandable

---

### Task 5: Pre-Seed Impactful Demo Data

**Goal:** Demo data tells a compelling story

**Current demo data issues:**
- Seeded randomly → patterns may not be obvious
- Need DRAMATIC patterns for demo impact

**Enhanced demo data with clear stories:**

```python
# bridge/db.py - Update seed_demo_data() for demo impact

def seed_demo_data_for_demo(days: int = 30):
    """Seed 30 days with DRAMATIC patterns for demo."""
    conn = get_db()

    # Clear existing data
    conn.execute("DELETE FROM health_logs")
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM conversations")

    now = datetime.now()

    # Story 1: Clear weekday/weekend sleep pattern
    for day_offset in range(days, 0, -1):
        ts = now - timedelta(days=day_offset)
        date_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        is_weekend = ts.weekday() >= 5

        # DRAMATIC sleep difference
        if is_weekend:
            sleep = round(8.0 + random.gauss(0, 0.3), 1)  # 7.5-8.5 hours
        else:
            sleep = round(6.0 + random.gauss(0, 0.3), 1)  # 5.5-6.5 hours

        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("sleep_hours", sleep, "", date_str),
        )

        # STRONG mood correlation with sleep
        if sleep >= 7.0:
            mood = round(random.uniform(4.0, 5.0), 1)  # Great mood
        elif sleep >= 6.5:
            mood = round(random.uniform(3.5, 4.5), 1)  # Good mood
        else:
            mood = round(random.uniform(2.0, 3.0), 1)  # Poor mood

        conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("mood", mood, "", date_str),
        )

    # Story 2: Weekend food spending spike
    for day_offset in range(days, 0, -1):
        ts = now - timedelta(days=day_offset)
        date_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        is_weekend = ts.weekday() >= 5
        is_friday = ts.weekday() == 4

        if is_weekend or is_friday:
            # Weekend/Friday: High dining out spending
            expenses = [
                (55.00, "food", "dinner at restaurant"),
                (45.00, "food", "brunch with friends"),
                (25.00, "food", "takeout"),
            ]
        else:
            # Weekdays: Normal spending
            expenses = [
                (12.00, "food", "lunch"),
                (5.00, "food", "coffee"),
            ]

        for amt, cat, desc in expenses:
            amt = round(amt * random.uniform(0.9, 1.1), 2)
            conn.execute(
                "INSERT INTO expenses (amount, category, description, timestamp) VALUES (?, ?, ?, ?)",
                (amt, cat, desc, date_str),
            )

    conn.commit()
    conn.close()
```

**Verification:**
```bash
# Check demo data patterns
sqlite3 aegis1.db << 'EOF'
-- Weekday vs weekend sleep
SELECT
    CASE WHEN CAST(strftime('%w', timestamp) AS INTEGER) IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END as day_type,
    ROUND(AVG(value), 1) as avg_sleep
FROM health_logs
WHERE metric = 'sleep_hours'
GROUP BY day_type;

-- Food spending by day of week
SELECT
    strftime('%w', timestamp) as dow,
    ROUND(SUM(amount), 2) as total_food_spending
FROM expenses
WHERE category = 'food'
GROUP BY dow
ORDER BY dow;

-- Sleep vs mood correlation
SELECT
    h1.value as sleep_hours,
    ROUND(AVG(h2.value), 1) as avg_mood
FROM health_logs h1
JOIN health_logs h2 ON DATE(h1.timestamp) = DATE(h2.timestamp)
WHERE h1.metric = 'sleep_hours' AND h2.metric = 'mood'
GROUP BY ROUND(h1.value, 0)
ORDER BY sleep_hours;
EOF
```

**Success criteria:**
- [ ] Weekday sleep: 5.5-6.5 hours (avg 6.0)
- [ ] Weekend sleep: 7.5-8.5 hours (avg 8.0)
- [ ] Clear mood correlation: <6h sleep → mood 2-3, >7h sleep → mood 4-5
- [ ] Weekend food spending 2-3x weekday spending
- [ ] Patterns obvious in first glance at data

---

## Success Criteria

- [ ] Test suite coverage ≥80% on critical paths
- [ ] All tests pass (26+ tests currently, 50+ after completion)
- [ ] Edge cases handled gracefully (no crashes)
- [ ] Latency targets met or exceeded consistently
- [ ] Demo video recorded (3 minutes, high quality)
- [ ] Demo script documented
- [ ] Demo data tells compelling story
- [ ] No console errors during demo runs
- [ ] WebSocket connections stable (no disconnections)
- [ ] Audio quality excellent (clear, no distortion)

---

## Troubleshooting

### Tests failing

```bash
# Check test output for specific failures
pytest tests/ -v --tb=short

# Run specific test in isolation
pytest tests/test_tools.py::test_get_health_context -v

# Check coverage gaps
pytest --cov=bridge --cov-report=term-missing tests/
```

### Latency not meeting targets

```bash
# Profile slow stages
python -m cProfile -s cumtime bridge/main.py

# Check faster-whisper model size
# Try switching from "base" to "tiny" for speed

# Check Piper TTS model
# Try switching to faster voice model

# Verify sentence buffering working
grep "sentence boundary" logs/bridge.log
```

### Demo data patterns not clear

```bash
# Re-seed with enhanced demo data
python -c "
from bridge.db import seed_demo_data_for_demo
seed_demo_data_for_demo(30)
"

# Verify patterns
sqlite3 aegis1.db < verify-patterns.sql
```

### Demo recording issues

```bash
# Audio quality check
# Ensure mic close to speaker (15-20cm)
# Ensure quiet environment
# Test audio levels before recording

# LED visibility
# Ensure well-lit environment
# Position camera for clear LED view
# Test LED patterns before recording
```

---

## Files Modified This Session

Track all changes:
```bash
# List modified files
git status

# Review changes
git diff

# Commit with descriptive message
git add tests/ bridge/ docs/demo-script.md
git commit -m "feat(phase4): polish and demo preparation

- Added comprehensive test suite (50+ tests)
- Implemented edge case handling for network/audio/tool errors
- Optimized latency (STT, Claude, TTS, sentence buffering)
- Created demo script and recorded 3-minute video
- Enhanced demo data with dramatic patterns (sleep/mood/spending)
- Latency: <2s simple queries, <5s complex queries
- Coverage: 85%+ on critical paths"
```

---

## Next Session

After Phase 4 complete, move to **Session 3: Final Submission**
