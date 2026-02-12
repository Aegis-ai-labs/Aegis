# AEGIS1 — Implementation Plan (4-Phase Restructure)

**Date:** 2026-02-12 (Day 3 of Hackathon)  
**Status:** FINAL — Approved for execution  
**Branch:** `feat/project-config`  
**Source:** shiny-wondering-kitten.md (restructure plan) + sharded-baking-lark.md (edge-optimization plan)

---

## Executive Summary

Two approved plans running in parallel:

1. **Restructure Plan** (shiny-wondering-kitten.md): Package rename bridge→aegis, Python 3.10+, CLI, health personalization (~12h, 4 phases)
2. **Edge-Optimization Plan** (sharded-baking-lark.md): Moonshine STT, Kokoro TTS, Silero VAD, Phi-3 local, sqlite-vec, ADPCM (~20-26h)

This plan merges both into a single 4-phase execution roadmap prioritizing Phase 1-2 for demo readiness.

---

## Phase 1: Foundation (6h target) — FIX & VERIFY

**Goal:** Bridge server works end-to-end with streaming + tools in terminal. All imports fixed, tests passing.

### 1.1 Package Rename (bridge → aegis)

- [ ] **Systematic find/replace** across all files:
  ```bash
  find . -type f -name "*.py" -exec sed -i '' 's/from bridge\./from aegis./g' {} +
  find . -type f -name "*.py" -exec sed -i '' 's/import bridge/import aegis/g' {} +
  ```
- [ ] **Rename directory**: `mv bridge/ aegis/`
- [ ] **Update pyproject.toml** (create if missing):

  ```toml
  [project]
  name = "aegis1"
  version = "0.1.0"
  requires-python = ">=3.10"
  dependencies = [... from requirements.txt ...]

  [project.scripts]
  aegis = "aegis.__main__:main"
  ```

- [ ] **Verify imports**:
  ```bash
  python -c "from aegis.main import app; print('Imports OK')"
  ```

### 1.2 CLI Entry Point

- [ ] **Create `aegis/__main__.py`** with Click-based CLI:

  ```python
  import click

  @click.group()
  def main():
      """AEGIS1 — Voice health & wealth assistant"""
      pass

  @main.command()
  def serve():
      """Start WebSocket bridge server"""
      # uvicorn aegis.main:app

  @main.command()
  def terminal():
      """Interactive terminal client (text-only)"""
      # WebSocket client for testing

  @main.command()
  @click.argument('xml_path')
  def import_health(xml_path):
      """Import Apple Health XML export"""
      # from aegis.health_import import parse_and_load

  @main.command()
  def seed():
      """Seed database with demo data"""
      # from aegis.db import seed_demo_data
  ```

- [ ] **Test CLI**:
  ```bash
  python -m aegis --help
  python -m aegis serve  # Should start server
  ```

### 1.3 Fix Dependencies

- [ ] **Install missing packages**:
  ```bash
  pip install moonshine-onnx kokoro-onnx silero-vad sqlite-vec
  ```
- [ ] **Verify each loads**:
  ```bash
  python -c "import moonshine_onnx; print('Moonshine OK')"
  python -c "import kokoro; print('Kokoro OK')"
  # ... etc
  ```
- [ ] **Update requirements.txt** with pinned versions:
  ```
  moonshine-onnx>=0.1.0
  kokoro>=0.4.0
  silero-vad>=5.1
  sqlite-vec>=0.1.0
  click>=8.1.0
  ```

### 1.4 Test Claude Streaming

- [ ] **Verify `aegis/claude_client.py` streaming**:
  - Uses `messages.stream()` (not `messages.create()`)
  - Sentence buffering working (splits on `. ! ?`)
  - Tool use loop functional (max 5 rounds)
  - Extended thinking enabled for Opus (`interleaved-thinking-2025-05-14` beta, `budget_tokens=10000`)
- [ ] **Terminal test**:
  ```bash
  python -m aegis terminal
  # Send: "How did I sleep this week?"
  # Expect: Streaming response with tool-derived data
  ```

### 1.5 Verify Tool APIs

- [ ] **Test all 7 tools return valid JSON**:
  - Health: `get_health_context`, `log_health`, `analyze_patterns`
  - Wealth: `track_expense`, `spending_summary`, `savings_goal`
  - Profile: `save_user_insight`
- [ ] **Verify tool registry dispatch**:
  ```python
  from aegis.tools.registry import execute_tool
  result = execute_tool("get_health_context", {"days": 7})
  assert "data" in result or "error" in result
  ```

### 1.6 Phase 1 Acceptance Criteria

✅ All imports work (`from aegis.*`)  
✅ CLI runs: `python -m aegis --help`  
✅ Server starts: `python -m aegis serve`  
✅ Terminal test: Query → streaming response → tool data → answer  
✅ All 7 tools return valid JSON  
✅ No import errors, no missing dependencies

---

## Phase 2: Smart (4h target) — HEALTH PERSONALIZATION

**Goal:** Dynamic health-aware system prompts. Responses reference user's actual body data. Apple Health import working.

### 2.1 Health Context Builder

- [ ] **Create `aegis/context.py`**:
  ```python
  async def build_health_context(user_id: int, days: int = 7) -> str:
      """
      Generate dynamic health context for system prompt injection.
      Returns:
      User's recent health context (last 7 days):
      - Sleep: Avg 6.2 hours/night (target: 7+). Notable: 3 days <6 hours.
      - Steps: Avg 8,500/day (good). Lowest: 4,200 (Sunday).
      - Heart rate: Avg resting 68 bpm (healthy).
      - Weight: Stable at 165 lbs.
      Patterns: Sleep deprivation correlates with low step count next day.
      """
      # Query user_health_logs table
      # Compute: avg, min, max, trend, notable events per metric
      # Identify patterns (e.g., sleep < target for N days)
      # Return formatted string for system prompt
  ```
- [ ] **Test context generation**:
  ```python
  context = await build_health_context(user_id=1, days=7)
  assert "Sleep:" in context
  assert "steps" in context.lower()
  ```

### 2.2 Dynamic System Prompt Injection

- [ ] **Update `aegis/claude_client.py`** to use 3-layer prompt:

  ```python
  # Layer 1: Static cached persona
  system_prompt_1 = """
  You are AEGIS, a voice assistant for a health & wealth tracking pendant.
  Be concise (1-2 sentences), warm, actionable. Use present tense.
  """

  # Layer 2: Dynamic health context (regenerated every call)
  health_context = await build_health_context(user_id)
  system_prompt_2 = f"""
  {health_context}
  """

  # Layer 3: Static cached tool directives
  system_prompt_3 = """
  Available tools: get_health_context, log_health, analyze_patterns, ...
  Use tools to query/write data. Never hallucinate.
  """

  # Combine for Claude request
  system = [
      {"type": "text", "text": system_prompt_1, "cache_control": {"type": "ephemeral"}},
      {"type": "text", "text": system_prompt_2},  # No cache (fresh every call)
      {"type": "text", "text": system_prompt_3, "cache_control": {"type": "ephemeral"}},
  ]
  ```

- [ ] **Verify personalized responses**:
  ```bash
  # Seed user with poor sleep data (5 days <6h)
  python -m aegis terminal
  # Send: "How am I doing?"
  # Expect: "You've been sleeping less than usual this week..."
  ```

### 2.3 Apple Health XML Import

- [ ] **Create `aegis/health_import.py`**:

  ```python
  from lxml import etree

  async def parse_apple_health_xml(xml_path: str) -> dict:
      """
      Parse Apple Health export.xml, extract 5 quantitative types:
      - steps (HKQuantityTypeIdentifierStepCount)
      - heart_rate (HKQuantityTypeIdentifierHeartRate)
      - weight (HKQuantityTypeIdentifierBodyMass)
      - exercise_minutes (HKQuantityTypeIdentifierAppleExerciseTime)
      - sleep_hours (HKCategoryTypeIdentifierSleepAnalysis)

      Returns: {metric: [(timestamp, value), ...], ...}
      """
      tree = etree.parse(xml_path)
      records = {}
      # XPath queries for each type
      # Group by metric, deduplicate, validate ranges
      return records

  async def load_to_database(user_id: int, records: dict):
      """
      INSERT INTO user_health_logs (user_id, metric, value, timestamp)
      Deduplicate by (user_id, metric, timestamp) unique constraint
      """
      # Batch insert with conflict resolution
  ```

- [ ] **Wire into CLI**:
  ```python
  @main.command()
  @click.argument('xml_path')
  def import_health(xml_path):
      records = await parse_apple_health_xml(xml_path)
      await load_to_database(user_id=1, records=records)
      click.echo(f"Imported {sum(len(v) for v in records.values())} records")
  ```
- [ ] **Test with sample XML** (create mock if needed):
  ```bash
  python -m aegis import-health sample_export.xml
  # Verify: SELECT COUNT(*) FROM user_health_logs;
  ```

### 2.4 Tool Data Enrichment

- [ ] **Enhance tool responses** with body-aware context:
  ```python
  # In aegis/tools/health.py:
  async def get_health_context(days: int = 7) -> dict:
      data = await db.get_recent_health(days)
      # Add insights:
      insights = []
      if data["sleep_avg"] < 7.0:
          insights.append("Sleep below recommended 7+ hours")
      if data["steps_avg"] < 8000:
          insights.append("Step count below 10k daily goal")
      return {"data": data, "insights": insights}
  ```
- [ ] **Add realistic variance** to demo data:
  - Sleep: weekday 6-7h, weekend 7-9h, occasional insomnia (4-5h)
  - Steps: weekday 8-12k, weekend 4-6k
  - Heart rate: resting 60-75 bpm, occasional spikes
  - Weight: stable ±2 lbs, slow downtrend if "weight loss goal" in profile
  - Expenses: weekday $20-50, weekend $80-150, occasional large purchases

### 2.5 Demo Data Curation

- [ ] **Create 3 compelling demo scenarios** (`docs/demo-scenarios.md`):
  1. **Sleep Analysis**: User asks "Why am I tired?" → Claude analyzes 30-day sleep patterns, finds weekend sleep debt, recommends consistent bedtime
  2. **Spending Patterns**: "How much did I spend on food this month?" → Shows $450 food category, $15/day avg, identifies 3 expensive restaurant visits, suggests meal prep
  3. **Savings Goal**: "Save $5000 in 6 months" → Calculates $833/month needed, compares to current $600/month spending, proposes cuts (entertainment $150 → $50)
- [ ] **Seed database** with these scenarios:
  ```bash
  python -m aegis seed --scenario sleep_analysis
  python -m aegis seed --scenario spending_patterns
  python -m aegis seed --scenario savings_goal
  ```

### 2.6 Phase 2 Acceptance Criteria

✅ `build_health_context()` generates personalized health summary  
✅ Claude responses reference actual body data ("You've been sleeping less...")  
✅ Apple Health XML import working (test with real or mock export)  
✅ All tools enriched with insights  
✅ Demo data seeded with 3 compelling scenarios  
✅ Terminal test: "How am I doing?" → personalized, not generic

---

## Phase 3: Shine (4h target) — POLISH & OPTIMIZE

**Goal:** Conversation memory, optimized latency, polished UX. Target 440ms simple queries.

### 3.1 Conversation Memory (sqlite-vec)

- [ ] **Create `aegis/memory.py`**:

  ```python
  from sqlite_vec import load_extension

  class ConversationMemory:
      def __init__(self, db_path: str):
          conn = sqlite3.connect(db_path)
          conn.enable_load_extension(True)
          load_extension(conn, "vec0")
          # CREATE VIRTUAL TABLE conversation_memory USING vec0(...)

      async def store(self, user_id: int, role: str, content: str):
          """Store conversation turn with embedding"""
          embedding = await self.get_embedding(content)
          # INSERT INTO conversation_memory

      async def recall(self, user_id: int, query: str, limit: int = 5) -> list[dict]:
          """Cosine similarity search"""
          query_embedding = await self.get_embedding(query)
          # SELECT * FROM conversation_memory
          # WHERE vec_distance_cosine(embedding, ?) < 0.3
          # ORDER BY vec_distance_cosine(embedding, ?) LIMIT ?

      async def get_embedding(self, text: str) -> list[float]:
          """Get embedding from Anthropic API or local model"""
          # Use text-embedding-3-small (512 dims) or all-MiniLM-L6-v2 (384 dims)
  ```

- [ ] **Integrate into claude_client.py**:
  ```python
  # Before each request:
  relevant_history = await memory.recall(user_id, user_text, limit=3)
  if relevant_history:
      context_prompt = "Relevant past context:\n" + "\n".join(...)
      # Prepend to conversation history
  ```
- [ ] **Test memory recall**:
  ```bash
  # Terminal test:
  User: "I slept 7 hours"
  # (wait 5 turns)
  User: "What did I tell you about my sleep yesterday?"
  # Expect: Recalls "You said you slept 7 hours"
  ```

### 3.2 Latency Optimization

- [ ] **Add Silero VAD** (if not already in Phase 1):
  - **Create `aegis/vad.py`**:

    ```python
    import torch
    from silero_vad import load_silero_vad

    class SileroVAD:
        def __init__(self, threshold=0.5):
            self.model = load_silero_vad()
            self.threshold = threshold

        def is_speech(self, audio_chunk: np.ndarray) -> bool:
            """Returns True if voice detected"""
            prob = self.model(torch.from_numpy(audio_chunk), 16000).item()
            return prob > self.threshold
    ```

  - **Integrate into audio pipeline**: End recording when `is_speech() == False` for N consecutive chunks

- [ ] **Upgrade STT to Moonshine** (if not already in Phase 1):
  - Replace `faster-whisper` with `moonshine-onnx` in `aegis/stt.py`
  - Verify 5x speedup: Target 80ms (was ~300ms with faster-whisper)
- [ ] **Verify Kokoro TTS** (if not already in Phase 1):
  - Confirm `aegis/tts.py` uses `kokoro-onnx`, not Piper
  - Target 60ms per sentence
- [ ] **Add ADPCM codec**:
  - **Create `aegis/audio.py`**:

    ```python
    def encode_adpcm(pcm_data: bytes) -> bytes:
        """IMA ADPCM encoder (4x compression)"""
        # Standard IMA ADPCM algorithm

    def decode_adpcm(adpcm_data: bytes) -> bytes:
        """IMA ADPCM decoder"""
        # Standard IMA ADPCM algorithm
    ```

  - **Update WebSocket handlers** in `aegis/main.py`:
    - Receive: ADPCM binary frames → `decode_adpcm()` → PCM
    - Send: PCM → `encode_adpcm()` → ADPCM binary frames

- [ ] **Measure latency per stage**:
  ```python
  latency = {
      "vad_ms": ...,
      "stt_ms": ...,
      "llm_ms": ...,
      "tts_ms": ...,
      "total_ms": ...
  }
  ```
- [ ] **Target verification**:
  - Simple query (Haiku): <440ms total
  - Complex query (Opus parallel): 440ms ack + 2s deep analysis

### 3.3 Local LLM Integration (Phi-3-mini)

- [ ] **Create `aegis/local_llm.py`**:

  ```python
  import httpx

  class OllamaClient:
      def __init__(self, model="phi3:mini", url="http://localhost:11434"):
          self.model = model
          self.url = url

      async def generate(self, prompt: str) -> str:
          """Single response from local LLM"""
          async with httpx.AsyncClient() as client:
              resp = await client.post(f"{self.url}/api/generate", json={
                  "model": self.model,
                  "prompt": prompt,
                  "stream": False
              }, timeout=5.0)
              return resp.json()["response"]

      async def is_available(self) -> bool:
          """Health check"""
          try:
              async with httpx.AsyncClient() as client:
                  resp = await client.get(f"{self.url}/api/tags", timeout=2.0)
                  return resp.status_code == 200
          except:
              return False
  ```

- [ ] **Add simple intent router**:
  ```python
  # In aegis/claude_client.py or aegis/router.py:
  async def route_query(text: str) -> str:
      """Route to local LLM if simple, Claude if complex"""
      simple_keywords = ["hello", "hi", "thanks", "how much", "what's"]
      if any(kw in text.lower() for kw in simple_keywords):
          # Try local LLM first
          if await local_llm.is_available():
              return await local_llm.generate(text)
      # Fallback to Claude
      return await claude_client.chat(text)
  ```
- [ ] **Test Phi-3 routing**:

  ```bash
  # Ollama running: ollama serve
  # Terminal test:
  User: "Hi there"
  # Should route to Phi-3 (<200ms)

  User: "Analyze my sleep patterns"
  # Should route to Claude Opus (extended thinking)
  ```

### 3.4 Parallel Opus Pattern

- [ ] **Implement in `aegis/claude_client.py`**:

  ```python
  async def chat_with_parallel_opus(user_text: str):
      """
      If complex query:
      1. Haiku quick ack: "Let me analyze that..."
      2. Spawn async Opus deep analysis task
      3. Yield Haiku ack immediately
      4. Wait for Opus, then yield deep analysis
      """
      if is_complex_query(user_text):
          # Quick Haiku ack
          haiku_response = await self.chat_haiku("Acknowledge: " + user_text)
          yield haiku_response

          # Opus async
          opus_task = asyncio.create_task(self.chat_opus(user_text))
          opus_response = await opus_task
          yield opus_response
      else:
          # Standard Haiku
          async for chunk in self.chat_haiku(user_text):
              yield chunk
  ```

- [ ] **Verify parallel pattern**:
  ```bash
  # Terminal test:
  User: "Why am I always tired on Mondays?"
  # Should see:
  # 1. Immediate ack (~440ms): "Let me analyze your weekly patterns..."
  # 2. Deep analysis (~2-3s later): "Your Monday fatigue stems from..."
  ```

### 3.5 Phase 3 Acceptance Criteria

✅ Conversation memory working (recall past turns)  
✅ Silero VAD integrated (<1ms per chunk)  
✅ Moonshine STT integrated (~80ms, 5x faster)  
✅ Kokoro TTS verified (~60ms per sentence)  
✅ ADPCM codec working (4x compression)  
✅ Latency measured: Simple <440ms, Complex 440ms + 2s  
✅ Phi-3 local LLM routing (optional, graceful fallback if unavailable)  
✅ Parallel Opus pattern working (immediate ack + async deep analysis)

---

## Phase 4: Perfect (6h target) — TEST & DEMO

**Goal:** Comprehensive tests, edge case handling, demo rehearsal, video recording.

### 4.1 Write Tests

- [ ] **Unit tests** (`tests/test_*.py`):
  - `tests/test_tools.py` — All 7 tools return valid JSON
  - `tests/test_context.py` — Health context builder logic
  - `tests/test_vad.py` — Silero VAD speech detection
  - `tests/test_codec.py` — ADPCM encode/decode round-trip
  - `tests/test_memory.py` — sqlite-vec recall accuracy
- [ ] **Integration tests** (`tests/integration/`):
  - `test_claude_streaming.py` — Full tool use loop
  - `test_audio_pipeline.py` — Audio → text → audio (mocked)
  - `test_health_import.py` — Apple Health XML parsing
- [ ] **Coverage target**: 70%+ on critical paths (tools, claude_client, context)
- [ ] **Run tests**:
  ```bash
  pytest tests/ --cov=aegis --cov-report=html
  ```

### 4.2 Edge Case Handling

- [ ] **Error recovery**:
  - [ ] STT timeout → fallback to faster-whisper
  - [ ] TTS failure → fallback to Piper or edge-tts
  - [ ] Claude API error → retry with exponential backoff
  - [ ] Tool error → return error JSON, Claude explains to user
  - [ ] WebSocket disconnect → auto-reconnect with backoff
- [ ] **Graceful degradation**:
  - [ ] Ollama not running → route all to Claude (no local LLM)
  - [ ] Memory DB locked → skip memory recall, log warning
  - [ ] Extended thinking timeout → cancel task, return Haiku fallback
- [ ] **Input validation**:
  - [ ] Tool parameters validated against JSON schema
  - [ ] Health metrics validated (e.g., sleep 0-24h, weight >0)
  - [ ] Expense amounts validated (>0, <$100k)

### 4.3 Demo Preparation

- [ ] **Rehearse 3 demo scenarios** 5 times each:
  1. Sleep analysis ("Why am I tired?")
  2. Spending patterns ("How much on food this month?")
  3. Savings goal ("Save $5000 in 6 months")
- [ ] **Timing**:
  - Each scenario: 30-45 seconds
  - Total demo: 2-3 minutes
- [ ] **Script** (`docs/demo-script.md`):

  ```markdown
  # AEGIS1 Demo Script

  ## Scenario 1: Sleep Analysis (45s)

  [Show pendant] "This is AEGIS1, my voice health assistant."
  [Press button] "Why am I always tired on Mondays?"
  [Wait for response] "Notice the immediate ack, then Opus deep analysis..."
  [Highlight] "Claude knows my actual sleep patterns from my data."

  ## Scenario 2: Spending Patterns (40s)

  [Press button] "How much did I spend on food this month?"
  [Show tool call] "Claude queries the database with get_spending_summary..."
  [Highlight] "Personalized insights: identifies my restaurant habit."

  ## Scenario 3: Savings Goal (45s)

  [Press button] "Help me save $5000 in 6 months."
  [Show extended thinking] "Opus reasoning about my spending patterns..."
  [Highlight] "Actionable plan: cut entertainment, increase monthly savings."
  ```

- [ ] **Backup plan**: Pre-record demo video if live demo risks too high

### 4.4 Documentation Polish

- [ ] **Update `README.md`**:
  - Project overview
  - Quick start (installation, setup)
  - Architecture diagram (link to docs/architecture.md)
  - Demo video link
  - Judging criteria alignment (Impact, Opus 4.6 Use, Depth, Demo)
- [ ] **Verify all docs updated**:
  - [x] MEMORY.md
  - [x] docs/memory-bank/projectbrief.md
  - [x] docs/memory-bank/techcontext.md
  - [x] docs/memory-bank/systempatterns.md
  - [x] docs/memory-bank/activecontext.md
  - [x] docs/memory-bank/progress.md
  - [x] docs/research.md
  - [x] docs/architecture.md
  - [x] docs/plan.md
  - [ ] docs/specs/phase-1-foundation.md
  - [ ] docs/specs/phase-2-smart.md (rename from phase-2-audio-pipeline.md)
- [ ] **Create `docs/demo-video-outline.md`**:
  - Intro (10s): "AEGIS1 — Voice health & wealth assistant powered by Claude Opus 4.6"
  - Problem (15s): "Tracking health & spending has too much friction"
  - Solution (30s): "Voice-first pendant, body-aware AI, instant insights"
  - Demo (90s): 3 scenarios back-to-back
  - Technical showcase (20s): "Extended thinking, streaming, 440ms latency"
  - Impact (15s): "Targets ages 30-65, eliminates friction fatigue"

### 4.5 Record Demo Video

- [ ] **Setup**:
  - Clean background
  - Good lighting
  - ESP32 pendant visible
  - Screen recording for Claude interactions
- [ ] **Record**:
  - 3 takes minimum
  - Best take: clear audio, no errors, <3 minutes
- [ ] **Edit** (optional):
  - Captions for key moments
  - Highlight extended thinking
  - Overlay latency numbers
- [ ] **Upload**:
  - YouTube (unlisted or public)
  - Add to README.md

### 4.6 Final Submission

- [ ] **GitHub**:
  - Push all code to `main` branch
  - Tag release: `v0.1.0-hackathon`
  - Public repository
- [ ] **Hackathon submission**:
  - Project title: "AEGIS1 — Voice Health & Wealth Assistant"
  - GitHub link
  - Demo video link
  - Description (200 words):

    ```
    AEGIS1 is a voice-first health & wealth tracking pendant that eliminates
    friction fatigue. Press a button, speak naturally, and get instant insights
    about your body and finances — powered by Claude Opus 4.6.

    Key innovations:
    - Body-aware AI: Dynamic system prompts inject your actual health context,
      making responses personalized (not generic)
    - Extended thinking showcase: Opus analyzes complex health correlations
      with 10k token reasoning budget
    - 440ms perceived latency: Moonshine STT, Kokoro TTS, Silero VAD, ADPCM
      codec, parallel Opus pattern (Haiku ack + async Opus deep analysis)
    - 7 specialized tools: Real database queries, not hallucinated data
    - Apple Health integration: One-time XML import, Claude always knows your
      current state

    Target demographic: Ages 30-65 with health awareness & disposable income.
    Addresses: "I download health apps, use them 2 weeks, then abandon."

    Tech stack: ESP32 pendant (mic/speaker/button), Python FastAPI bridge,
    Anthropic Claude API (Haiku 4.5 + Opus 4.6), local TTS/STT, sqlite-vec memory.
    ```

### 4.7 Phase 4 Acceptance Criteria

✅ Test suite: 70%+ coverage, all passing  
✅ Edge cases handled: STT/TTS/API failures gracefully degraded  
✅ Demo rehearsed 5x: No failures, <3 min runtime  
✅ Demo video recorded: Clear audio, showcases extended thinking  
✅ All documentation updated: README, architecture, specs  
✅ GitHub pushed: Public repo, tagged release  
✅ Hackathon submitted: Project link + demo video + description

---

## Critical Files Reference

| Component      | File Path                 | Status     | Phase   |
| -------------- | ------------------------- | ---------- | ------- |
| Main server    | `aegis/main.py`           | ✅ Done    | Phase 1 |
| Claude client  | `aegis/claude_client.py`  | ✅ Done    | Phase 1 |
| Config         | `aegis/config.py`         | ✅ Done    | Phase 1 |
| Database       | `aegis/db.py`             | ✅ Done    | Phase 1 |
| Tool registry  | `aegis/tools/registry.py` | ✅ Done    | Phase 1 |
| Health tools   | `aegis/tools/health.py`   | ✅ Done    | Phase 1 |
| Wealth tools   | `aegis/tools/wealth.py`   | ✅ Done    | Phase 1 |
| Profile tool   | `aegis/tools/profile.py`  | ⏳ Planned | Phase 2 |
| CLI entry      | `aegis/__main__.py`       | ⏳ Planned | Phase 1 |
| Health context | `aegis/context.py`        | ⏳ Planned | Phase 2 |
| Health import  | `aegis/health_import.py`  | ⏳ Planned | Phase 2 |
| STT            | `aegis/stt.py`            | ⚠️ Partial | Phase 3 |
| TTS            | `aegis/tts.py`            | ⚠️ Partial | Phase 3 |
| VAD            | `aegis/vad.py`            | ⏳ Planned | Phase 3 |
| Audio codec    | `aegis/audio.py`          | ⏳ Planned | Phase 3 |
| Memory         | `aegis/memory.py`         | ⏳ Planned | Phase 3 |
| Local LLM      | `aegis/local_llm.py`      | ⏳ Planned | Phase 3 |

**Legend:**

- ✅ Done: Working, tested
- ⚠️ Partial: Exists but needs updates (e.g., STT uses faster-whisper, needs Moonshine)
- ⏳ Planned: Not yet implemented

---

## Decision Log

| Date   | Decision                          | Rationale                                                          |
| ------ | --------------------------------- | ------------------------------------------------------------------ |
| Feb 12 | Package rename: bridge→aegis      | "Portable system" positioning, not middleware                      |
| Feb 12 | Python 3.10+ (was 3.9)            | Kokoro TTS requirement (breaking change)                           |
| Feb 12 | Direct Anthropic SDK (no Pipecat) | Fastest implementation, lowest latency, best Opus showcase         |
| Feb 12 | Moonshine Streaming Tiny STT      | 27M params, 26MB, MIT, 5x faster, native streaming                 |
| Feb 12 | Kokoro-82M TTS                    | 82M params, Apache 2.0, Piper archived Oct 2025                    |
| Feb 12 | Silero VAD                        | <1ms, replaces naive silence counting                              |
| Feb 12 | Phi-3-mini via Ollama             | <200ms simple queries, offloads Haiku                              |
| Feb 12 | sqlite-vec memory                 | <50ms cosine search, embedded, no API dependency                   |
| Feb 12 | ADPCM audio codec                 | 4x compression, minimal loss, simple implementation                |
| Feb 12 | 7 tools (3H, 3W, 1P)              | Quality over quantity, focused demo                                |
| Feb 12 | Parallel Opus pattern             | Haiku quick ack + async Opus deep analysis                         |
| Feb 12 | Dynamic health system prompts     | 3-layer injection (static cached + dynamic health + static tools)  |
| Feb 12 | Apple Health XML import           | Real user data, one-time CLI import                                |
| Feb 12 | 4-phase structure (not 6)         | Simplified from edge-optimization plan, prioritizes demo readiness |

---

## Risk Mitigation

| Risk                               | Probability | Impact | Mitigation                                                       |
| ---------------------------------- | ----------- | ------ | ---------------------------------------------------------------- |
| Time constraint (26h work, 4 days) | Medium      | High   | Phase 3 can be simplified (skip memory/local LLM if needed)      |
| Package rename breakage            | Low         | Medium | Systematic sed, test after rename, revert if critical issues     |
| Moonshine quality issues           | Medium      | Medium | Keep faster-whisper fallback, upgrade to Base (61M) if needed    |
| Kokoro setup complexity            | Low         | Medium | Fallback to Piper (still works despite archive), edge-tts backup |
| Apple Health XML parsing           | Medium      | Low    | Use mock data if real export unavailable, focus on architecture  |
| Phi-3 too slow / unavailable       | Low         | Low    | Graceful fallback to all-Claude routing                          |
| sqlite-vec setup issues            | Low         | Low    | Fallback to plain SQLite JSON search                             |
| ADPCM quality loss                 | Low         | Medium | Test early, revert to raw PCM if unacceptable                    |
| Demo video recording issues        | Medium      | Medium | Record backup video early, rehearse 5x before final take         |

---

## Existing Code (Do Not Recreate)

**Already working:**

- `aegis/config.py` — Pydantic settings (needs v2 updates in Phase 1)
- `aegis/db.py` — SQLite schema, CRUD, demo seeding (complete)
- `aegis/claude_client.py` — Streaming, tool loop, extended thinking (complete)
- `aegis/tools/registry.py` — Tool dispatch (complete)
- `aegis/tools/health.py` — 3 health tools (complete)
- `aegis/tools/wealth.py` — 3 wealth tools (complete)
- `aegis/main.py` — FastAPI server, WebSocket (needs CLI + imports update)
- `aegis/requirements.txt` — Dependencies (needs v2 additions)
- `aegis/.env.example` — Env template (needs v2 additions)
- `firmware/src/main.cpp` — ESP32 firmware (tested working, needs Phase 4 ADPCM updates)

**Database schema** (in `aegis/db.py`):

- `users` — User profiles
- `user_health_logs` — Health metrics (sleep, steps, heart_rate, weight, exercise_minutes)
- `user_expenses` — Expense tracking (amount, category, description, timestamp)
- Demo data: 30 days auto-seeded with `random.seed(42)`

---

## Next Actions (Priority Order)

1. **Fix imports** (bridge→aegis) — Blocking all testing
2. **Create `aegis/__main__.py`** — Enables CLI testing
3. **Install missing dependencies** — Unblocks component testing
4. **Terminal test** — Phase 1 verification milestone
5. **Implement `aegis/context.py`** — Phase 2 start (health personalization)
6. **Implement `aegis/health_import.py`** — Phase 2 Apple Health import
7. **Integrate Moonshine/Silero/Kokoro** — Phase 3 latency optimization
8. **Write tests** — Phase 4 verification
9. **Rehearse demo** — Phase 4 preparation
10. **Record video + submit** — Phase 4 delivery
