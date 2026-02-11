# AEGIS1 — System Patterns

## Architecture Pattern: Pipeline Orchestrator

The bridge server follows a **linear pipeline with sentence-level streaming**:

```
Audio In → STT → Claude (streaming + tools) → Sentence Buffer → TTS → Audio Out
```

Each stage is a discrete component (`stt.py`, `claude_client.py`, `tts.py`) with the orchestrator (`main.py`) threading them together. The sentence buffer is the key innovation — TTS starts on the first complete sentence, not after the full LLM response.

## Async Pattern

- **FastAPI + asyncio** — The WebSocket handler is async, allowing concurrent connections
- **Claude client uses sync API with async wrapper** — `anthropic.Anthropic` (not `AsyncAnthropic`) because the tool use loop is sequential by nature
- **`async for` streaming** — `ClaudeClient.get_response()` is an `AsyncGenerator[str, None]` that yields text chunks
- **Per-connection state** — Each WebSocket gets its own `ClaudeClient` instance with conversation history

## Tool Dispatch Pattern

Tools follow a **registry pattern**:

1. `tools/registry.py` holds `TOOL_DEFINITIONS` (JSON schema for Claude) and `HANDLERS` (name → function map)
2. `execute_tool(name, arguments)` dispatches to the handler and returns JSON
3. Tool implementations in `tools/health.py` and `tools/wealth.py` are plain async functions that take keyword arguments
4. All tools return `dict`, serialized to JSON by the registry

The Claude client handles the tool loop: send message → receive tool_use blocks → execute → send results → repeat (max 5 rounds).

## Model Routing Pattern

```python
OPUS_TRIGGERS = ["analyze", "pattern", "trend", "plan", "correlat", ...]

def select_model(user_text: str) -> str:
    for trigger in OPUS_TRIGGERS:
        if trigger in text_lower:
            return opus_model
    return haiku_model
```

Simple keyword matching in `claude_client.py`. Opus gets extended thinking (`budget_tokens=2048`) and higher `max_tokens` (1024 vs 300).

## Configuration Pattern

- `pydantic-settings` `BaseSettings` class in `config.py`
- All config via environment variables (`.env` file)
- Singleton `settings = Settings()` imported everywhere
- Sensible defaults for all values except `ANTHROPIC_API_KEY`

## Database Pattern

- SQLite with WAL mode for concurrent reads
- `get_db()` returns a new connection each call (no connection pooling — fine for hackathon)
- Schema created on import (`init_db()` at module level)
- Demo data auto-seeded on import (`seed_demo_data()` at module level)
- `sqlite3.Row` factory for dict-like access

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `claude_client.py` |
| Classes | PascalCase | `ClaudeClient`, `TTSEngine`, `Settings` |
| Functions | snake_case | `get_health_context`, `select_model` |
| Constants | UPPER_SNAKE | `OPUS_TRIGGERS`, `TOOL_DEFINITIONS` |
| Config vars | snake_case (Python) / UPPER_SNAKE (.env) | `bridge_port` / `BRIDGE_PORT` |

## Error Handling

- **STT/TTS failures** — Return `None`, log warning, skip that stage
- **Tool errors** — Return JSON `{"error": "message"}` to Claude (Claude handles gracefully)
- **WebSocket errors** — Catch `WebSocketDisconnect`, clean up connection state
- **Import failures** — Graceful degradation (e.g., `FASTER_WHISPER_AVAILABLE` flag)
- **No silent swallowing** — All errors logged with `logger.error()` and `exc_info=True`

## File Organization

- One module per concern: `config`, `db`, `audio`, `stt`, `tts`, `claude_client`, `main`
- Tools in a sub-package: `tools/registry.py` + `tools/health.py` + `tools/wealth.py`
- No deep nesting — flat structure under `bridge/`
- Docs separate from code: `docs/` at project root

## Latency Measurement Pattern

Every pipeline stage is timed with `time.monotonic()`:
```python
start = time.monotonic()
# ... do work ...
ms = (time.monotonic() - start) * 1000
log_latency("stage_name", ms)
```

The `/api/status` endpoint exposes rolling stats (avg, min, max) for the last 100 measurements per stage.
