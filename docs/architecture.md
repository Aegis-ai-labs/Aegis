# AEGIS1 — System Architecture

## 1. System Overview

```
┌─────────────────┐     WebSocket (PCM)      ┌──────────────────────────────┐
│   ESP32 Pendant  │ <──────────────────────> │     Python Bridge Server     │
│                  │     Binary audio +        │         (FastAPI)            │
│  ┌──────────┐   │     JSON control msgs     │                              │
│  │ INMP441  │   │                           │  ┌─────────┐  ┌───────────┐ │
│  │  (Mic)   │───┤                           │  │  STT    │  │  Claude   │ │
│  └──────────┘   │                           │  │ faster- │──│   API     │ │
│  ┌──────────┐   │                           │  │ whisper │  │           │ │
│  │ PAM8403  │   │                           │  └─────────┘  │ ┌───────┐ │ │
│  │(Speaker) │<──┤                           │               │ │Haiku  │ │ │
│  └──────────┘   │                           │  ┌─────────┐  │ │4.5    │ │ │
│  ┌──────────┐   │                           │  │  TTS    │<─│ ├───────┤ │ │
│  │  LED     │   │                           │  │  Piper  │  │ │Opus   │ │ │
│  │  Button  │   │                           │  │ (local) │  │ │4.6    │ │ │
│  └──────────┘   │                           │  └─────────┘  │ └───────┘ │ │
└─────────────────┘                           │               │    |      │ │
                                              │               │ ┌───────┐ │ │
                                              │               │ │ Tools │ │ │
                                              │               │ │health │ │ │
                                              │               │ │wealth │ │ │
                                              │               │ └───────┘ │ │
                                              │               └───────────┘ │
                                              │                    |        │
                                              │              ┌──────────┐   │
                                              │              │  SQLite  │   │
                                              │              │  (data)  │   │
                                              │              └──────────┘   │
                                              └──────────────────────────────┘
```

## 2. Streaming Pipeline (Critical Path)

This is the latency-critical path. Every millisecond matters.

```
User speaks → ESP32 mic → PCM chunks (200ms) → WebSocket → Bridge
                                                              │
                                                              ▼
                                                    ┌──────────────┐
                                                    │ Silence Det. │ amplitude < 500
                                                    │ (8 chunks =  │ = 1.6s silence
                                                    │  end_of_speech)
                                                    └──────┬───────┘
                                                           ▼
                                                    ┌──────────────┐
                                                    │     STT      │ target: <300ms
                                                    │faster-whisper│ base model, beam=1
                                                    │  vad_filter  │
                                                    └──────┬───────┘
                                                           ▼
                                                    ┌──────────────┐
                                                    │   Claude     │ streaming response
                                                    │  Haiku 4.5   │ or Opus 4.6
                                                    │  + tool loop  │ (max 5 rounds)
                                                    └──────┬───────┘
                                                           ▼
                                                    ┌──────────────┐
                                                    │  Sentence    │ buffer until . ! ?
                                                    │  Buffer      │ then immediately:
                                                    └──────┬───────┘
                                                           ▼
                                                    ┌──────────────┐
                                                    │    TTS       │ target: <150ms
                                                    │   Piper      │ per sentence
                                                    └──────┬───────┘
                                                           ▼
                                                    WebSocket → ESP32 → Speaker
```

**Key insight:** TTS starts on the first sentence boundary, not after the full Claude response. While Piper synthesizes sentence 1, Claude is still generating sentence 2. This overlapping is what achieves <2s perceived latency.

## 3. Model Routing Strategy

| Complexity | Model | Thinking | Max Tokens | Use Case |
|-----------|-------|----------|------------|----------|
| Simple | Haiku 4.5 | None | 300 | Greetings, logging data, simple lookups |
| Complex | Opus 4.6 | Enabled (2048 budget) | 1024 | Pattern analysis, trends, financial planning |

**Routing triggers for Opus 4.6** (keyword matching in `claude_client.py`):
- Analysis: "analyze", "pattern", "trend", "correlat", "compare"
- Planning: "plan", "savings goal", "financial plan", "budget plan"
- Causation: "why am i", "why do i", "what's causing", "relationship between"
- Temporal: "over time"

**System prompt** (voice-optimized):
> You are Aegis, a voice health and wealth assistant worn as a pendant. You speak concisely — 1-2 sentences for simple queries, up to 4 for analysis. Use tools when the user asks about their data. Don't guess — look it up.

## 4. Tool Architecture

Six tools organized into two domains:

### Health Tools (`bridge/tools/health.py`)

| Tool | Parameters | Returns | Purpose |
|------|-----------|---------|---------|
| `get_health_context` | `days` (int, default 7), `metrics` (list[str], optional) | Grouped entries with avg/min/max per metric | "How did I sleep this week?" |
| `log_health` | `metric` (enum), `value` (number), `notes` (str) | Confirmation with logged values | "I slept 7 hours" |
| `analyze_health_patterns` | `query` (str), `days` (int, default 30) | Daily records for all metrics (raw data for Claude to analyze) | "Is my sleep correlated with exercise?" |

**Health metrics:** `sleep_hours`, `steps`, `heart_rate`, `mood`, `weight`, `water`, `exercise_minutes`

### Wealth Tools (`bridge/tools/wealth.py`)

| Tool | Parameters | Returns | Purpose |
|------|-----------|---------|---------|
| `track_expense` | `amount` (number), `category` (enum), `description` (str) | Confirmation + week total in category | "I spent $12 on lunch" |
| `get_spending_summary` | `days` (int, default 30), `category` (str, optional) | Total, daily avg, by-category breakdown, recent 5 | "How much did I spend this month?" |
| `calculate_savings_goal` | `target_amount` (number), `target_months` (int), `monthly_income` (number, optional) | Monthly needed, current spending, gap analysis | "How can I save $5000 in 6 months?" |

**Expense categories:** `food`, `transport`, `housing`, `health`, `entertainment`, `shopping`, `utilities`, `other`

### Tool Execution Flow

```
Claude response contains tool_use block
    │
    ├── registry.execute_tool(name, arguments)
    │       │
    │       ├── HANDLERS[name] → health.py or wealth.py function
    │       │
    │       └── Returns JSON string
    │
    ├── Tool result sent back to Claude as tool_result
    │
    └── Claude generates natural language response using tool data
        (loop continues for up to 5 rounds if Claude calls more tools)
```

## 5. Data Model (SQLite)

```sql
-- Health tracking
CREATE TABLE health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,           -- sleep_hours, steps, heart_rate, mood, weight, water, exercise_minutes
    value REAL NOT NULL,            -- numeric value
    notes TEXT DEFAULT '',          -- optional context
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_health_metric ON health_logs(metric, timestamp);

-- Expense tracking
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,           -- dollar amount
    category TEXT NOT NULL,         -- food, transport, housing, health, entertainment, shopping, utilities, other
    description TEXT DEFAULT '',    -- what was purchased
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_expense_cat ON expenses(category, timestamp);

-- Conversation history (for latency tracking and debugging)
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,             -- user or assistant
    content TEXT NOT NULL,
    model_used TEXT DEFAULT '',     -- which Claude model was used
    latency_ms REAL DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Demo data:** 30 days auto-seeded with `random.seed(42)` — sleep, steps, heart rate, mood, weight, water, exercise, and 1-3 daily expenses. Data has realistic patterns (worse sleep on weekdays, mood correlates with sleep, spending varies by category).

## 6. WebSocket Protocol

### ESP32 → Bridge
- **Binary frames:** Raw PCM audio (16kHz, 16-bit mono, ~6400 bytes per 200ms chunk)
- **Text frames (JSON):**
  - `{"type": "end_of_speech"}` — Button released, process immediately
  - `{"type": "reset"}` — Clear conversation history

### Bridge → ESP32
- **Binary frames:** TTS PCM audio (chunked at 6400 bytes with 10ms delay between chunks)
- **Text frames (JSON):**
  - `{"type": "connected", "message": "AEGIS1 ready", "config": {...}}`
  - `{"type": "status", "state": "processing"|"speaking"|"idle"}`
  - `{"type": "done", "latency": {"stt_ms": ..., "llm_ms": ..., "total_ms": ...}}`

## 7. ESP32 State Machine

```
         button press
  IDLE ──────────────> LISTENING
   ^                      │
   │                      │ silence detected / button release
   │                      v
   │               PROCESSING
   │                      │
   │                      │ audio received
   │                      v
   └──────────────── SPEAKING
         playback done
```

**LED patterns:**
- IDLE: Breathing (slow pulse)
- LISTENING: Solid on
- PROCESSING: Fast pulse
- SPEAKING: Fast blink

## 8. Latency Targets

| Stage | Target | Measurement Point |
|-------|--------|-------------------|
| STT (faster-whisper) | <300ms | Audio bytes → text string |
| Claude first token | <200ms | Request sent → first text chunk |
| TTS per sentence | <150ms | Text → PCM bytes |
| **Perceived latency** | **<750ms** | End of speech → first audio out |
| Full pipeline | <2.0s | End of speech → response complete |

Latency is tracked per-stage in `main.py` and exposed via `GET /api/status`.
