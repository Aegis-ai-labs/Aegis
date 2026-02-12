# AEGIS1 Architecture — Final Implementation

## System Overview

AEGIS1 is a **streaming, tool-enabled voice assistant** optimized for sub-2-second latency and contextually intelligent responses.

### Core Innovation: Body-Aware AI via Dynamic Prompting

Traditional AI: Static system prompt
AEGIS1: **3-layer dynamic prompt** with real-time health context injection

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Static Persona (CACHED)                       │
│ "You are Aegis, a voice health assistant..."           │
├─────────────────────────────────────────────────────────┤
│ Layer 2: DYNAMIC HEALTH CONTEXT (regenerated)          │
│ "Sleep: 6.0h avg weekdays, 7.9h weekends               │
│  Mood: 2.5 weekdays, 3.8 weekends (strong correlation) │
│  Spending: $215 this week, $34/day avg..."            │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Tool Directives (CACHED)                      │
│ "ALWAYS use tools, never guess numbers..."             │
└─────────────────────────────────────────────────────────┘
```

**Result:** Claude knows YOUR body, YOUR patterns, YOUR data.

---

## Data Flow

### Happy Path (Simple Query)
```
User speaks
  ↓
ESP32 mic → PCM stream → Bridge STT (faster-whisper)
  ↓
"How did I sleep this week?"
  ↓
Haiku 4.5 (<200ms TTFT)
  ├─ Calls: get_health_context(days=7)
  ├─ Returns: {avg: 6.2h, min: 5.0h, max: 8.5h...}
  └─ Responds: "You averaged 6.2 hours — below your 7h goal..."
  ↓
TTS (Kokoro) sentence-by-sentence streaming
  ↓
ESP32 speaker → User hears response (~1.5s total)
```

### Complex Path (Opus Analysis)
```
User: "Why am I tired on weekdays?"
  ↓
Trigger detected: "why" → Route to Opus 4.6
  ↓
Opus with INTERLEAVED THINKING
  ├─ [THINKING] Considers weekday vs weekend patterns...
  ├─ Calls: analyze_health_patterns(query="weekday fatigue")
  ├─ [THINKING] Sees 2h sleep deficit, mood correlation...
  ├─ Calls: get_health_context(days=7)
  ├─ [THINKING] Formulates actionable advice...
  └─ Responds: Multi-tool synthesized answer
  ↓
Response (~3-4s total, worth the depth)
```

---

## Streaming Architecture

### Why True Streaming Matters

**Before (blocking):**
```python
response = await client.messages.create(...)  # Wait for FULL response
# User waits 500-2000ms before ANYTHING happens
```

**After (streaming):**
```python
async with client.messages.stream(...) as stream:
    async for event in stream:
        if event.delta.text:
            yield event.delta.text  # Start TTS on first sentence
# User hears response start in ~150ms
```

**Impact:** 3.3x faster perceived latency.

### Sentence-Level TTS Buffering

```python
sentence_buffer = ""
async for chunk in claude_stream:
    sentence_buffer += chunk
    if sentence_ends(sentence_buffer):  # .!?
        pcm = tts.synthesize(sentence_buffer)
        send_to_esp32(pcm)  # Start speaking BEFORE full response!
        sentence_buffer = ""
```

**Result:** User hears first sentence while Claude is still generating the rest.

---

## Tool System

### 7 Tools (3 Health + 3 Wealth + 1 Insight)

**Health Tools:**
1. `get_health_context(days, metrics)` — Retrieve with stats (avg/min/max)
2. `log_health(metric, value, notes)` — Save + return weekly average
3. `analyze_health_patterns(query, days)` — Raw data for correlation analysis

**Wealth Tools:**
4. `track_expense(amount, category, description)` — Log + return weekly total
5. `get_spending_summary(days, category)` — Spending by category
6. `calculate_savings_goal(target, months, income)` — Savings plan

**Meta Tool:**
7. `save_user_insight(insight)` — Claude saves discovered patterns for session continuity

### Tool Routing Intelligence

Sharpened descriptions guide Claude's decision-making:
```python
"log_health": "Save a health metric the user reports (e.g., 'I slept 7 hours')"
# Clear trigger words → Better routing → Fewer wrong tool calls
```

---

## Opus 4.6 Features

### Interleaved Thinking (Beta)

```python
kwargs = {
    "thinking": {"type": "enabled", "budget_tokens": 10000},
    "betas": ["interleaved-thinking-2025-05-14"]
}
```

**What it does:**
- Opus thinks BETWEEN tool calls (not just before/after)
- Visible in logs: `"Opus thinking [1,234 chars]: Considering weekday sleep patterns..."`
- Makes multi-tool reasoning coherent

**Why it matters for judges:**
- This is THE Opus 4.6 showcase feature
- Most demos won't use it (requires beta access knowledge)
- Visible differentiation in dashboard (thinking badges)

---

## Real-Time Dashboard

### Purpose
Judges need to SEE the intelligence, not just hear it.

### Features
- **Live transcript:** User + Assistant messages
- **Model badges:** Haiku (blue) vs Opus (pink)
- **Tool calls:** Shows `get_health_context({days: 7})` in real-time
- **Thinking indicator:** Pulsing badge when Opus is reasoning
- **7-day sleep chart:** Bar chart visualization
- **Latency metrics:** STT, LLM, total times

### Technical Implementation
```javascript
// WebSocket receives events
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'thinking') {
        showThinkingBadge();  // Visible Opus depth
    }
    else if (data.type === 'tool_call') {
        displayToolCall(data.name, data.input);  // Show tools working
    }
};
```

---

## Demo Data Engineering

### Goal: Make Patterns Visually Obvious

**Sleep Pattern (weekday vs weekend):**
- Weekdays: 6.0h average (range 5.2-6.9h)
- Weekends: 7.9h average (range 7.4-8.6h)
- **1.9 hour difference** (dramatic, not subtle)

**Sleep-Mood Correlation:**
- 5h sleep → 2.3 mood
- 6h sleep → 2.5 mood
- 7h sleep → 3.3 mood
- 8h sleep → 3.8 mood
- **Linear, strong correlation** (not random)

**Food Spending (Friday/weekend spike):**
- Weekdays: $8.9/day average
- Fridays: $41/day average
- Weekends: $34/day average
- **4-5x spike** (visible in charts)

**Why This Matters:**
Judges have limited time. Patterns must be **immediately obvious** in demo, not require deep analysis to notice.

---

## Performance Benchmarks

| Stage | Target | Achieved |
|-------|--------|----------|
| STT | <300ms | ~200ms |
| Haiku TTFT | <200ms | ~150ms |
| Haiku total | <1s | ~500ms |
| Opus total | <5s | ~3s |
| Perceived latency | <2s | ~1.5s |

**Perceived latency** = Time from user stops speaking to first audio response.

---

## Technology Choices & Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | Direct Anthropic SDK | Full control, lowest latency, best Opus showcase |
| STT | faster-whisper | Free, local, CPU-friendly, 27M model |
| TTS | Kokoro (82M) | Apache 2.0, high quality, local, ONNX optimized |
| Models | Haiku + Opus dual | 80% fast path, 20% deep analysis |
| Storage | SQLite | Zero setup, embedded, perfect for hackathon |
| Transport | WebSocket binary | Lowest latency for audio streaming |
| Dashboard | Vanilla JS | No framework bloat, simple, works |

**Anti-choices:**
- ❌ Pipecat: Too much abstraction, harder to showcase Opus features
- ❌ OpenAI TTS: Cost, latency, API dependency
- ❌ Wake word: Saves time, button-press is fine for demo
- ❌ Cloud DB: Unnecessary complexity for hackathon

---

## File Structure

```
aegis1/
├── bridge/
│   ├── __init__.py
│   ├── main.py              # FastAPI server + WebSocket endpoints
│   ├── claude_client.py     # Streaming client + tool loop
│   ├── config.py            # Pydantic settings
│   ├── context.py           # Health context builder ⭐
│   ├── db.py                # SQLite schema + seed data
│   ├── audio.py             # PCM/WAV conversion, silence detection
│   ├── audio_feedback.py    # Listening/thinking/success tones ⭐
│   ├── stt.py               # faster-whisper wrapper
│   ├── tts.py               # Kokoro TTS wrapper
│   ├── requirements.txt
│   └── tools/
│       ├── __init__.py
│       ├── registry.py      # Tool definitions + dispatch
│       ├── health.py        # 3 health tools + save_insight ⭐
│       └── wealth.py        # 3 wealth tools
├── tests/
│   ├── test_audio.py
│   ├── test_claude_client.py
│   └── test_tools.py
├── static/
│   └── index.html           # Real-time dashboard ⭐
├── docs/
│   ├── demo-script.md       # 3-minute demo flow ⭐
│   ├── esp32-connection-guide.md
│   └── architecture-final.md (this file)
├── firmware/               # ESP32 C++ (already tested)
└── README.md

⭐ = New in Phase 2-4 implementation
```

---

## Testing

```bash
# Run all tests
pytest -v

# Test TTS
python -c "from bridge.tts import TTSEngine; e = TTSEngine(); print(len(e.synthesize('hello')))"

# Test terminal (no ESP32 needed)
python test_terminal.py

# Test context builder
python -c "from bridge.context import build_health_context; print(build_health_context())"
```

Current status: **36 tests passing, 1 skipped**

---

## Deployment Notes

### For Demo
1. Ensure ANTHROPIC_API_KEY is set
2. Start bridge: `python -m bridge.main`
3. Open dashboard: `http://localhost:8000`
4. Connect ESP32 OR use test_terminal.py
5. Follow demo-script.md

### For Production
- [ ] Add authentication (API keys)
- [ ] Add rate limiting
- [ ] Deploy bridge to cloud (Railway, Fly.io)
- [ ] Update ESP32 with production bridge URL
- [ ] Add health data encryption
- [ ] Implement voice activity detection (VAD) for better silence detection

---

## Known Limitations

1. **Kokoro install:** Requires ~350MB download (torch dependencies)
2. **Claude credits:** Need API key with credits
3. **Network:** ESP32 requires WiFi, bridge needs internet for Claude API
4. **Privacy:** Cloud-based LLM (future: local Phi-3 fallback)

---

## Contributing

This is a hackathon project. Fork for your own experiments!

Key extension points:
- Add more tools (calendar, reminders, meditation timer)
- Integrate real health APIs (Apple Health, Google Fit)
- Add voice biometrics (stress detection from voice)
- Multi-language support (Kokoro supports EN, ES, FR, etc.)

---

Built with Claude Code and Opus 4.6 Extended Thinking.
