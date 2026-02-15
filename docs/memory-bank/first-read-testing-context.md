# AEGIS1 — First Read: Project Context & Testing Phase

**Purpose:** Single reference for project structure, documentation, memory bank, and testing readiness. Use this before firmware, hardware, and software testing.

**Last updated:** 2026-02-15

---

## 1. What AEGIS1 Is

- **Product:** AI voice pendant (health + wealth) for the Anthropic Claude Code Hackathon (Feb 10–16, 2026).
- **Stack:** ESP32 pendant (mic, speaker, LED, button) → WebSocket → Python bridge server (FastAPI) → Claude (Haiku 4.5 + Opus 4.6) + 7 tools → SQLite.
- **State:** Implementation complete; currently in **testing phase** (firmware, hardware, software).

---

## 2. Repository Structure (Relevant Paths)

```
aegis1/
├── bridge/                    # Legacy Python server (some code still referenced)
├── aegis/                      # Target Python package (config, db, claude_client, tools, main, etc.)
├── firmware/                  # ESP32 PlatformIO (main = voice; from AEGIS prototype)
│   ├── src/main.cpp           # Voice pipeline: mic → bridge → speaker
│   ├── config.h               # WIFI_SSID, BRIDGE_HOST, pins (edit before flash)
│   └── platformio.ini         # Build: pio run; upload: pio run -t upload
├── docs/
│   ├── README.md               # Doc index and navigation
│   ├── memory-bank/            # Project context (this file lives here)
│   │   ├── projectbrief.md     # Mission, scope, hackathon criteria
│   │   ├── techcontext.md      # Tech stack, env vars, hardware pins, repo layout
│   │   ├── activecontext.md    # Current phase, decisions, risks, next actions
│   │   ├── progress.md         # Phase 1–4 status, firmware status, risks
│   │   ├── systempatterns.md   # Pipeline, tools, model routing, DB, config
│   │   └── first-read-testing-context.md  # This file
│   ├── esp32-connection-guide.md   # Hardware setup, bridge URL, dashboard, fallback
│   ├── RED_PHASE_*             # RED phase deliverables (DB, API, audio pipeline)
│   ├── IMPLEMENTATION_*.md     # Implementation guides and checklists
│   └── database_schema_requirements.md
├── tests/                     # All test suites (see below)
├── README.md                   # Product overview, architecture, quick start
├── .env                        # ANTHROPIC_API_KEY, server, audio, DB config
└── CLAUDE.md                   # Claude Code workflow and rules
```

---

## 3. Documentation & Memory Bank — Where to Look

| Need | Document |
|------|----------|
| What AEGIS1 is, goals, audience | `docs/memory-bank/projectbrief.md` |
| Tech stack, setup, env, hardware pins | `docs/memory-bank/techcontext.md` |
| Current phase, decisions, risks, next steps | `docs/memory-bank/activecontext.md` |
| Phase 1–4 and firmware completion status | `docs/memory-bank/progress.md` |
| Patterns: pipeline, tools, routing, DB | `docs/memory-bank/systempatterns.md` |
| Doc index and navigation | `docs/README.md` |
| RED phase tests index | `docs/INDEX.md` (RED_PHASE_*) |
| ESP32 connection and testing | `docs/esp32-connection-guide.md` |
| Bridge vs aegis, auto-connect, real-time demo | `docs/ESP32_CONNECTION_AND_DEMO.md` |
| High-level product and architecture | Root `README.md` |

---

## 4. Test Suites (Software)

| Suite | File | Purpose |
|-------|------|---------|
| DB (RED phase) | `tests/test_db_red_phase.py` | 30 tests: health/expense CRUD, date range, spending, embeddings, transactions, indexes |
| Claude API (RED) | `tests/test_claude_api_red.py` | Model selection, streaming, history, rate limit, tools |
| Audio pipeline (RED) | `tests/test_audio_pipeline_red.py` | Audio format, STT/TTS/Claude integration, E2E, errors, perf |
| Health/wealth (RED) | `tests/test_health_wealth_red.py` | Health and wealth tool behavior |
| Tools | `tests/test_tools.py` | Tool registry and handlers |
| Claude client | `tests/test_claude_client.py` | Client behavior |
| Config | `tests/test_config.py` | Settings and env |
| Audio | `tests/test_audio.py` | Audio utilities |
| E2E | `tests/test_e2e_pipeline.py` | End-to-end pipeline |
| DB (legacy) | `tests/test_db.py` | Older DB tests |
| **Hardware integration (RED)** | `tests/test_hardware_integration_red.py` | Bridge ↔ ESP32 contract: /health, /api/status, /ws/audio, firmware snippet (13 tests) |
| **Firmware main** | `tests/test_firmware_main.py` | Firmware main file and config exist and match bridge contract (15 tests) |

**RED phase:** Many tests are written to fail until implementation is done; see `docs/RED_PHASE_EXPECTED_FAILURES.md` and `docs/QUICK_START_RED_TESTS.txt`.

**Hardware RED:** See `docs/HARDWARE_RED_PHASE.md`. Single hardware check + firmware load: `docs/HARDWARE_CHECK.md`.

---

## 5. Firmware & Hardware Testing

- **Hardware:** ESP32 DevKit V1, INMP441 (I2S), PAM8403 (DAC1 GPIO25), LED GPIO2, Button GPIO0.
- **Connection:** Bridge at `ws://<IP>:8000/ws/audio`; start server then point ESP32 at correct IP.
- **Flow:** Start **bridge** (not aegis) → set BRIDGE_HOST in firmware → power ESP32 → speak → listen for chimes and response.
- **Reference:** `docs/ESP32_CONNECTION_AND_DEMO.md`, `docs/esp32-connection-guide.md`, `HARDWARE_SETUP_GUIDE.md`, `HARDWARE_QUICK_CHECKLIST.md`.
- **Hardware RED (TDD):** `docs/HARDWARE_RED_PHASE.md` — failing tests that define bridge/ESP32 contract.
- **Hardware check (one flow):** `docs/HARDWARE_CHECK.md` — wiring checklist, firmware load, server start, run hardware RED tests.

---

## 6. Quick Commands

```bash
# Server for ESP32 hardware: bridge only (aegis has stub /ws/audio)
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
python -m bridge.main

# Dashboard
open http://localhost:8000

# Run test suites
python3 -m pytest tests/test_db_red_phase.py -v
python3 -m pytest tests/test_claude_api_red.py -v
python3 -m pytest tests/test_audio_pipeline_red.py -v
# Firmware main file (contract match): 15 tests
python3 -m pytest tests/test_firmware_main.py -v
# Hardware RED (firmware-only, no bridge app): 5 tests
python3 -m pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v
# Hardware RED (full suite; use bridge venv): 13 tests
source bridge/.venv/bin/activate && python3 -m pytest tests/test_hardware_integration_red.py -v
python3 -m pytest tests/ -v
```

---

## 7. Testing Phase Objectives (Your Goals)

1. **Firmware:** Verify ESP32 build, flash, WiFi, WebSocket, audio in/out, button/LED.
2. **Hardware:** Verify mic, speaker, power, connections per pinout.
3. **Software:** Run test suites; move RED → GREEN where applicable; document expected failures.
4. **First read / memory bank:** Use this file and `docs/memory-bank/*` for context; update `activecontext.md` and `progress.md` as testing progresses.

---

## 8. Next Step

You said: *"Then I'll tell you what to do."* Context and docs are initialized. Specify the first concrete task (e.g. run a test suite, firmware checklist, or update a doc), and we can execute it step by step.
