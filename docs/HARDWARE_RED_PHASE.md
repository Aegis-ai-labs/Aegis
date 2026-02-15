# Hardware Integration — RED Phase

**Purpose:** TDD-style failing tests that define the contract between the AEGIS1 bridge server and ESP32 hardware. Implement or fix until tests pass (GREEN).

**Test file:** `tests/test_hardware_integration_red.py`

---

## What These Tests Define

1. **HTTP endpoints** — Bridge exposes `/health` and `/api/status` for monitoring and dashboard.
2. **WebSocket contract** — `/ws/audio` accepts ESP32, sends a `connected` message with config (sample_rate, chunk_size_ms), accepts binary PCM, and responds with audio (e.g. listening chime).
3. **Firmware load** — Firmware snippet is obtainable from the project and contains required symbols: `/ws/audio`, WIFI_SSID, WIFI_PASSWORD, WebSocketsClient, sendBIN, playAudioToSpeaker/WStype_BIN.

---

## Test Classes

| Class | Tests | What it verifies |
|-------|-------|------------------|
| TestHealthEndpoint | 2 | GET /health returns 200 and JSON with status/version |
| TestApiStatusEndpoint | 2 | GET /api/status returns 200 and connections/latency |
| TestWebSocketAudioEndpoint | 4 | /ws/audio connect, first message, accept binary, respond with bytes |
| TestFirmwareSnippetObtainable | 5 | Snippet exists and contains required symbols |

**Total:** 13 tests.

---

## How to Run

### Firmware-only (no bridge app; safe in any env)

```bash
cd /Users/apple/Documents/aegis1
python3 -m pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v
```

Expected: 5 passed.

### Full suite (bridge server + WebSocket)

Use the bridge virtualenv so `bridge.main` and its dependencies (numpy, audio_feedback) load correctly:

```bash
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
python3 -m pytest tests/test_hardware_integration_red.py -v
```

Expected (RED): some failures until server and firmware match the contract.  
Expected (GREEN): 13 passed after implementation.

---

## RED vs GREEN

- **RED:** Tests written first; they fail because behavior is missing or wrong.
- **GREEN:** Fix bridge (or firmware snippet) so all 13 tests pass. No change to test assertions.
- **REFACTOR:** Clean up bridge/firmware code; keep tests green.

---

## Relation to Other Docs

- **Hardware setup and wiring:** `HARDWARE_SETUP_GUIDE.md`, `HARDWARE_QUICK_CHECKLIST.md`
- **Single hardware check + firmware load:** `HARDWARE_CHECK.md`
- **ESP32 connection flow:** `docs/esp32-connection-guide.md`

---

## Success Criteria

- [ ] All 13 hardware integration RED tests pass (GREEN).
- [ ] Bridge server starts and serves `/health`, `/api/status`, `/ws/audio`.
- [ ] ESP32 can connect to bridge, receive config, send PCM, receive audio.
- [ ] Firmware snippet is obtainable and contains required symbols (so "load firmware" step is validated).
