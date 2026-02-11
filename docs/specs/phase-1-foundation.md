# Phase 1 Specification — Foundation

**Goal:** Bridge server with Claude streaming + tools working in terminal
**Timeline:** Feb 12 (Day 1)
**Status:** Code written, verification pending

---

## Scope

Build the core bridge server that:
1. Accepts text input (terminal for now)
2. Routes to Claude Haiku or Opus based on query complexity
3. Executes health/wealth tools when Claude requests them
4. Streams text responses back

No audio, no WebSocket, no ESP32 — just the Claude + tools intelligence layer.

---

## Components

### 1. Configuration — `bridge/config.py`

**Implementation:** pydantic-settings `BaseSettings` with `.env` file loading.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `anthropic_api_key` | str | "" | Claude API key (required) |
| `claude_haiku_model` | str | "claude-haiku-4-5-20251001" | Fast model |
| `claude_opus_model` | str | "claude-opus-4-6" | Deep model |
| `claude_max_tokens` | int | 300 | Response limit (Haiku) |
| `bridge_host` | str | "0.0.0.0" | Server bind address |
| `bridge_port` | int | 8000 | Server port |
| `sample_rate` | int | 16000 | Audio sample rate |
| `channels` | int | 1 | Audio channels |
| `chunk_size_ms` | int | 200 | Audio chunk duration |
| `piper_model_path` | str | "" | Piper voice model |
| `piper_config_path` | str | "" | Piper config |
| `piper_tts_url` | str | "http://localhost:5000" | Piper server URL |
| `stt_model` | str | "base" | Whisper model size |
| `stt_device` | str | "cpu" | Compute device |
| `stt_language` | str | "en" | Recognition language |
| `db_path` | str | "aegis1.db" | Database file |
| `log_level` | str | "INFO" | Logging level |

**Acceptance criteria:** Settings load from `.env`, defaults work without `.env`.

### 2. Database — `bridge/db.py`

**Schema:** 3 tables with indexes.

```sql
health_logs (id, metric, value, notes, timestamp)  -- INDEX on (metric, timestamp)
expenses    (id, amount, category, description, timestamp)  -- INDEX on (category, timestamp)
conversations (id, role, content, model_used, latency_ms, timestamp)
```

**Functions:**
- `get_db()` → `sqlite3.Connection` (WAL mode, Row factory)
- `init_db()` → Creates tables + indexes (idempotent)
- `seed_demo_data(days=30)` → Seeds 30 days of data if empty

**Demo data spec (seed=42):**
Per day: sleep_hours (5.5-8.5, worse weekdays), steps (3000-12000), heart_rate (60-85), mood (1-5, correlates with sleep), weight (trending ~181 lbs), water (4-10 glasses), exercise_minutes (0-60, more weekends). Plus 1-3 random expenses from 10 templates.

**Acceptance criteria:** `init_db()` + `seed_demo_data()` run on import. Tables exist. Demo data is reproducible.

### 3. Tool Registry — `bridge/tools/registry.py`

**Exports:**
- `TOOL_DEFINITIONS` — List of 6 tool schemas (JSON for Claude API)
- `HANDLERS` — Dict mapping tool name → async handler function
- `execute_tool(name, arguments)` → JSON string result

**Acceptance criteria:** All 6 tools registered with correct schemas. Unknown tool returns error JSON.

### 4. Health Tools — `bridge/tools/health.py`

| Function | Input | Output | SQL |
|----------|-------|--------|-----|
| `get_health_context(days, metrics)` | days: int=7, metrics: list=None | Grouped entries with stats | SELECT with optional metric filter |
| `log_health(metric, value, notes)` | metric: enum, value: float, notes: str="" | `{"status": "logged", ...}` | INSERT |
| `analyze_health_patterns(query, days)` | query: str, days: int=30 | Daily records for all metrics | SELECT all, group by date |

**Acceptance criteria:** Each function returns dict, not JSON. Stats include avg/min/max per metric.

### 5. Wealth Tools — `bridge/tools/wealth.py`

| Function | Input | Output | SQL |
|----------|-------|--------|-----|
| `track_expense(amount, category, description)` | amount: float, category: enum, description: str="" | Confirmation + week total in category | INSERT + SELECT SUM |
| `get_spending_summary(days, category)` | days: int=30, category: str=None | Total, daily avg, by-category, recent 5 | SELECT with optional filter |
| `calculate_savings_goal(target_amount, target_months, monthly_income)` | target: float, months: int, income: float=None | Monthly needed, current spending, gap | SELECT SUM + compute |

**Acceptance criteria:** `track_expense` returns weekly context. `calculate_savings_goal` returns gap analysis when income provided.

### 6. Claude Client — `bridge/claude_client.py`

**Class:** `ClaudeClient`
- `__init__()` — Creates `anthropic.Anthropic` client, empty conversation history
- `reset_conversation()` — Clears history
- `get_response(user_text)` → `AsyncGenerator[str, None]` — Streams text chunks
- `get_full_response(user_text)` → `str` — Collects all chunks (for testing)

**Model routing:** `select_model(user_text)` — Keyword matching against `OPUS_TRIGGERS` list.

**Tool loop:** Up to 5 rounds. For each round:
1. Send messages to Claude with tool definitions
2. Process response: yield text blocks, collect tool_use blocks
3. If tool calls exist: execute via registry, append results, continue loop
4. If no tool calls: break

**Extended thinking:** Enabled for Opus only (`budget_tokens=2048`).

**Conversation management:** History capped at last 20 turns (40 messages).

**Acceptance criteria:**
- Simple query → Haiku, text response
- "Analyze my sleep patterns" → Opus with extended thinking
- "How much did I spend on food?" → tool call → data in response

---

## Verification Plan

```bash
# Terminal test script (Phase 1 verification)
cd bridge/
python -c "
import asyncio
from bridge.claude_client import ClaudeClient

async def test():
    client = ClaudeClient()

    # Test 1: Simple greeting (Haiku)
    print('--- Test 1: Simple greeting ---')
    response = await client.get_full_response('Hello, how are you?')
    print(response)

    # Test 2: Health lookup (Haiku + tool)
    print('--- Test 2: Health lookup ---')
    response = await client.get_full_response('How did I sleep this week?')
    print(response)

    # Test 3: Expense logging (Haiku + tool)
    print('--- Test 3: Expense logging ---')
    response = await client.get_full_response('I spent 12 dollars on lunch')
    print(response)

    # Test 4: Complex analysis (Opus + tool)
    print('--- Test 4: Complex analysis ---')
    response = await client.get_full_response('Analyze the relationship between my sleep and mood over time')
    print(response)

asyncio.run(test())
"
```
