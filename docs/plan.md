# AEGIS1 — Edge-Optimized Architecture v2 Plan

**Date:** 2026-02-12 (Day 3 of Hackathon)
**Status:** FINAL — Approved for parallel implementation (Boris strategy)
**Branch:** `feat/project-config`

---

## Boris Parallel Session Strategy

Each phase is **self-contained** and can be implemented by an independent Claude session.
Sessions 1-3 can run in parallel. Session 4 depends on 1+2+3. Session 5 depends on 4.

| Session | Phase                       | Hours | Can Start Immediately |
| ------- | --------------------------- | ----- | --------------------- |
| Tab 1   | Phase 1: Core Bridge        | 4-5h  | YES                   |
| Tab 2   | Phase 2: Audio Pipeline     | 4-5h  | YES                   |
| Tab 3   | Phase 3: Local LLM + Memory | 3-4h  | YES                   |
| Tab 4   | Phase 4: ESP32 Integration  | 4-5h  | After 1+2+3           |
| Tab 5   | Phase 5+6: Demo + Docs      | 3-4h  | After 4               |

---

## Architecture: AEGIS1 v2

```
ESP32 Pendant                    Mac Mini Bridge                    Cloud
┌─────────────┐     WebSocket    ┌──────────────────┐              ┌─────────┐
│ INMP441 Mic │───── ADPCM ─────▶│ Silero VAD       │              │         │
│ Button PTT  │     (4x compress)│ Moonshine STT    │── simple ──▶│ Phi-3   │
│             │                  │ Intent Router    │              │ (local) │
│ PAM8403 Spk │◀──── ADPCM ──────│ Kokoro TTS       │── complex ─▶│ Claude  │
│ LED Status  │     (4x compress)│ sqlite-vec Memory│              │ Opus4.6 │
│ GPIO2 LED   │                  │ Tool Executor    │              │         │
└─────────────┘                  └──────────────────┘              └─────────┘
```

### Technology Stack (v2 swaps)

| Component     | Old                     | New                                  | Latency Gain |
| ------------- | ----------------------- | ------------------------------------ | ------------ |
| STT           | faster-whisper (~300ms) | **Moonshine Streaming Tiny** (~60ms) | 5x           |
| TTS           | Piper (~200ms)          | **Kokoro-82M** (~50ms)               | 4x           |
| VAD           | Naive silence counting  | **Silero VAD** (<1ms)                | 100x         |
| Memory        | None                    | **sqlite-vec** (<50ms)               | New          |
| Tools         | Placeholder             | **Direct DB calls** (<50ms)          | 30-60x       |
| LLM (simple)  | Claude Haiku (800ms)    | **Phi-3-mini local** (<200ms)        | 4x           |
| LLM (complex) | Claude Opus (1500ms)    | Claude Opus (unchanged)              | —            |
| Audio codec   | Raw PCM (256kbps)       | **ADPCM** (64kbps)                   | 4x less data |

### Latency Budget

| Stage               | v1          | v2 Target           |
| ------------------- | ----------- | ------------------- |
| ESP32 → Bridge      | 50ms        | 30ms (ADPCM)        |
| VAD                 | ~100ms      | <1ms (Silero)       |
| STT                 | ~300ms      | ~60ms (Moonshine)   |
| Intent Route        | N/A         | <20ms               |
| LLM (simple)        | 800ms       | <200ms (Phi-3)      |
| LLM (complex)       | 1500ms      | 800-1500ms (Claude) |
| Tool Exec           | 1500-3000ms | <50ms (direct DB)   |
| TTS                 | ~200ms      | ~50ms (Kokoro)      |
| Bridge → ESP32      | 50ms        | 30ms (ADPCM)        |
| **Total (simple)**  | **~3s**     | **~440ms**          |
| **Total (complex)** | **~3.6s**   | **~1040ms**         |

---

## Phase 1: Core Bridge (Tab 1)

**Goal:** Text query → Claude streaming + tool calls → text response
**Existing files:** `bridge/config.py`, `bridge/db.py`, `bridge/requirements.txt`, `bridge/.env.example`

### Step 1.1: Package inits

- [ ] Create `bridge/__init__.py` — Package docstring only
- [ ] Create `bridge/tools/__init__.py` — Re-export `TOOL_DEFINITIONS`, `dispatch_tool`

### Step 1.2: Health tools

- [ ] Create `bridge/tools/health.py`
  - `log_health(sleep_hours, steps, heart_rate, mood, notes, date)` → calls `db.log_health()`
  - `get_health_today()` → calls `db.get_health_by_date(today)`
  - `get_health_summary(days=7)` → calls `db.get_recent_health()`, computes averages
  - All functions return `dict` with `status` field
  - All use `await get_db()` from `bridge.db`

### Step 1.3: Wealth tools

- [ ] Create `bridge/tools/wealth.py`
  - `track_expense(amount, category, description, date)` → calls `db.track_expense()`
  - `get_spending_today()` → calls `db.get_expenses_by_date(today)`
  - `get_spending_summary(days=30)` → calls `db.get_spending_by_category()`
  - `get_budget_status(monthly_budget=3000)` → computes remaining/daily allowance
  - All return `dict`, all async, all use `get_db()`

### Step 1.4: Tool registry

- [ ] Create `bridge/tools/registry.py`
  - `TOOL_DEFINITIONS: list[dict]` — Anthropic API format (name, description, input_schema)
  - 7 tools: log_health, get_health_today, get_health_summary, track_expense, get_spending_today, get_spending_summary, get_budget_status
  - `_HANDLERS: dict[str, Callable]` — Maps tool name → async function
  - `dispatch_tool(tool_name, tool_input) -> str` — JSON result string

### Step 1.5: Claude client

- [ ] Create `bridge/claude_client.py`
  - `ClaudeClient` class with:
    - `conversation_history: list[dict]` — Last 20 turns
    - `SYSTEM_PROMPT` — Voice-tuned (2-3 sentence max, natural, use tools)
    - `async chat(user_text) -> AsyncGenerator[str, None]` — Yields sentence chunks
    - Tool use loop: max 5 rounds of tool calls
    - Uses `anthropic.AsyncAnthropic` with streaming (`messages.stream()`)
    - Sentence splitting via regex (`[.!?]+\s*`)
    - `async reset()` — Clears history
  - Model: `settings.claude_opus_model` (router will override in Phase 3)

### Step 1.6: FastAPI entry point

- [ ] Create `bridge/main.py`
  - `lifespan()` — Init DB on startup, close on shutdown
  - `GET /health` — Health check endpoint
  - `WS /ws/text` — Text-only WebSocket for testing:
    - Client sends: `{"text": "user message"}`
    - Server streams: `{"text": "sentence", "done": false}` per sentence
    - Final: `{"text": "", "done": true}`
    - `/reset` command clears conversation
  - `WS /ws/audio` — Audio WebSocket (stub for Phase 2):
    - Accept binary frames, JSON control frames
    - Return "not implemented" until Phase 2 wires it
  - `main()` function: `uvicorn.run("bridge.main:app", ...)`

### Step 1.7: Update config.py

- [ ] Update `bridge/config.py` — Add new v2 settings:
  - `stt_engine: str = "moonshine"` — "moonshine" | "faster-whisper"
  - `stt_model: str = "moonshine/tiny"`
  - `tts_engine: str = "kokoro"` — "kokoro" | "piper"
  - `tts_kokoro_voice: str = "af_heart"`
  - `tts_piper_model: str = "en_US-lessac-medium"`
  - `vad_threshold: float = 0.5`
  - `vad_min_speech_ms: int = 250`
  - `vad_silence_ms: int = 700`
  - `local_llm_enabled: bool = True`
  - `local_llm_model: str = "phi3:mini"`
  - `local_llm_url: str = "http://localhost:11434"`
  - `router_complexity_threshold: float = 0.5`
  - `memory_enabled: bool = True`
  - `memory_db_path: str = "aegis1_memory.db"`
  - `use_adpcm: bool = True`
  - Remove: `silence_threshold`, `silence_chunks_to_stop`, `stt_device`, `stt_beam_size`, `tts_model`, `tts_speaker_id`

### Verification

```bash
# Install deps
pip install -e . || pip install -r bridge/requirements.txt

# Import test
python -c "from bridge.main import app; print('Phase 1 OK')"

# Run server
python -m bridge.main
# In another terminal, test with wscat or Python:
# wscat -c ws://localhost:8000/ws/text
# Send: {"text": "How did I sleep this week?"}
# Expect: streamed sentence chunks with tool-derived data
```

---

## Phase 2: Audio Pipeline (Tab 2)

**Goal:** Audio file → full pipeline → audio file output, latency < 500ms
**Dependencies:** None (can work standalone, integrates into main.py later)

### Step 2.1: ADPCM codec

- [ ] Create `bridge/audio.py`
  - `encode_adpcm(pcm_data: bytes) -> bytes` — IMA ADPCM encoder (4x compression)
  - `decode_adpcm(adpcm_data: bytes) -> bytes` — IMA ADPCM decoder
  - `pcm_to_float32(pcm_data: bytes) -> np.ndarray` — 16-bit PCM to float32
  - `float32_to_pcm(audio: np.ndarray) -> bytes` — float32 to 16-bit PCM
  - Use `struct` + numpy, no external deps needed for ADPCM
  - Constants: `SAMPLE_RATE = 16000`, `CHANNELS = 1`, `SAMPLE_WIDTH = 2`

### Step 2.2: Silero VAD

- [ ] Create `bridge/vad.py`
  - `SileroVAD` class:
    - `__init__(threshold, min_speech_ms, silence_ms)` — Load Silero model
    - `process_chunk(audio_chunk: np.ndarray) -> VADEvent` — Returns SPEECH_START, SPEECH_END, or SPEECH_CONTINUE
    - `reset()` — Clear internal state
  - Load via `torch.hub.load('snakers4/silero-vad', 'silero_vad')` or `silero-vad` pip package
  - VADEvent = Literal["speech_start", "speech_end", "speech_continue", "silence"]
  - Configurable via `settings.vad_threshold`, `settings.vad_silence_ms`

### Step 2.3: Moonshine STT

- [ ] Create `bridge/stt.py`
  - `MoonshineST` class (primary):
    - `__init__()` — Load `moonshine-onnx` model (auto-downloads ~26MB)
    - `transcribe_stream(audio_chunks: AsyncGenerator) -> AsyncGenerator[str, None]` — Streaming transcription
    - `transcribe(audio: np.ndarray) -> str` — Full utterance transcription
  - `FasterWhisperSTT` class (fallback):
    - Same interface using `faster-whisper` library
  - Factory: `create_stt(engine=settings.stt_engine) -> STT`
  - Install: `pip install moonshine-onnx` (includes onnxruntime)

### Step 2.4: Kokoro TTS

- [ ] Create `bridge/tts.py`
  - `KokoroTTS` class (primary):
    - `__init__(voice=settings.tts_kokoro_voice)` — Load kokoro-onnx model (~350MB)
    - `synthesize(text: str) -> np.ndarray` — Text to audio float32 array
    - `synthesize_stream(sentences: AsyncGenerator) -> AsyncGenerator[bytes, None]` — Yields PCM chunks per sentence
  - `PiperTTS` class (fallback):
    - Same interface using `piper-tts` library (~22MB model)
  - Factory: `create_tts(engine=settings.tts_engine) -> TTS`
  - Install: `pip install kokoro-onnx` for primary, `pip install piper-tts` for fallback

### Step 2.5: Pipeline orchestrator

- [ ] Create `bridge/pipeline.py`
  - `AudioPipeline` class:
    - `__init__(vad, stt, tts, llm_callback)` — Compose all components
    - `process_audio_chunk(chunk: bytes) -> AsyncGenerator[bytes, None]`:
      1. Decode ADPCM if enabled
      2. Feed to VAD
      3. On speech_end: feed accumulated audio to STT
      4. Pass transcribed text to `llm_callback`
      5. Stream sentence chunks through TTS
      6. Encode ADPCM if enabled
      7. Yield audio response bytes
    - `reset()` — Clear all component state
  - Latency logging at every stage (STT ms, LLM ms, TTS ms)

### Step 2.6: Update requirements.txt

- [ ] Add to `bridge/requirements.txt`:
  ```
  moonshine-onnx>=0.1.0
  kokoro-onnx>=0.4.0
  piper-tts>=1.2.0
  silero-vad>=5.1
  onnxruntime>=1.19.0
  ```

### Verification

```bash
# Test each component individually:
python -c "from bridge.vad import SileroVAD; v = SileroVAD(); print('VAD OK')"
python -c "from bridge.stt import create_stt; s = create_stt(); print('STT OK')"
python -c "from bridge.tts import create_tts; t = create_tts(); print('TTS OK')"

# End-to-end test:
python -c "
import asyncio
from bridge.pipeline import AudioPipeline
# ... test with a sample WAV file
"
# Target: <500ms for simple query through full pipeline
```

---

## Phase 3: Local LLM + Memory (Tab 3)

**Goal:** Simple queries → local Phi-3 (<200ms), complex → Claude; memory recalls context
**Dependencies:** None (standalone modules, integrate later)

### Step 3.1: Ollama setup

- [ ] `ollama pull phi3:mini` — One-time download (~2.3GB)
- [ ] Verify: `ollama run phi3:mini "Hello"` responds

### Step 3.2: Local LLM client

- [ ] Create `bridge/local_llm.py`
  - `OllamaClient` class:
    - `__init__(model=settings.local_llm_model, url=settings.local_llm_url)`
    - `async generate(prompt: str, system: str = None) -> str` — Single response
    - `async generate_stream(prompt: str, system: str = None) -> AsyncGenerator[str, None]` — Streaming
    - `async is_available() -> bool` — Health check Ollama
  - Uses `httpx.AsyncClient` for Ollama REST API (`POST /api/generate`)
  - System prompt: same AEGIS persona as Claude client
  - Timeout: 5s (if Phi-3 is too slow, route to Claude)

### Step 3.3: Intent router

- [ ] Create `bridge/router.py`
  - `IntentRouter` class:
    - `classify(text: str) -> Literal["simple", "complex"]`
    - Simple heuristics (no ML model needed for hackathon):
      - **Simple** (→ local Phi-3): greetings, time, weather, simple health queries ("how am I doing"), simple expense logging ("I spent $20 on lunch"), confirmations
      - **Complex** (→ Claude Opus): analysis requests ("analyze my sleep patterns"), multi-step reasoning, anything with "why", "compare", "trend", "recommend", planning questions
    - Keyword lists + sentence length heuristic
    - `async route(text: str, claude_client, local_llm) -> AsyncGenerator[str, None]`:
      - Classifies intent
      - Routes to appropriate LLM
      - Falls back Claude if local LLM fails/timeout
      - Yields sentence chunks (same interface as ClaudeClient.chat)

### Step 3.4: Conversation memory

- [ ] Create `bridge/memory.py`
  - `ConversationMemory` class:
    - `__init__(db_path=settings.memory_db_path)` — Init sqlite-vec DB
    - `async store(user_text: str, assistant_text: str, metadata: dict)` — Store turn with embedding
    - `async recall(query: str, limit=5) -> list[dict]` — Cosine similarity search
    - `async get_context_prompt(query: str) -> str` — Formatted memory context for LLM
  - Embeddings: use a simple sentence embedding (e.g. `onnxruntime` + small model, or TF-IDF fallback)
  - If `sqlite-vec` is problematic: fallback to plain SQLite with JSON + keyword search
  - Install: `pip install sqlite-vec`

### Step 3.5: Update requirements.txt

- [ ] Add:
  ```
  httpx>=0.27.0
  sqlite-vec>=0.1.0
  ```

### Verification

```bash
# Ollama running?
curl http://localhost:11434/api/tags

# Test local LLM
python -c "
import asyncio
from bridge.local_llm import OllamaClient
async def test():
    c = OllamaClient()
    if await c.is_available():
        print(await c.generate('Hello, how are you?'))
    else:
        print('Ollama not running')
asyncio.run(test())
"

# Test router
python -c "
from bridge.router import IntentRouter
r = IntentRouter()
assert r.classify('hi there') == 'simple'
assert r.classify('analyze my sleep patterns over the last month') == 'complex'
print('Router OK')
"
```

---

## Phase 4: ESP32 Integration (Tab 4)

**Goal:** Speak into pendant → hear response from speaker, full round-trip < 1.5s
**Dependencies:** Phase 1 + 2 + 3 complete

### Step 4.1: Wire audio pipeline into main.py

- [ ] Update `bridge/main.py` `/ws/audio` endpoint:
  - On binary frame: feed to `AudioPipeline.process_audio_chunk()`
  - Yield binary audio response frames back
  - JSON control frames for state: `{"state": "listening|processing|speaking"}`

### Step 4.2: ADPCM on ESP32

- [ ] Update `firmware/src/main.cpp`:
  - Add IMA ADPCM encoder for mic data (4x compression)
  - Add IMA ADPCM decoder for speaker data
  - Reduce buffer sizes (ADPCM = 4x smaller)
  - Update WebSocket frame handling

### Step 4.3: LED state machine

- [ ] Update `firmware/src/main.cpp`:
  - 4 states: IDLE (breathing), LISTENING (solid), PROCESSING (pulse), SPEAKING (fast-blink)
  - Driven by JSON control frames from bridge
  - PTT button (GPIO0) triggers LISTENING state

### Step 4.4: Integration test

- [ ] End-to-end: "How did I sleep this week?" → spoken response with real data
- [ ] Latency measurement: full round-trip timing
- [ ] Audio quality tuning if needed

### Verification

- Speak into pendant → hear AI response from speaker
- Full round-trip < 1.5s for simple queries
- LED states transition correctly
- Stable over 10+ consecutive queries

---

## Phase 5+6: Demo Polish + Submission (Tab 5)

**Goal:** Demo-ready, submitted
**Dependencies:** Phase 4 complete

### Step 5.1: Demo optimization

- [ ] Pre-cache 10 common demo responses (instant fallback)
- [ ] Fallback chain: local LLM → Haiku → Opus → cached response
- [ ] Error recovery: auto-reconnect, graceful degradation

### Step 5.2: Demo script

- [ ] Write `docs/demo-script.md` — 3-minute demo script
- [ ] 5 demo scenarios: health log, spending track, weekly summary, budget check, sleep analysis
- [ ] Rehearse 5 times without failure

### Step 5.3: Documentation

- [ ] Update `docs/architecture.md` with v2 architecture
- [ ] Write `README.md` — Overview, setup, architecture diagram, demo video link
- [ ] Submission materials

### Step 5.4: Record + submit

- [ ] Record backup demo video
- [ ] Push to GitHub (public repo)
- [ ] Submit to Anthropic Claude Code Hackathon

---

## Decision Log

| Date   | Decision                            | Rationale                                                       |
| ------ | ----------------------------------- | --------------------------------------------------------------- |
| Feb 12 | Moonshine Streaming Tiny for STT    | 27M params, 26MB, MIT, native streaming, 5x faster than whisper |
| Feb 12 | Kokoro-82M for TTS                  | #1 TTS-Arena, 82M, Apache 2.0, ONNX, Piper fallback             |
| Feb 12 | Silero VAD                          | Industry standard, <1ms, replaces naive silence counting        |
| Feb 12 | Phi-3-mini via Ollama for local LLM | <200ms for simple queries, 4x faster than Haiku API             |
| Feb 12 | sqlite-vec for memory               | <50ms cosine search, no external deps                           |
| Feb 12 | ADPCM audio codec                   | 4x compression, good quality, simple implementation             |
| Feb 12 | Keep Python (no Go/Rust rewrite)    | 20-30h savings, hackathon constraint                            |
| Feb 12 | Boris parallel strategy             | 5 tabs, independent phases, maximize throughput                 |
| Feb 12 | Kyutai Pocket TTS as backup         | 100M, MIT, voice cloning, evaluate if Kokoro fails              |

## Risk Mitigation

| Risk                     | Probability | Impact | Mitigation                                               |
| ------------------------ | ----------- | ------ | -------------------------------------------------------- |
| Moonshine quality issues | Medium      | Medium | Upgrade to Base (61M); fallback to faster-whisper        |
| Kokoro setup complexity  | Low         | Medium | Fallback to Piper (22MB, instant); try Kyutai Pocket TTS |
| Phi-3 too slow           | Low         | Low    | Route all to Claude; Ollama warm start helps             |
| ADPCM quality loss       | Low         | Medium | Test early; revert to raw PCM if unacceptable            |
| sqlite-vec setup issues  | Low         | Low    | Fallback to plain SQLite JSON search                     |
| Time overrun             | Medium      | High   | Phase 3 can be simplified (routing only, skip memory)    |
| Ollama not installed     | Low         | Low    | Graceful fallback to all-Claude routing                  |

## Existing Code Reference

Files already done (do not recreate):

- `bridge/config.py` — Settings (needs v2 update in Phase 1)
- `bridge/db.py` — Database CRUD + demo data seeding (complete, working)
- `bridge/requirements.txt` — Dependencies (needs v2 additions)
- `bridge/.env.example` — Env template (needs v2 additions)
- `firmware/src/main.cpp` — ESP32 firmware (tested working, needs Phase 4 updates)

Database schema (in db.py):

- `health_logs`: id, date, sleep_hours, steps, heart_rate_avg, mood, notes, created_at
- `expenses`: id, date, amount, category, description, created_at
- 30 days of demo data auto-seeded on first run
