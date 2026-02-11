# AEGIS1 — Master Development Plan

## Timeline

| Phase | Day | Date | Goal | Status |
|-------|-----|------|------|--------|
| 1 | Day 1 | Feb 12 | Bridge server + Claude streaming + tools in terminal | In Progress |
| 2 | Day 2 | Feb 13 | Full speech-to-speech via WebSocket | Not Started |
| 3 | Day 3 | Feb 14 | ESP32 + Bridge end-to-end integration | Not Started |
| 4 | Day 4 | Feb 15 | Tests, polish, demo prep | Not Started |
| 5 | Day 5 | Feb 16 | README, push, submit | Not Started |

---

## Phase 1: Foundation (Feb 12)

**Goal:** Bridge server with Claude streaming + tools working in terminal

### Deliverables
- [x] Project directory structure
- [x] `bridge/config.py` — pydantic-settings env config
- [x] `bridge/requirements.txt` — Python dependencies
- [x] `bridge/.env.example` — Environment template
- [x] `bridge/db.py` — SQLite schema + CRUD + demo data seeding
- [x] `bridge/tools/registry.py` — Tool definitions + dispatch
- [x] `bridge/tools/health.py` — get_health_context, log_health, analyze_health_patterns
- [x] `bridge/tools/wealth.py` — track_expense, get_spending_summary, calculate_savings_goal
- [x] `bridge/claude_client.py` — Streaming client with tool use loop
  - [x] System prompt tuned for voice (concise responses)
  - [x] Haiku/Opus model routing
  - [x] Tool call execution loop
  - [x] Streaming text yield
  - [x] Adaptive extended thinking (Opus only)
- [ ] **Terminal test: text in → Claude with tools → text out**
- [ ] **All 6 tools return correct data**
- [ ] **Model routing selects Opus for complex queries**

### Known Gaps
- `stt_beam_size` referenced in `stt.py` but missing from `config.py`
- `silence_chunks_to_stop` / `max_recording_time_ms` use `hasattr()` fallback in `main.py`

---

## Phase 2: Audio Pipeline (Feb 13)

**Goal:** Full speech-to-speech working via WebSocket

### Deliverables
- [x] `bridge/audio.py` — PCM/WAV conversion, silence detection
- [x] `bridge/stt.py` — faster-whisper wrapper (lazy load, VAD filter)
- [x] `bridge/tts.py` — Piper TTS (Python API + CLI fallback)
- [x] `bridge/main.py` — FastAPI + WebSocket server
  - [x] `/ws/audio` endpoint (binary PCM streaming)
  - [x] `/health` endpoint
  - [x] `/api/status` endpoint (latency stats)
  - [x] Full pipeline: audio → STT → Claude → TTS → audio
  - [x] Sentence-level streaming (TTS on first sentence boundary)
  - [x] Latency logging at every stage
  - [x] Conversation history (multi-turn via ClaudeClient)
- [ ] **Python test client sends .wav → gets spoken response**
- [ ] **Perceived latency <2s for simple queries**
- [ ] **Latency breakdown logged for each stage**

---

## Phase 3: Firmware + Integration (Feb 14)

**Goal:** ESP32 talking to bridge, end-to-end working

### Deliverables
- [x] ESP32 speaker test — working
- [x] ESP32 mic test — working
- [x] ESP32 WiFi — working
- [x] ESP32 WebSocket — working
- [ ] Update `main.cpp` for bridge protocol (JSON status handling)
- [ ] 4-state machine: IDLE → LISTENING → PROCESSING → SPEAKING
- [ ] LED patterns (breathing, solid, pulse, fast-blink)
- [ ] **End-to-end: speak → hear AI response**
- [ ] **Audio quality tuning (gain, noise, silence thresholds)**
- [ ] **Opus 4.6 routing verified for complex queries**

### Verification Scenarios
- "How did I sleep this week?" → accurate spoken response with data
- "I spent $45 on lunch" → expense logged + contextual response
- "Analyze my sleep patterns" → Opus deep analysis with correlations

---

## Phase 4: Polish + Demo (Feb 15)

**Goal:** Demo-ready, all rough edges smoothed

### Deliverables
- [ ] `tests/test_tools.py` — Unit tests for all 6 tools
- [ ] `tests/test_claude.py` — Claude streaming + tool handling
- [ ] `tests/test_latency.py` — Latency benchmarks
- [ ] `tests/test_bridge.py` — Integration tests
- [ ] Pre-seed 30 days compelling demo data (already implemented, verify quality)
- [ ] `docs/demo-script.md` — 3-minute demo script
- [ ] Record demo video
- [ ] `README.md` with architecture diagram
- [ ] Edge case handling (network drops, empty responses, tool errors)
- [ ] Final latency optimization

---

## Phase 5: Submit (Feb 16)

**Goal:** Ship it

### Deliverables
- [ ] Final README polish
- [ ] Push to GitHub (public repo)
- [ ] Submit to Anthropic Claude Code Hackathon

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 12 | Claude-native, no framework | Fastest to implement, lowest latency, best Opus showcase |
| Feb 12 | Piper TTS over OpenAI TTS | Free, local, no API dependency, low latency |
| Feb 12 | Button-press only (no wake word) | Saves implementation time, still compelling demo |
| Feb 12 | SQLite over any DB service | Zero setup, embedded, hackathon-appropriate |
| Feb 12 | Firmware already tested | Skip firmware rework, focus on bridge software |
| Feb 12 | Sentence-level streaming | TTS on first sentence boundary, not after full response |
| Feb 12 | Keyword-based model routing | Simple, fast, sufficient for demo query patterns |
| Feb 12 | Demo data with random.seed(42) | Reproducible, realistic patterns, instant setup |

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Latency >3s | Medium | High | Sentence streaming, Haiku for simple queries |
| Piper voice quality | Medium | Medium | Choose best voice model, keep responses short |
| STT accuracy | Low | Medium | VAD filter, English-only, short utterances |
| ESP32 audio quality | Low | High | Already tested — quality is adequate |
| API rate limiting | Very Low | Medium | Single user, low request rate |
