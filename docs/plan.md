# AEGIS1 Implementation Plan — Phase-wise Development

## Status Key

- [ ] Not started
- [x] Complete
- [~] In progress

## Current Status (Feb 12, 2026)

**Phase 1: COMPLETE** ✅ — Custom Ultra-Light Architecture fully implemented and tested
**Phase 2: COMPLETE** ✅ — Full audio pipeline operational with WebSocket streaming

- All core components operational: claude_client, tools (7 tools), db, stt, tts, audio, orchestrator
- Full speech-to-speech pipeline working via WebSocket
- Sentence-level streaming achieving <2s perceived latency
- 26+ tests passing (test_tools.py, test_claude_client.py, test_audio.py)
- Real-time dashboard with WebSocket updates
- Ready for Phase 3 (ESP32 Integration)

---

## Phase 1: Foundation (Day 1 — Feb 12) ✅ COMPLETE

**Goal:** Bridge server with Claude streaming + tools working in terminal

### Infrastructure

- [x] Project directory structure created
- [x] bridge/config.py — pydantic-settings env config
- [x] bridge/requirements.txt — Python dependencies
- [x] bridge/.env.example — Environment template

### Data Layer

- [x] bridge/db.py — SQLite schema + CRUD operations
- [x] Seed script — 30 days demo health + expense data

### Tool Layer

- [x] bridge/tools/**init**.py
- [x] bridge/tools/registry.py — Tool definitions + dispatch (7 tools)
- [x] bridge/tools/health.py — get_health_context, log_health, analyze_health_patterns
- [x] bridge/tools/wealth.py — track_expense, get_spending_summary, calculate_savings_goal
- [x] bridge/context.py — Rich context builder with weekly comparisons

### Claude Integration (Core)

- [x] bridge/claude_client.py — Streaming client with tool use loop
  - [x] System prompt tuned for voice (concise responses)
  - [x] Haiku/Opus model routing (keyword-based triggers)
  - [x] Tool call execution loop (max 5 rounds)
  - [x] Streaming text yield (AsyncGenerator)
  - [x] Adaptive extended thinking (Opus only)

### Audio Components

- [x] bridge/stt.py — faster-whisper wrapper
- [x] bridge/tts.py — Piper TTS streaming wrapper
- [x] bridge/audio.py — PCM↔WAV conversion, silence detection

### Orchestrator

- [x] bridge/main.py — FastAPI + WebSocket server
  - [x] /ws/audio endpoint (binary PCM streaming)
  - [x] /health endpoint
  - [x] /api/status endpoint
  - [x] Full pipeline: audio → STT → Claude → TTS → audio
  - [x] Sentence-level streaming (TTS on first sentence boundary)
  - [x] Latency logging at every stage
  - [x] Conversation history (multi-turn)
  - [x] Real-time dashboard with WebSocket updates

### Verification

- [x] Terminal test: text in → Claude with tools → text out
- [x] All 7 tools return correct data
- [x] Model routing selects Opus for complex queries
- [x] 26+ tests passing (unit + integration)

---

## Phase 2: Audio Pipeline (Day 2 — Feb 13) ✅ COMPLETE

**Goal:** Full speech-to-speech working via WebSocket

### Audio Components

- [x] bridge/audio.py — PCM↔WAV conversion, silence detection
- [x] bridge/stt.py — faster-whisper wrapper (adapted from reference)
- [x] bridge/tts.py — Piper TTS streaming wrapper

### Orchestrator

- [x] bridge/main.py — FastAPI + WebSocket server
  - [x] /ws/audio endpoint (binary PCM streaming)
  - [x] /health endpoint
  - [x] /api/status endpoint
  - [x] Full pipeline: audio → STT → Claude → TTS → audio
  - [x] Sentence-level streaming (TTS on first sentence boundary)
  - [x] Latency logging at every stage
  - [x] Conversation history (multi-turn)
  - [x] Real-time dashboard with WebSocket updates

### Verification

- [x] Python test client sends .wav → gets spoken response
- [x] Perceived latency <2s for simple queries
- [x] Latency breakdown logged for each stage

---

## Phase 3: Firmware + Integration (Day 3 — Feb 14)

**Goal:** ESP32 talking to bridge, end-to-end working

### Firmware (if needed — user says firmware is tested)

- [x] Speaker test — working
- [x] Mic test — working
- [x] WiFi test — working
- [x] WebSocket test — working
- [ ] Update main.cpp for new bridge protocol (if needed)
- [ ] 4-state machine: IDLE → LISTENING → PROCESSING → SPEAKING
- [ ] LED patterns

### Integration

- [ ] Connect ESP32 to bridge server
- [ ] End-to-end: speak → hear AI response
- [ ] Tune audio quality (gain, noise, silence thresholds)
- [ ] Opus 4.6 routing verified for complex queries

### Verification

- [ ] "How did I sleep this week?" → accurate spoken response
- [ ] "I spent $45 on lunch" → expense logged + context response
- [ ] "Analyze my sleep patterns" → Opus deep analysis

---

## Phase 4: Polish + Demo (Day 4 — Feb 15)

**Goal:** Demo-ready, all rough edges smoothed

### Tests

- [ ] tests/test_tools.py — Unit tests for all 6 tools
- [ ] tests/test_claude.py — Claude streaming + tool handling
- [ ] tests/test_latency.py — Latency benchmarks
- [ ] tests/test_bridge.py — Integration tests

### Demo Prep

- [ ] Pre-seed 30 days compelling demo data
- [ ] docs/demo-script.md — 3-minute demo script
- [ ] Record demo video
- [ ] README.md with architecture diagram

### Polish

- [ ] Edge case handling (network drops, empty responses, tool errors)
- [ ] Final latency optimization
- [ ] Cleanup dead code

---

## Phase 5: Submit (Day 5 — Feb 16)

- [ ] Final README polish
- [ ] Push to GitHub
- [ ] Submit to hackathon

---

## Decision Log

| Date   | Decision                                     | Rationale                                                                                        |
| ------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Feb 12 | **Custom Ultra-Light Framework** (FINAL)     | After 6 parallel experiments, this approach won on latency, implementation speed, and simplicity |
|        | - Direct Anthropic SDK (no Pipecat)          | Full control over streaming, tool calls, and model routing                                       |
|        | - FastAPI + WebSocket                        | Clean async architecture, minimal overhead                                                       |
|        | - Component-based design                     | Enables independent optimization of each pipeline stage                                          |
|        | - Sentence-level streaming                   | Critical innovation: TTS starts on first sentence boundary → <2s perceived latency               |
|        | - 3-layer system prompt                      | Enables Anthropic prompt caching optimization                                                    |
|        | - Smart model routing (Haiku 80% / Opus 20%) | Balance speed and intelligence with keyword triggers                                             |
| Feb 12 | Rejected: Pipecat                            | Too heavyweight, abstraction prevented sentence-level streaming optimization                     |
| Feb 12 | Rejected: OpenCLAW fork                      | Complex, designed for multi-agent scenarios, overkill for single-agent pendant                   |
| Feb 12 | Rejected: Nanobot                            | Experimental, immature ecosystem, would require building too much from scratch                   |
| Feb 12 | Piper TTS over OpenAI TTS                    | Free, local, no API dependency, low latency                                                      |
| Feb 12 | Button-press only (no wake word)             | Saves time, still compelling demo                                                                |
| Feb 12 | SQLite over any DB service                   | Zero setup, embedded, hackathon-appropriate                                                      |
| Feb 12 | Firmware already tested                      | Skip firmware work, focus on bridge software                                                     |
