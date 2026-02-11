# AEGIS1 Architecture

## System Overview

```
┌─────────────────┐     WebSocket (PCM)      ┌──────────────────────────────┐
│   ESP32 Pendant  │ ◄──────────────────────► │     Python Bridge Server     │
│                  │     Binary audio +        │         (FastAPI)            │
│  ┌──────────┐   │     JSON control msgs     │                              │
│  │ INMP441  │   │                           │  ┌─────────┐  ┌───────────┐ │
│  │  (Mic)   │───┤                           │  │  STT    │  │  Claude   │ │
│  └──────────┘   │                           │  │ faster- │──│   API     │ │
│  ┌──────────┐   │                           │  │ whisper │  │           │ │
│  │ PAM8403  │   │                           │  └─────────┘  │ ┌───────┐ │ │
│  │(Speaker) │◄──┤                           │               │ │Haiku  │ │ │
│  └──────────┘   │                           │  ┌─────────┐  │ │4.5    │ │ │
│  ┌──────────┐   │                           │  │  TTS    │◄─│ ├───────┤ │ │
│  │  LED     │   │                           │  │  Piper  │  │ │Opus   │ │ │
│  │  Button  │   │                           │  │ (local) │  │ │4.6    │ │ │
│  └──────────┘   │                           │  └─────────┘  │ └───────┘ │ │
└─────────────────┘                           │               │    ↕      │ │
                                              │               │ ┌───────┐ │ │
                                              │               │ │ Tools │ │ │
                                              │               │ │health │ │ │
                                              │               │ │wealth │ │ │
                                              │               │ └───────┘ │ │
                                              │               └───────────┘ │
                                              │                    ↕        │
                                              │              ┌──────────┐   │
                                              │              │  SQLite  │   │
                                              │              │  (data)  │   │
                                              │              └──────────┘   │
                                              └──────────────────────────────┘
```

## Streaming Pipeline (Critical Path)

```
User speaks → ESP32 mic → PCM chunks → WebSocket → Bridge
                                                      │
                                                      ▼
                                              ┌──────────────┐
                                              │ Silence Det. │
                                              │ (end_of_speech)
                                              └──────┬───────┘
                                                     ▼
                                              ┌──────────────┐
                                              │     STT      │ ~250ms
                                              │faster-whisper│
                                              └──────┬───────┘
                                                     ▼
                                              ┌──────────────┐
                                              │   Claude     │ streaming
                                              │  (Haiku or   │
                                              │   Opus 4.6)  │──→ Tool calls
                                              └──────┬───────┘     (health/wealth)
                                                     ▼
                                              ┌──────────────┐
                                              │  Sentence    │ buffer until . ! ?
                                              │  Buffer      │
                                              └──────┬───────┘
                                                     ▼
                                              ┌──────────────┐
                                              │    TTS       │ ~100ms to first chunk
                                              │   Piper      │
                                              └──────┬───────┘
                                                     ▼
                                              WebSocket → ESP32 → Speaker
```

## Model Routing Strategy

| Complexity | Model | Thinking | Use Case |
|-----------|-------|----------|----------|
| Simple | Haiku 4.5 | None | Greetings, logging, simple lookups |
| Complex | Opus 4.6 | Adaptive | Pattern analysis, financial planning |

**Routing triggers for Opus 4.6:**
- Keywords: "analyze", "pattern", "trend", "plan", "correlat", "compare", "why"
- Health queries spanning >7 days
- Financial planning/savings goals

## Latency Targets

| Stage | Target | Method |
|-------|--------|--------|
| STT | <300ms | faster-whisper base, beam_size=1, vad_filter |
| Claude first token | <200ms | Haiku 4.5, streaming |
| TTS first chunk | <150ms | Piper local, streaming |
| **Perceived latency** | **<750ms** | Sentence-level streaming |
| Full pipeline | <2.0s | Parallel TTS while Claude continues |

## Tool Architecture

```
Claude API (with tool definitions)
    │
    ├── get_health_context(days, metrics)
    │       → SELECT from health_logs
    │
    ├── log_health(metric, value, notes)
    │       → INSERT into health_logs
    │
    ├── analyze_health_patterns(query, days)
    │       → SELECT + aggregate from health_logs
    │       → Returns raw data for Claude to analyze
    │
    ├── track_expense(amount, category, description)
    │       → INSERT into expenses
    │
    ├── get_spending_summary(days, category)
    │       → SELECT + aggregate from expenses
    │
    └── calculate_savings_goal(target_amount, target_months, monthly_income)
            → SELECT from expenses + compute projections
```

## Data Model (SQLite)

```sql
health_logs (id INTEGER PK, metric TEXT, value REAL, notes TEXT, timestamp DATETIME)
expenses    (id INTEGER PK, amount REAL, category TEXT, description TEXT, timestamp DATETIME)
conversations (id INTEGER PK, role TEXT, content TEXT, model TEXT, latency_ms REAL, timestamp DATETIME)
```

## ESP32 State Machine

```
         button press
  IDLE ──────────────► LISTENING
   ▲                      │
   │                      │ silence detected
   │                      ▼
   │               PROCESSING
   │                      │
   │                      │ audio received
   │                      ▼
   └──────────────── SPEAKING
         playback done
```

LED Patterns: breathing=IDLE, solid=LISTENING, pulse=PROCESSING, fast-blink=SPEAKING
