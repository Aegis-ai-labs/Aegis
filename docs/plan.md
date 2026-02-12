# AEGIS1 Implementation Plan — Phase-wise Development

## Status Key
- [ ] Not started
- [x] Complete
- [~] In progress

---

## Phase 1: Foundation (Day 1 — Feb 12)
**Goal:** Bridge server with Claude streaming + tools working in terminal

### Infrastructure
- [x] Project directory structure created
- [~] bridge/config.py — pydantic-settings env config
- [ ] bridge/requirements.txt — Python dependencies
- [ ] bridge/.env.example — Environment template

### Data Layer
- [ ] bridge/db.py — SQLite schema + CRUD operations
- [ ] Seed script — 30 days demo health + expense data

### Tool Layer
- [ ] bridge/tools/__init__.py
- [ ] bridge/tools/registry.py — Tool definitions + dispatch
- [ ] bridge/tools/health.py — get_health_context, log_health, analyze_health_patterns
- [ ] bridge/tools/wealth.py — track_expense, get_spending_summary, calculate_savings_goal

### Claude Integration (Core)
- [ ] bridge/claude_client.py — Streaming client with tool use loop
  - [ ] System prompt tuned for voice (concise responses)
  - [ ] Haiku/Opus model routing
  - [ ] Tool call execution loop
  - [ ] Streaming text yield
  - [ ] Adaptive extended thinking (Opus only)

### Verification
- [ ] Terminal test: text in → Claude with tools → text out
- [ ] All 6 tools return correct data
- [ ] Model routing selects Opus for complex queries

---

## Phase 2: Audio Pipeline (Day 2 — Feb 13)
**Goal:** Full speech-to-speech working via WebSocket

### Audio Components
- [ ] bridge/audio.py — PCM↔WAV conversion, silence detection
- [ ] bridge/stt.py — faster-whisper wrapper (adapted from reference)
- [ ] bridge/tts.py — Piper TTS streaming wrapper

### Orchestrator
- [ ] bridge/main.py — FastAPI + WebSocket server
  - [ ] /ws/audio endpoint (binary PCM streaming)
  - [ ] /health endpoint
  - [ ] /api/status endpoint
  - [ ] Full pipeline: audio → STT → Claude → TTS → audio
  - [ ] Sentence-level streaming (TTS on first sentence boundary)
  - [ ] Latency logging at every stage
  - [ ] Conversation history (multi-turn)

### Verification
- [ ] Python test client sends .wav → gets spoken response
- [ ] Perceived latency <2s for simple queries
- [ ] Latency breakdown logged for each stage

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

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 12 | Claude-native, no framework | Fastest to implement, lowest latency, best Opus showcase |
| Feb 12 | Piper TTS over OpenAI TTS | Free, local, no API dependency, low latency |
| Feb 12 | Button-press only (no wake word) | Saves time, still compelling demo |
| Feb 12 | SQLite over any DB service | Zero setup, embedded, hackathon-appropriate |
| Feb 12 | Firmware already tested | Skip firmware work, focus on bridge software |
