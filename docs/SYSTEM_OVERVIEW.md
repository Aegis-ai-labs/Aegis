# AEGIS1 — System Overview and Input/Output

**Purpose:** Single reference for how the system is planned to work, how data flows end-to-end, and where each “side” (ESP32, bridge, model, dashboard) is documented.

**Last updated:** 2026-02-15

---

## 1. How the System Is Planned to Work

### 1.1 End-to-end flow

```
User speaks → ESP32 (mic) → PCM over WebSocket → Bridge
    → STT (speech → text) → LLM (text → text + tool calls) → TTS (text → PCM)
    → PCM over WebSocket → ESP32 (speaker) → User hears response
```

- **One software for hardware:** The **bridge** server (`python -m bridge.main`) is the only server that connects to the ESP32 for full voice. The **aegis** package has a minimal /ws/audio stub; for hardware demos use the bridge only (see `docs/ESP32_CONNECTION_AND_DEMO.md`).

- **LLM options:** Bridge can use **Claude** (default), **Gemini** (USE_GEMINI_FOR_TESTING=true), or **Ollama** (USE_LOCAL_MODEL=true). Model input is always text; model output is streaming text plus optional tool-use blocks.

- **Streaming:** The bridge streams LLM output sentence-by-sentence and sends PCM to the ESP32 as soon as a sentence is complete, so TTS starts before the full response is ready (lower perceived latency).

---

## 2. Input/Output by Stage

### 2.1 ESP32 (hardware) side

| Direction   | Medium        | Format / content |
|------------|---------------|------------------|
| **Input**  | Mic (INMP441) | 16 kHz, 16-bit mono PCM. Firmware sends 320-byte chunks (10 ms) over WebSocket binary to bridge. |
| **Output** | Speaker (PAM8403) | Bridge sends 16-bit PCM; firmware converts to 8-bit DAC (GPIO 25). Volume reduced by `PLAYBACK_VOLUME_PERCENT` in `firmware/config.h` if amp is too loud for small speaker. |

**Docs:** `firmware/README.md`, `docs/esp32-connection-guide.md`, `docs/HARDWARE_CHECK.md`, `docs/ESP32_CONNECTION_AND_DEMO.md`, `HARDWARE_SETUP_GUIDE.md`.

---

### 2.2 Bridge (server) side

| Stage   | Input                    | Output |
|---------|--------------------------|--------|
| **WebSocket** | Binary PCM chunks from ESP32; optional JSON `end_of_speech` / `reset`. | On connect: JSON `{"type":"connected", "config":{...}}`. Then: binary PCM (listening chime, thinking tone, TTS, success chime); JSON `{"type":"status","state":"..."}`. |
| **STT** | Raw PCM (16 kHz 16-bit mono) converted to WAV. | Plain text (user utterance). |
| **LLM** | Text (user message) + system prompt (persona + health context + tool directives). | Streaming text tokens; optional tool_use blocks (name + arguments). |
| **Tools** | Tool name + arguments (from LLM). | JSON result (e.g. health summary, logged expense). |
| **TTS** | Text (one sentence or full reply). | 16-bit PCM at 16 kHz (Piper in current bridge). |
| **Back to ESP32** | — | Binary PCM in ~6400-byte chunks (200 ms); JSON status/done. |

**Current implementation:** STT = faster-whisper; TTS = Piper; LLM = Claude or Gemini or Ollama via `bridge/llm_router.py`. No ADPCM in current bridge; PCM is sent as-is. Chimes generated in `bridge/audio_feedback.py`.

**Docs:** `bridge/main.py` (orchestrator), `docs/architecture.md`, `docs/architecture-final.md`, `docs/memory-bank/systempatterns.md`.

---

### 2.3 Model (LLM) side

| Item    | Description |
|---------|-------------|
| **Input** | **Messages:** system prompt (3-layer: persona, health context, tool directives) + conversation history + latest user text. **Tools:** JSON schema for 7 tools (health×3, wealth×3, insight×1). |
| **Output** | **Streaming:** Text deltas (token-by-token). **Tool use:** Blocks with tool name and input schema; bridge executes and sends results back; model may continue with more text or tool calls (max 5 rounds). |
| **Routing** | Simple keywords (e.g. "analyze", "pattern") → Opus for deeper analysis; otherwise Haiku. Optional: Ollama for local, Gemini for budget testing. |

**Model input format (conceptual):**

- System: string (persona + dynamic health context + tool rules).
- User: string (STT result, e.g. "How did I sleep this week?").
- Tools: list of `{name, description, input_schema}`.

**Model output format (conceptual):**

- Stream: `content_block` with `text` delta or `tool_use` (id, name, input).
- Bridge maps tool_use → `execute_tool(name, arguments)` → JSON string → appended as tool result message; streaming continues.

**Docs:** `bridge/claude_client.py`, `bridge/llm_router.py`, `bridge/tools/registry.py`, `docs/memory-bank/systempatterns.md` (model routing, tool dispatch).

---

### 2.4 Dashboard side

| Direction | Content |
|-----------|--------|
| **Browser → Bridge** | HTTP GET `/` (dashboard HTML), WebSocket `/ws/dashboard` (optional). |
| **Bridge → Dashboard** | Events over `/ws/dashboard`: e.g. `health_summary`, `user_message`, `pipeline_state`, `assistant_message`, `tool_call`, `tool_result`. |

**Docs:** `static/index.html`, `bridge/main.py` (dashboard route and broadcast).

---

## 3. Where Each “Side” Is Documented

| Side       | What it covers | Key docs |
|------------|----------------|----------|
| **ESP32 / firmware** | Hardware pins, WiFi, WebSocket, PCM in/out, volume | `firmware/README.md`, `firmware/config.h`, `docs/esp32-connection-guide.md`, `docs/HARDWARE_CHECK.md`, `docs/ESP32_CONNECTION_AND_DEMO.md`, `HARDWARE_SETUP_GUIDE.md` |
| **Bridge / server** | Pipeline, STT, TTS, chimes, WebSocket protocol, mDNS | `bridge/main.py`, `docs/architecture.md`, `docs/architecture-final.md`, `docs/ESP32_CONNECTION_AND_DEMO.md`, `docs/memory-bank/systempatterns.md` |
| **Model / LLM** | Claude (and Gemini/Ollama), streaming, tools, routing | `bridge/claude_client.py`, `bridge/llm_router.py`, `bridge/tools/registry.py`, `docs/memory-bank/systempatterns.md`, `docs/architecture-final.md` |
| **Dashboard** | Real-time UI, events | `static/index.html`, `bridge/main.py` (dashboard_websocket, broadcast_to_dashboard) |
| **Tests** | Contract and pipeline tests | `docs/memory-bank/first-read-testing-context.md`, `docs/HARDWARE_RED_PHASE.md`, `docs/RED_PHASE_*`, `tests/test_*.py` |

---

## 4. Planned vs Current (Bridge)

| Component | Planned (some docs) | Current (bridge) |
|-----------|---------------------|-------------------|
| STT       | Moonshine, Silero VAD | faster-whisper, silence detection (amplitude) |
| TTS       | Kokoro              | Piper (PiperVoice or CLI) |
| Audio codec | ADPCM (4×)        | Raw PCM |
| LLM       | Haiku + Opus, optional Ollama | Claude / Gemini / Ollama via llm_router |
| Hardware server | — | bridge only (aegis has stub /ws/audio) |

The **system overview** above and **model input/output** (Section 2.2, 2.3) reflect the **current** bridge behavior. Architecture and research docs describe both target and current where they differ.

---

## 5. Quick Reference: Data Types

| Stage     | Input type  | Output type |
|-----------|------------|------------|
| ESP32 → Bridge | Binary: PCM 320 B (10 ms) | — |
| Bridge STT | PCM (WAV) | String (user text) |
| Bridge → Model | String (user) + system + tools | Stream: text deltas + tool_use blocks |
| Bridge tools | name + dict args | JSON string (result) |
| Bridge TTS | String (sentence) | PCM bytes (16-bit, 16 kHz) |
| Bridge → ESP32 | — | Binary: PCM chunks; JSON: status/done |
| Dashboard | — | JSON events (user_message, assistant_message, tool_call, etc.) |

---

## 6. Doc Index (by topic)

- **System overview and I/O:** this file (`docs/SYSTEM_OVERVIEW.md`).
- **Architecture and pipeline:** `docs/architecture.md`, `docs/architecture-final.md`.
- **ESP32 connection and demo:** `docs/ESP32_CONNECTION_AND_DEMO.md`, `docs/esp32-connection-guide.md`, `docs/HARDWARE_CHECK.md`.
- **Bridge vs aegis:** `docs/ESP32_CONNECTION_AND_DEMO.md` (§1).
- **Patterns and conventions:** `docs/memory-bank/systempatterns.md`.
- **Project and tech context:** `docs/memory-bank/projectbrief.md`, `docs/memory-bank/techcontext.md`.
- **Testing and first read:** `docs/memory-bank/first-read-testing-context.md`, `docs/HARDWARE_RED_PHASE.md`, `docs/INDEX.md`.
