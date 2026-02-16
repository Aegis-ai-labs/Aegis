# Phase 1 Specification — Foundation (Fix & Verify)

**Goal:** Bridge server works end-to-end with streaming + tools in terminal. All imports fixed, dependencies installed, tests passing.  
**Timeline:** Day 3-4 (Feb 12-13)  
**Estimated:** 6 hours  
**Status:** In progress

---

## Scope

Phase 1 is about **fixing and verifying** existing code, not writing new features:

1. **Package rename**: `bridge/` → `aegis/` (portable system, not middleware)
2. **CLI entry point**: Create `aegis/__main__.py` for subcommands (serve, terminal, import-health, seed)
3. **Dependencies**: Install missing packages (moonshine-onnx, kokoro, silero-vad, sqlite-vec)
4. **Streaming**: Verify `aegis/claude_client.py` works with `messages.stream()` + tool loop
5. **Tool APIs**: Confirm all 7 tools return valid JSON

**Out of scope for Phase 1:**
- Health personalization (Phase 2)
- Audio pipeline optimization (Phase 3)
- Testing & demo (Phase 4)

---

## Component Specifications

### 1. Package Rename — `aegis/`

**Current state:** Code exists in `bridge/` directory with `bridge.*` imports throughout

**Required changes:**
- [ ] Rename directory: `mv bridge/ aegis/`
- [ ] Find/replace all imports:
  ```bash
  find . -type f -name "*.py" -exec sed -i '' 's/from bridge\./from aegis./g' {} +
  find . -type f -name "*.py" -exec sed -i '' 's/import bridge/import aegis/g' {} +
  ```
- [ ] Update references in documentation (if any stale references remain)

**Acceptance criteria:**
- ✅ No `bridge/` directory exists (renamed to `aegis/`)
- ✅ No `from bridge.` imports in codebase
- ✅ `python -c "from aegis.main import app; print('OK')"` succeeds

**Rationale:** "AEGIS" = portable system positioning. "Bridge" implies middleware, which undersells the product vision.

---

### 2. CLI Entry Point — `aegis/__main__.py`

**Required:** Command-line interface for all operations (not just running server)

**Implementation:**

```python
"""
AEGIS1 — Voice Health & Wealth Assistant

Command-line interface for server, testing, and data management.
"""
import click
from aegis.main import app
from aegis.db import init_db, seed_demo_data
import uvicorn

@click.group()
@click.version_option(version="0.1.0")
def main():
    """AEGIS1 — AI voice assistant for health & wealth tracking"""
    pass

@main.command()
@click.option('--host', default='0.0.0.0', help='Server bind address')
@click.option('--port', default=8000, help='Server port')
@click.option('--reload', is_flag=True, help='Enable auto-reload (dev mode)')
def serve(host: str, port: int, reload: bool):
    """Start WebSocket bridge server"""
    click.echo(f"Starting AEGIS1 server on {host}:{port}...")
    uvicorn.run("aegis.main:app", host=host, port=port, reload=reload)

@main.command()
def terminal():
    """Interactive terminal client (text-only testing)"""
    import asyncio
    import websockets
    import json
    
    async def client():
        uri = "ws://localhost:8000/ws/text"
        async with websockets.connect(uri) as ws:
            click.echo("Connected to AEGIS1. Type /quit to exit, /reset to clear history.")
            
            while True:
                user_input = input("You: ")
                if user_input == "/quit":
                    break
                if user_input == "/reset":
                    await ws.send(json.dumps({"type": "reset"}))
                    continue
                
                await ws.send(json.dumps({"text": user_input}))
                
                # Receive streaming response
                response_parts = []
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("done"):
                        break
                    if text := data.get("text"):
                        response_parts.append(text)
                        print(text, end="", flush=True)
                print()  # newline after response
    
    asyncio.run(client())

@main.command()
@click.argument('xml_path', type=click.Path(exists=True))
@click.option('--user-id', default=1, help='User ID to import data for')
def import_health(xml_path: str, user_id: int):
    """Import Apple Health XML export"""
    # Placeholder — implemented in Phase 2
    click.echo(f"Importing Apple Health data from {xml_path} for user {user_id}...")
    click.echo("⚠️  Not implemented yet (Phase 2). Using demo data for now.")

@main.command()
@click.option('--days', default=30, help='Days of demo data to generate')
@click.option('--force', is_flag=True, help='Overwrite existing data')
def seed(days: int, force: bool):
    """Seed database with demo health & expense data"""
    init_db()
    seed_demo_data(days=days, force=force)
    click.echo(f"✅ Seeded {days} days of demo data")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Start server
python -m aegis serve

# Terminal testing
python -m aegis terminal

# Seed demo data
python -m aegis seed --days 30

# Import Apple Health (Phase 2)
python -m aegis import-health ~/Downloads/export.xml

# Help
python -m aegis --help
```

**Acceptance criteria:**
- ✅ `python -m aegis --help` shows all commands
- ✅ `python -m aegis serve` starts FastAPI server
- ✅ `python -m aegis terminal` connects to WebSocket (if server running)
- ✅ `python -m aegis seed` populates database with demo data

---

### 3. Dependencies — `requirements.txt` + `pyproject.toml`

**Current state:** `aegis/requirements.txt` exists but missing Phase 3 dependencies

**Required additions:**

```txt
# Existing (Phase 1 working)
anthropic>=0.41.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic-settings>=2.6.0
websockets>=14.1
aiosqlite>=0.20.0

# Phase 3 additions (install in Phase 1 for early testing)
moonshine-onnx>=0.1.0       # STT (27M params, 5x faster)
kokoro>=0.4.0               # TTS (82M params, Apache 2.0)
silero-vad>=5.1             # VAD (<1ms)
sqlite-vec>=0.1.0           # Conversation memory
click>=8.1.0                # CLI framework
httpx>=0.27.0               # Ollama client (Phase 3)
lxml>=5.0.0                 # Apple Health XML parsing (Phase 2)
numpy>=2.0.0                # Audio processing
torch>=2.0.0                # Silero VAD dependency
onnxruntime>=1.19.0         # ONNX inference

# Fallbacks (optional)
faster-whisper>=1.0.0       # STT fallback
piper-tts>=1.2.0            # TTS fallback (archived but works)
```

**Optional: Create `pyproject.toml`** (Python 3.10+ requirement):

```toml
[project]
name = "aegis1"
version = "0.1.0"
description = "Voice health & wealth assistant powered by Claude Opus 4.6"
requires-python = ">=3.10"
dependencies = [
    "anthropic>=0.41.0",
    "fastapi>=0.115.0",
    # ... (copy from requirements.txt)
]

[project.scripts]
aegis = "aegis.__main__:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**Installation:**
```bash
# Option 1: pip install from requirements.txt
pip install -r aegis/requirements.txt

# Option 2: pip install as editable package (if pyproject.toml created)
pip install -e .

# Verify critical imports
python -c "import moonshine_onnx; print('Moonshine OK')"
python -c "import kokoro; print('Kokoro OK')"
python -c "from silero_vad import load_silero_vad; print('Silero OK')"
python -c "import sqlite_vec; print('sqlite-vec OK')"
```

**System dependencies:**
- **espeak-ng** (required for Kokoro phoneme support):
  ```bash
  # macOS
  brew install espeak-ng
  
  # Linux (Ubuntu/Debian)
  sudo apt-get install espeak-ng
  ```

**Acceptance criteria:**
- ✅ All packages install without errors
- ✅ Critical imports succeed (moonshine, kokoro, silero, sqlite-vec)
- ✅ espeak-ng installed (verify: `espeak-ng --version`)

---

### 4. Claude Streaming — `aegis/claude_client.py`

**Current state:** File exists with streaming implementation

**Verification checklist:**

- [ ] **Uses `messages.stream()`** (not `messages.create()` with manual streaming wrapper)
  ```python
  with client.messages.stream(
      model=model,
      max_tokens=max_tokens,
      messages=messages,
      tools=TOOL_DEFINITIONS,
      # ...
  ) as stream:
      for event in stream:
          # Process events
  ```

- [ ] **Sentence buffering** for TTS optimization:
  - Buffer tokens until sentence boundary (`. ! ?`)
  - Yield complete sentences (not individual tokens)
  - Prevents TTS from synthesizing mid-sentence

- [ ] **Tool use loop** (max 5 rounds):
  - Detect `tool_use` blocks in stream
  - Execute via `registry.execute_tool(name, arguments)`
  - Append `tool_result` to messages
  - Continue streaming until no more tool calls

- [ ] **Extended thinking** for Opus:
  ```python
  headers = {
      "anthropic-beta": "interleaved-thinking-2025-05-14"
  }
  # budget_tokens parameter:
  extra_body = {"budget_tokens": 10000}
  ```

- [ ] **Model routing**:
  - Default: Haiku 4.5 (`claude-haiku-4-5-20251001`)
  - Keywords → Opus 4.6: "analyze", "pattern", "why", "correlation", "plan"
  - Opus uses extended thinking

- [ ] **Conversation history**:
  - Capped at last 20 turns (40 messages)
  - Includes tool calls + results
  - `reset_conversation()` clears history

**Test vectors:**

| Input | Expected Model | Tool Calls | Response Check |
|-------|---------------|------------|----------------|
| "Hello" | Haiku | 0 | Greeting, <100 tokens |
| "How did I sleep this week?" | Haiku | 1 (get_health_context) | Mentions sleep data from last 7 days |
| "I spent $12 on lunch" | Haiku | 1 (track_expense) | Confirms expense logged |
| "Analyze my sleep patterns" | Opus | 2 (get_health_context, analyze_patterns) | Uses extended thinking, identifies trends |

**Acceptance criteria:**
- ✅ Streaming works (sentence-by-sentence, not token-by-token)
- ✅ Tool loop functional (queries database, returns data in response)
- ✅ Model routing correct (Haiku default, Opus for analysis)
- ✅ Extended thinking enabled for Opus (verify via logs or API response metadata)
- ✅ No import errors, no API errors

---

### 5. Tool APIs — `aegis/tools/*.py`

**Current state:** 6 tools implemented (3 health, 3 wealth)

**Phase 1 addition:** 7th tool for personalization

#### Existing Tools (Verify Only)

**Health tools** (`aegis/tools/health.py`):
1. `get_health_context(days: int = 7, metrics: list[str] | None = None) -> dict`
   - Returns: `{"data": {...}, "summary": {...}}`
   - Queries `user_health_logs` table
2. `log_health(metric: str, value: float, notes: str = "", timestamp: str | None = None) -> dict`
   - Returns: `{"status": "logged", "metric": metric, "value": value}`
   - Inserts into `user_health_logs`
3. `analyze_patterns(metric: str, days: int = 30) -> dict`
   - Returns: `{"data": [...], "insights": [...]}`
   - Daily records for specified metric

**Wealth tools** (`aegis/tools/wealth.py`):
4. `track_expense(amount: float, category: str, description: str = "", timestamp: str | None = None) -> dict`
   - Returns: `{"status": "logged", "week_total_in_category": ...}`
5. `spending_summary(days: int = 30, category: str | None = None) -> dict`
   - Returns: `{"total": ..., "daily_avg": ..., "by_category": {...}, "recent": [...]}`
6. `savings_goal(target_amount: float, target_months: int, current_savings: float = 0) -> dict`
   - Returns: `{"monthly_needed": ..., "current_spending": ..., "gap": ...}`

#### New Tool (Phase 1 Addition)

**Profile tool** (`aegis/tools/profile.py`):
7. `save_user_insight(key: str, value: str, category: str = "preference") -> dict`
   - Input:
     - `key`: Insight key (e.g., "dietary_restriction", "fitness_goal")
     - `value`: Insight value (e.g., "vegetarian", "run 5k")
     - `category`: One of ["preference", "goal", "constraint"]
   - Returns: `{"status": "saved", "key": key, "value": value}`
   - Inserts/updates `user_profile` table (UPSERT on conflict)
   - Use case: "Remember I'm vegetarian" → saves for future meal recommendations

**Implementation:**

```python
# aegis/tools/profile.py
from aegis.db import get_db

async def save_user_insight(key: str, value: str, category: str = "preference") -> dict:
    """
    Save user preference, goal, or constraint for personalization.
    
    Args:
        key: Insight key (e.g., "dietary_restriction", "fitness_goal")
        value: Insight value (e.g., "vegetarian", "run 5k")
        category: One of ["preference", "goal", "constraint"]
    
    Returns:
        {"status": "saved", "key": key, "value": value}
    """
    if category not in ["preference", "goal", "constraint"]:
        return {"error": f"Invalid category: {category}"}
    
    db = await get_db()
    await db.execute(
        """
        INSERT INTO user_profile (user_id, key, value, category)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(user_id, key) DO UPDATE SET
            value = excluded.value,
            category = excluded.category
        """,
        (key, value, category)
    )
    await db.commit()
    
    return {
        "status": "saved",
        "key": key,
        "value": value,
        "category": category
    }
```

**Update registry** (`aegis/tools/registry.py`):

```python
from aegis.tools.profile import save_user_insight

TOOL_DEFINITIONS = [
    # ... existing 6 tools ...
    {
        "name": "save_user_insight",
        "description": "Store user preferences, goals, or constraints for personalization. Use when user shares information about themselves that should be remembered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Insight key (e.g., 'dietary_restriction', 'fitness_goal')"},
                "value": {"type": "string", "description": "Insight value (e.g., 'vegetarian', 'run 5k')"},
                "category": {"type": "string", "enum": ["preference", "goal", "constraint"], "description": "Type of insight"}
            },
            "required": ["key", "value"]
        }
    }
]

HANDLERS = {
    # ... existing handlers ...
    "save_user_insight": save_user_insight
}
```

**Database schema update** (`aegis/db.py`):

```sql
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT NOT NULL,  -- preference, goal, constraint
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);
```

**Acceptance criteria:**
- ✅ All 7 tools return valid JSON (not Python dict, but JSON-serializable dict)
- ✅ Tool errors return `{"error": "..."}` format
- ✅ Database queries execute without errors
- ✅ `save_user_insight` UPSERT works (update on conflict)

---

## Verification Plan

### Step 1: Import Test

```bash
# Verify all imports work after package rename
python -c "
from aegis.main import app
from aegis.claude_client import ClaudeClient
from aegis.tools.registry import TOOL_DEFINITIONS, execute_tool
from aegis.tools.health import get_health_context, log_health, analyze_patterns
from aegis.tools.wealth import track_expense, spending_summary, savings_goal
from aegis.tools.profile import save_user_insight
print('✅ All imports OK')
"
```

### Step 2: CLI Test

```bash
# Test CLI commands
python -m aegis --help
python -m aegis serve --help
python -m aegis terminal --help
python -m aegis seed --help
python -m aegis import-health --help

# Seed database
python -m aegis seed --days 30
```

### Step 3: Tool Test

```python
# test_tools.py
import asyncio
from aegis.tools.registry import execute_tool

async def test_all_tools():
    # Test 1: Health context
    result = await execute_tool("get_health_context", {"days": 7})
    assert "data" in result or "error" in result
    print("✅ get_health_context")
    
    # Test 2: Log health
    result = await execute_tool("log_health", {
        "metric": "sleep_hours",
        "value": 7.5,
        "notes": "Good night"
    })
    assert result["status"] == "logged"
    print("✅ log_health")
    
    # Test 3: Analyze patterns
    result = await execute_tool("analyze_patterns", {
        "metric": "sleep_hours",
        "days": 14
    })
    assert "data" in result
    print("✅ analyze_patterns")
    
    # Test 4: Track expense
    result = await execute_tool("track_expense", {
        "amount": 12.50,
        "category": "food",
        "description": "Lunch"
    })
    assert result["status"] == "logged"
    print("✅ track_expense")
    
    # Test 5: Spending summary
    result = await execute_tool("spending_summary", {"days": 30})
    assert "total" in result
    print("✅ spending_summary")
    
    # Test 6: Savings goal
    result = await execute_tool("savings_goal", {
        "target_amount": 5000,
        "target_months": 6
    })
    assert "monthly_needed" in result
    print("✅ savings_goal")
    
    # Test 7: Save user insight
    result = await execute_tool("save_user_insight", {
        "key": "dietary_restriction",
        "value": "vegetarian",
        "category": "preference"
    })
    assert result["status"] == "saved"
    print("✅ save_user_insight")

asyncio.run(test_all_tools())
```

### Step 4: Claude Streaming Test

```python
# test_streaming.py
import asyncio
from aegis.claude_client import ClaudeClient

async def test_streaming():
    client = ClaudeClient()
    
    # Test 1: Simple query (Haiku)
    print("--- Test 1: Simple greeting ---")
    async for sentence in client.chat("Hello, how are you?"):
        print(sentence, end="", flush=True)
    print("\n")
    
    # Test 2: Health lookup (Haiku + tool)
    print("--- Test 2: Health lookup with tool ---")
    async for sentence in client.chat("How did I sleep this week?"):
        print(sentence, end="", flush=True)
    print("\n")
    
    # Test 3: Complex analysis (Opus + tool + extended thinking)
    print("--- Test 3: Complex analysis with Opus ---")
    async for sentence in client.chat("Analyze the relationship between my sleep and mood"):
        print(sentence, end="", flush=True)
    print("\n")
    
    print("✅ All streaming tests passed")

asyncio.run(test_streaming())
```

### Step 5: End-to-End Terminal Test

```bash
# Start server in one terminal
python -m aegis serve

# In another terminal, start terminal client
python -m aegis terminal

# Send test queries:
# User: "Hello"
# User: "How did I sleep this week?"
# User: "I spent $12 on lunch"
# User: "Analyze my sleep patterns"
# User: "Remember I'm vegetarian"
# User: "/reset"
# User: "/quit"
```

---

## Acceptance Criteria

### ✅ Phase 1 Complete When:

1. **Package rename**: No `bridge/` references, all imports use `aegis.*`
2. **CLI working**: `python -m aegis --help` shows all commands
3. **Dependencies installed**: All imports succeed (moonshine, kokoro, silero, sqlite-vec)
4. **Streaming verified**: Claude responds with tool data, sentence-level streaming
5. **7 tools working**: All tools return valid JSON, no errors
6. **Terminal test passes**: End-to-end query → streaming response → tool data → answer
7. **No blockers**: No import errors, API errors, or critical bugs

### 🚫 Not Required for Phase 1:

- ❌ Health personalization (dynamic system prompts) → Phase 2
- ❌ Apple Health XML import → Phase 2
- ❌ Audio pipeline optimization (Moonshine/Silero/Kokoro integration) → Phase 3
- ❌ Conversation memory (sqlite-vec) → Phase 3
- ❌ Local LLM routing (Phi-3-mini) → Phase 3
- ❌ ADPCM codec → Phase 3
- ❌ Comprehensive tests → Phase 4
- ❌ Demo video → Phase 4

---

## Time Estimate

| Task | Estimated Time |
|------|---------------|
| Package rename + import fixes | 1h |
| CLI entry point (`__main__.py`) | 1h |
| Install dependencies + verify imports | 1h |
| Verify Claude streaming + tool loop | 1.5h |
| Add 7th tool (save_user_insight) | 0.5h |
| End-to-end terminal testing | 1h |
| **Total** | **6h** |

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Import errors after rename | Low | Systematic sed, test after each change |
| Missing dependencies fail install | Low | Use pip install with --no-deps flag, install individually |
| Claude API quota exceeded | Low | Use test mode with cached responses |
| Tool errors in production | Medium | Comprehensive error handling, return `{"error": ...}` format |
| Terminal client connection fails | Low | Add retry logic with exponential backoff |

---

## Next Steps → Phase 2

After Phase 1 acceptance criteria met:
1. Implement **health context builder** (`aegis/context.py`)
2. Add **dynamic system prompt injection** (3-layer architecture)
3. Create **Apple Health XML import** (`aegis/health_import.py`)
4. Enrich **tool responses** with body-aware insights
5. Curate **3 demo scenarios** with realistic data
