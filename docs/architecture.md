# AEGIS1 — System Architecture

*Last updated: Feb 12, 2026 (Day 3)*

## 1. System Overview

```
┌─────────────────────┐  WebSocket (ADPCM)    ┌────────────────────────────────────────────┐
│   ESP32 Pendant     │ <──────────────────> │      Python Bridge Server (FastAPI)       │
│                     │  Binary audio +       │                 aegis/                    │
│  ┌──────────────┐  │  JSON control msgs    │                                            │
│  │   INMP441    │  │                       │  ┌──────────────┐    ┌──────────────────┐ │
│  │  (Mic I2S)   │──┤                       │  │  Silero VAD  │    │  Moonshine STT   │ │
│  │ GPIO13/14/33 │  │                       │  │   <1ms per   │───>│  Streaming Tiny  │ │
│  └──────────────┘  │                       │  │    chunk     │    │   5x faster      │ │
│  ┌──────────────┐  │                       │  └──────────────┘    └────────┬─────────┘ │
│  │  PAM8403     │  │                       │                               │           │
│  │ (Speaker DAC)│<─┤                       │  ┌────────────────────────────┴────────┐  │
│  │  GPIO25      │  │                       │  │        Claude API (Anthropic)       │  │
│  └──────────────┘  │                       │  │                                      │  │
│  ┌──────────────┐  │                       │  │  ┌───────────┐    ┌──────────────┐ │  │
│  │     LED      │  │                       │  │  │  Haiku    │    │   Opus 4.6   │ │  │
│  │   GPIO2      │  │                       │  │  │  4.5      │    │  Extended    │ │  │
│  │    Button    │  │                       │  │  │  Fast     │    │  Thinking    │ │  │
│  │   GPIO0      │  │                       │  │  │ <200ms    │    │ 10k budget   │ │  │
│  └──────────────┘  │                       │  │  └─────┬─────┘    └──────┬───────┘ │  │
└─────────────────────┘                       │  │        │                 │         │  │
                                              │  │        └─────── OR ──────┘         │  │
                                              │  │                 │                   │  │
                                              │  │          Parallel Pattern:          │  │
                                              │  │          Haiku quick ack +          │  │
                                              │  │          Opus async deep analysis   │  │
                                              │  └───────────────┬─────────────────────┘  │
                                              │                  │                        │
                                              │  ┌───────────────▼──────────┐            │
                                              │  │   Tool Dispatch          │            │
                                              │  │   7 tools (3H, 3W, 1P)   │            │
                                              │  │   health/wealth/profile  │            │
                                              │  └───────────┬──────────────┘            │
                                              │              │                           │
                                              │  ┌───────────▼──────────────┐            │
                                              │  │  SQLite + sqlite-vec     │            │
                                              │  │  • user_health_logs      │            │
                                              │  │  • user_expenses         │            │
                                              │  │  • conversation_memory   │            │
                                              │  │  • users (profiles)      │            │
                                              │  └──────────────────────────┘            │
                                              │                  │                        │
                                              │  ┌───────────────▼──────────┐            │
                                              │  │   Kokoro TTS (82M ONNX)  │            │
                                              │  │   Local, Apache 2.0      │            │
                                              │  │   <100ms per sentence    │            │
                                              │  └───────────┬──────────────┘            │
                                              │              │                           │
                                              │  ┌───────────▼──────────────┐            │
                                              │  │  ADPCM Compression       │            │
                                              │  │  256kbps → 64kbps (4x)   │            │
                                              │  └──────────────────────────┘            │
                                              │                                           │
                                              │  Optional:                                │
                                              │  ┌──────────────────────────┐            │
                                              │  │  Phi-3-mini (Ollama)     │            │
                                              │  │  <200ms simple queries   │            │
                                              │  └──────────────────────────┘            │
                                              └───────────────────────────────────────────┘
```

## 2. Streaming Pipeline (Critical Path)

This is the latency-critical path for **simple queries** (Haiku, 440ms target):

```
User speaks → ESP32 mic → PCM chunks (200ms @ 16kHz 16-bit mono)
                              │
                              ▼ WebSocket binary (ADPCM compressed)
                    ┌─────────────────────────┐
                    │  ADPCM Decompression    │ <5ms
                    │  64kbps → 256kbps PCM   │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │    Silero VAD           │ <1ms per chunk
                    │  Voice probability      │ threshold: 0.5
                    │  N low chunks = end     │ (N=10 chunks = 2s)
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Moonshine STT Tiny     │ ~80ms
                    │  27M params, streaming  │ 5x faster than
                    │  native chunk process   │ faster-whisper
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Model Routing          │ keyword match
                    │  "analyze" → Opus       │ default → Haiku
                    │  Simple → Haiku 4.5     │
                    └───────────┬─────────────┘
                                ▼
        ┌─────────────────────────────────────────────────────┐
        │               SIMPLE PATH (Haiku)                   │
        │  ┌──────────────────────────────────────────────┐  │
        │  │  3-Layer System Prompt Injection:            │  │
        │  │  Layer 1: Static persona (cached)            │  │
        │  │  Layer 2: Dynamic health context (fresh)     │  │
        │  │  Layer 3: Static tools (cached)              │  │
        │  └────────────────┬─────────────────────────────┘  │
        │                   ▼                                 │
        │  ┌──────────────────────────────────────────────┐  │
        │  │  Haiku 4.5 Streaming                         │  │ ~150ms TTFT
        │  │  messages.stream() → token-by-token          │  │
        │  └────────────────┬─────────────────────────────┘  │
        │                   ▼                                 │
        │  ┌──────────────────────────────────────────────┐  │
        │  │  Tool Loop (if tool_use blocks)              │  │
        │  │  Max 5 rounds, dispatch to health/wealth     │  │
        │  └────────────────┬─────────────────────────────┘  │
        │                   ▼                                 │
        │  ┌──────────────────────────────────────────────┐  │
        │  │  Sentence Buffer                             │  │
        │  │  Buffer until . ! ? → immediately:           │  │
        │  └────────────────┬─────────────────────────────┘  │
        └───────────────────┼─────────────────────────────────┘
                            ▼
                ┌───────────────────────┐
                │  Kokoro TTS (82M)     │ ~60ms per sentence
                │  ONNX local inference │
                └───────────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │  ADPCM Compression    │ <5ms
                │  256kbps → 64kbps     │
                └───────────┬───────────┘
                            ▼
                      WebSocket binary → ESP32 speaker
```

**Parallel Opus Pattern** (for complex queries like "analyze my sleep patterns"):

```
                    Moonshine STT
                         │
                         ▼
            ┌────────────────────────────┐
            │     Model Router           │
            │  "analyze" detected        │
            │  → Parallel Opus Pattern   │
            └──────┬────────────┬────────┘
                   │            │
        ┌──────────▼──┐      ┌──▼─────────────────────────┐
        │  Haiku Ack  │      │  Opus 4.6 Deep Analysis    │
        │  Quick resp │      │  (asyncio.create_task)     │
        │ "Let me     │      │  Extended thinking on      │
        │  analyze    │      │  budget_tokens=10000       │
        │  that..."   │      │  interleaved-thinking beta │
        └──────┬──────┘      └────────────┬───────────────┘
               │                          │
               ▼                          │ (runs async)
          Kokoro TTS                      │
               │                          │
               ▼                          │
       ESP32 speaker                      │
     (user hears ack in ~440ms)           │
                                          ▼
                                     Wait for Opus
                                     (2-4 seconds)
                                          │
                                          ▼
                                   Kokoro TTS
                                          │
                                          ▼
                                   ESP32 speaker
                              (deep analysis streamed)
```

**Key insight:** Sentence-level streaming means TTS starts on the first sentence boundary, not after the full Claude response. While Kokoro synthesizes sentence 1, Claude is still generating sentence 2. This overlapping achieves <440ms perceived latency.

## 3. Health Personalization Architecture

### 3.1 Dynamic System Prompt Injection (3-Layer Pattern)

Every Claude request uses a **3-layer system prompt** to make responses body-aware:

```python
# Layer 1: Static Cached Persona & Rules
"""
You are AEGIS, a voice assistant for a health & wealth tracking pendant worn by the user.
Speak concisely (1-2 sentences for simple queries, up to 4 for analysis).
Use present tense, warm tone, actionable advice.
Never hallucinate data — always use tools to query the database.
"""
# Cache control: ephemeral (cached after first request)

# Layer 2: Dynamic Health Context (Regenerated Every Call)
"""
User's recent health context (last 7 days):
- Sleep: Avg 6.2 hours/night (target: 7+). Notable: 3 days <6 hours (Mon, Wed, Fri).
- Steps: Avg 8,500/day (good). Lowest: 4,200 (Sunday).
- Heart rate: Avg resting 68 bpm (healthy).
- Weight: Stable at 165 lbs.
- Exercise: 4 days with 30+ minutes.
Patterns: Sleep deprivation correlates with low step count next day.
"""
# Generated by: build_health_context(user_id, days=7) from user_health_logs table
# Cache control: None (fresh every request)

# Layer 3: Static Cached Tool Directives
"""
Available tools:
- Health: get_health_context, log_health, analyze_patterns
- Wealth: track_expense, spending_summary, savings_goal
- Profile: save_user_insight (store user preferences)

Use tools to query/write data. Max 5 tool call rounds per conversation turn.
"""
# Cache control: ephemeral (cached after first request)
```

**Benefits:**
- Layers 1+3 cached → reduced latency after first call (prompt caching)
- Layer 2 dynamic → Claude always knows current body state
- Personalized responses: "You've been sleeping less than usual this week, and your step count dropped. Consider prioritizing rest tonight." (not generic advice)

### 3.2 Apple Health Import Flow

```
                 ┌──────────────────────┐
                 │  Apple Health App    │
                 │  "Export Health Data"│
                 └──────────┬───────────┘
                            │ export.xml
                            ▼
         ┌────────────────────────────────────────┐
         │  python -m aegis import-health         │
         │  path/to/export.xml                    │
         └──────────┬─────────────────────────────┘
                    │
                    ▼
         ┌────────────────────────────────────────┐
         │  health_import.py                      │
         │  • Parse XML (lxml)                    │
         │  • Extract 5 types:                    │
         │    - steps (HKQuantityTypeIdentifier   │
         │      StepCount)                        │
         │    - heart_rate (HeartRate)            │
         │    - weight (BodyMass)                 │
         │    - exercise_minutes (AppleExercise   │
         │      Time)                              │
         │    - sleep_hours (SleepAnalysis)       │
         └──────────┬─────────────────────────────┘
                    │
                    ▼
         ┌────────────────────────────────────────┐
         │  INSERT INTO user_health_logs          │
         │  (user_id, metric, value, timestamp)   │
         │  • Deduplicate by timestamp            │
         │  • Validate ranges (e.g., sleep 0-24h) │
         └────────────────────────────────────────┘
```

**One-time setup:**
1. User exports Apple Health data (Settings → Health → Export)
2. Run `python -m aegis import-health export.xml`
3. Data loaded to `user_health_logs` table
4. `build_health_context()` now uses real data instead of synthetic demo data

## 4. Model Routing & Extended Thinking

### 4.1 Routing Decision Tree

```
User query text (from Moonshine STT)
        │
        ▼
┌───────────────────────┐
│  Keyword Analysis     │
│  Check for:           │
│  • "analyze"          │
│  • "pattern"          │
│  • "why am I"         │
│  • "correlation"      │
│  • "plan"             │
│  • "should I"         │
└────┬──────────────┬───┘
     │              │
     │ No match     │ Match found
     │              │
     ▼              ▼
┌────────────┐  ┌─────────────────────┐
│  Haiku     │  │  Parallel Opus      │
│  Fast Path │  │  Pattern            │
│  <200ms    │  │  1. Haiku quick ack │
│  TTFT      │  │  2. Opus async deep │
└────────────┘  └─────────────────────┘
```

### 4.2 Extended Thinking Configuration

**Opus 4.6 requests use:**
- Header: `anthropic-beta: interleaved-thinking-2025-05-14`
- Parameter: `budget_tokens=10000` (allows Claude 10k tokens of internal reasoning)
- Streaming: `messages.stream()` with `text` and `thinking` event types
- Purpose: Showcase extended thinking on complex health correlations (e.g., "Why do I feel tired on Mondays?" → Opus reasons about sleep debt accumulation, weekend patterns, circadian disruption)

**Example extended thinking flow:**
```
User: "Why am I always tired on Mondays?"
  │
  ▼
Haiku (quick ack): "Let me analyze your weekly patterns..."
  │ (user hears this in ~440ms)
  ▼
Opus (async deep analysis):
  thinking: "Need to look at sleep patterns across weeks, compare 
             weekend vs weekday sleep, check for sleep debt 
             accumulation, consider exercise and nutrition timing..."
  tool_use: get_health_context(days=30, metrics=["sleep", "exercise"])
  tool_use: analyze_patterns(metric="sleep", days=30)
  thinking: "I see a pattern: Friday/Saturday late sleep (avg 1am), 
             Sunday recovery attempt but still 7h, Monday morning 6am 
             alarm = sleep debt. Exercise drops on weekends too."
  text: "Your Monday fatigue stems from weekend sleep schedule shifts. 
         You're going to bed 2 hours later Friday and Saturday, 
         recovering Sunday, but Monday's 6am alarm still cuts into 
         your sleep debt. Try keeping bedtime within 1 hour of your 
         weekday schedule, even on weekends."
  │ (streamed sentence-by-sentence to TTS)
  ▼
Kokoro TTS → ESP32 speaker
```

## 5. Tool Architecture

### 5.1 Tool Registry

Seven tools organized into three domains:

**Health Tools** (`aegis/tools/health.py`):
| Tool | Parameters | Returns | Example Query |
|------|-----------|---------|---------------|
| `get_health_context` | `days` (int, default 7), `metrics` (list[str], optional) | Grouped entries with avg/min/max per metric | "How did I sleep this week?" |
| `log_health` | `metric` (enum), `value` (number), `timestamp` (str, optional), `notes` (str) | Confirmation with logged values | "I slept 7 hours" |
| `analyze_patterns` | `metric` (str), `days` (int, default 30) | Daily records for specified metric (raw data for Claude to analyze) | "Analyze my sleep patterns" |

**Wealth Tools** (`aegis/tools/wealth.py`):
| Tool | Parameters | Returns | Example Query |
|------|-----------|---------|---------------|
| `track_expense` | `amount` (number), `category` (enum), `description` (str), `timestamp` (str, optional) | Confirmation + week total in category | "I spent $12 on lunch" |
| `spending_summary` | `days` (int, default 30), `category` (str, optional) | Total, daily avg, by-category breakdown, recent 5 | "How much did I spend this month?" |
| `savings_goal` | `target_amount` (number), `target_months` (int), `current_savings` (number, optional) | Monthly savings needed, spending analysis, gap to goal | "Save $5000 in 6 months" |

**Profile Tool** (`aegis/tools/profile.py`):
| Tool | Parameters | Returns | Example Query |
|------|-----------|---------|---------------|
| `save_user_insight` | `key` (str), `value` (str), `category` (enum: preference/goal/constraint) | Confirmation of stored insight | "Remember I'm vegetarian" → saves to profile for future personalization |

### 5.2 Tool Execution Flow

```
Claude streaming response contains tool_use block
    │
    ▼
┌─────────────────────────────────────────┐
│  registry.execute_tool(name, args)      │
│  • Validate against JSON schema         │
│  • Dispatch to domain handler:          │
│    - health.* → health.py                │
│    - wealth.* → wealth.py                │
│    - profile.* → profile.py              │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│  Tool function (e.g., log_health)       │
│  • Query/insert to SQLite                │
│  • Return JSON string                    │
│    {"success": true, "data": {...}}      │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│  Tool result sent back to Claude as     │
│  tool_result block in conversation      │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│  Claude generates natural language      │
│  response using tool data                │
│  (loop continues for up to 5 rounds)    │
└─────────────────────────────────────────┘
```

## 6. Data Model (SQLite + sqlite-vec)

```sql
-- User profiles
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Health tracking (Apple Health import target)
CREATE TABLE user_health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    metric TEXT NOT NULL,           -- sleep_hours, steps, heart_rate, weight, exercise_minutes
    value REAL NOT NULL,            -- numeric value
    notes TEXT DEFAULT '',          -- optional context
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_user_health ON user_health_logs(user_id, metric, timestamp);

-- Expense tracking
CREATE TABLE user_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    amount REAL NOT NULL,           -- dollar amount
    category TEXT NOT NULL,         -- food, transport, housing, health, entertainment, shopping, utilities, other
    description TEXT DEFAULT '',    -- what was purchased
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_user_expense ON user_expenses(user_id, category, timestamp);

-- User profile insights (for personalization)
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    key TEXT NOT NULL,              -- e.g., "dietary_restriction", "fitness_goal"
    value TEXT NOT NULL,            -- e.g., "vegetarian", "run 5k"
    category TEXT NOT NULL,         -- preference, goal, constraint
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX idx_user_profile_key ON user_profile(user_id, key);

-- Conversation memory (sqlite-vec for semantic search)
CREATE VIRTUAL TABLE conversation_memory USING vec0(
    user_id INTEGER,
    turn_id INTEGER,
    role TEXT,                      -- user or assistant
    content TEXT,
    embedding FLOAT[512],           -- text-embedding-3-small
    timestamp DATETIME
);
-- Query: SELECT * FROM conversation_memory 
--        WHERE user_id = 1 AND vec_distance_cosine(embedding, ?) < 0.3
--        ORDER BY vec_distance_cosine(embedding, ?) LIMIT 5
```

**Demo data seeding:**
- 30 days auto-seeded with `random.seed(42)` for reproducibility
- Health: Sleep (5-9h with weekday/weekend variance), steps (4k-12k), heart rate (60-80 bpm), weight (163-167 lbs trending down), exercise (0-60 min/day)
- Expenses: 1-3 daily expenses across categories ($5-$150 range, food most frequent)
- Patterns: Sleep correlates with next-day steps, weekend spending higher, mood tracks sleep

## 7. WebSocket Protocol

### 7.1 ESP32 → Bridge (aegis server)

**Binary frames (audio):**
- Format: ADPCM compressed PCM
- Compression: 4x (256kbps raw → 64kbps ADPCM)
- Sample rate: 16kHz, 16-bit mono
- Chunk size: 200ms worth (1600 bytes PCM → 400 bytes ADPCM)

**Text frames (JSON control):**
```json
{"type": "end_of_speech"}         // Button released, process now
{"type": "reset"}                  // Clear conversation history
{"type": "ping"}                   // Keepalive
```

### 7.2 Bridge → ESP32

**Binary frames (audio):**
- Format: ADPCM compressed TTS output
- Chunking: 400 bytes per frame with 10ms delay between chunks (prevents buffer overflow)

**Text frames (JSON status):**
```json
{"type": "connected", "message": "AEGIS1 ready", "config": {...}}
{"type": "status", "state": "processing"|"speaking"|"idle"}
{"type": "done", "latency": {
  "vad_ms": 100,
  "stt_ms": 80,
  "llm_ms": 150,
  "tts_ms": 60,
  "total_ms": 390
}}
{"type": "error", "message": "STT failed: ...", "code": "STT_ERROR"}
```

## 8. ESP32 Firmware State Machine

```
         button press
  IDLE ──────────────> LISTENING
   ^                      │
   │                      │ Silero VAD detects end
   │                      │ (voice prob <0.5 for 10 chunks)
   │                      v
   │               PROCESSING
   │                      │
   │                      │ TTS audio received
   │                      v
   └──────────────── SPEAKING
         playback done
```

**LED patterns:**
- IDLE: Breathing (slow pulse, 2s cycle)
- LISTENING: Solid on (bright)
- PROCESSING: Fast pulse (200ms cycle)
- SPEAKING: Fast blink (100ms on/off)

## 9. Latency Targets & Measurement

### 9.1 Simple Query Path (Haiku, 80% of interactions)

| Stage | Target | Actual Measurement Point | Optimizations |
|-------|--------|--------------------------|---------------|
| ADPCM decompression | <5ms | Compressed frame → PCM buffer | Standard codec |
| Silero VAD | <1ms | Per 200ms chunk | Optimized PyTorch model |
| Moonshine STT | 80ms | Audio buffer → text string | Native streaming, 27M params |
| Claude Haiku TTFT | 150ms | Request sent → first token | Prompt caching on L1+L3 |
| Tool execution (if any) | 20ms | Tool call → JSON result | SQLite indexed queries |
| Kokoro TTS | 60ms | Text sentence → PCM audio | CPU ONNX inference |
| ADPCM compression | <5ms | PCM → compressed frame | Standard codec |
| **Perceived latency** | **440ms** | End of speech → first audio | **Target met** |

### 9.2 Complex Query Path (Opus parallel, 20% of interactions)

| Path | Latency | User Experience |
|------|---------|-----------------|
| Haiku quick ack | 440ms | "Let me analyze that..." (immediate) |
| Opus async deep | +2000ms | Detailed analysis (streamed later) |
| **Total perceived** | **440ms + 2.5s** | Feels natural (immediate ack, then thinking pause) |

### 9.3 Latency Tracking

**Per-stage timing** tracked in `main.py`:
```python
latency = {
    "vad_ms": end_silence - start_audio,
    "stt_ms": end_stt - end_silence,
    "llm_ms": end_llm - end_stt,
    "tts_ms": end_tts - end_llm,
    "codec_ms": (decompress_time + compress_time),
    "total_ms": end_tts - start_audio
}
```

**Exposed via API:**
- `GET /api/status` → JSON with last request latency
- `GET /health` → Overall system health + avg latency (last 10 requests)

## 10. Error Handling & Fallbacks

### 10.1 Component Fallback Chain

| Component | Primary | Fallback 1 | Fallback 2 |
|-----------|---------|------------|------------|
| STT | Moonshine Streaming Tiny | faster-whisper | Return error to user |
| TTS | Kokoro-82M | Piper | edge-tts (cloud) |
| VAD | Silero VAD | Naive RMS silence detection | N/A |
| LLM (simple) | Haiku 4.5 | Phi-3-mini (if Ollama running) | Return error |
| LLM (complex) | Opus 4.6 | Haiku 4.5 (degraded mode) | Return error |
| Memory | sqlite-vec semantic search | SQL text search (LIKE) | Skip memory, continue |

### 10.2 Error Recovery Patterns

**STT failure:**
```
Audio chunks received → Moonshine fails
    ↓
Fallback to faster-whisper
    ↓ (if also fails)
Return to ESP32: {"type": "error", "message": "I didn't catch that. Please try again."}
    ↓
TTS: "I didn't catch that. Please try again."
```

**Tool execution error:**
```
Claude calls tool → tool returns {"error": "Database locked"}
    ↓
Return tool_result to Claude with error
    ↓
Claude explains to user: "I couldn't save that right now. Let me try again."
    ↓
Retry tool call (max 3 retries)
```

**Extended thinking timeout:**
```
Opus running for >10 seconds
    ↓
Send Haiku fallback response: "This is taking longer than expected. Let me give you a quick summary..."
    ↓
Cancel Opus async task
```

## 11. Security & Privacy

**Data residency:** All data stored locally in SQLite (no cloud upload except Claude API calls)  
**API keys:** Stored in `.env` file (never committed to git)  
**Health data:** Apple Health import is one-way (no export back to Apple)  
**Conversation logs:** Optionally disabled via `STORE_CONVERSATIONS=false` env var  
**WebSocket:** No authentication in demo (single-user), but TLS/WSS supported for production

## 12. Critical Files Reference

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Main server | `aegis/main.py` | FastAPI app, WebSocket endpoint, pipeline orchestrator |
| Claude client | `aegis/claude_client.py` | Streaming, tool loop, model routing, extended thinking |
| STT | `aegis/stt.py` | Moonshine/faster-whisper wrapper, VAD integration |
| TTS | `aegis/tts.py` | Kokoro engine with sentence splitting |
| VAD | `aegis/vad.py` | Silero VAD wrapper, probability-based end detection |
| Audio codec | `aegis/audio.py` | ADPCM compression, PCM/WAV utils |
| Tool registry | `aegis/tools/registry.py` | Tool dispatch, schema validation |
| Health tools | `aegis/tools/health.py` | get_health_context, log_health, analyze_patterns |
| Wealth tools | `aegis/tools/wealth.py` | track_expense, spending_summary, savings_goal |
| Profile tool | `aegis/tools/profile.py` | save_user_insight |
| Health import | `aegis/health_import.py` | Apple Health XML parser, DB loader |
| Context builder | `aegis/context.py` | build_health_context() for dynamic system prompts |
| Database | `aegis/db.py` | Schema, seeder, query helpers |
| Config | `aegis/config.py` | Pydantic settings, env var loading |
| CLI entry | `aegis/__main__.py` | Subcommands: serve, terminal, import-health, seed |
