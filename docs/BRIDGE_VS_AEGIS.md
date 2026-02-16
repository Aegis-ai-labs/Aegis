# Bridge vs Aegis — What Runs Where

**Purpose:** Clarify what "bridge" and "aegis" are, what talks to what, and how to run the system (Anthropic first, then optional Ollama).

---

## 1. Short Answer

| Term | What it is | Where it lives | Who talks to it |
|------|------------|----------------|-----------------|
| **Bridge** | The **server** that does the full voice pipeline (mic → STT → LLM → TTS → speaker). It also does tool calling and can use Claude, Gemini, or Ollama. | `bridge/` in this repo | **ESP32** connects to bridge only. You run bridge on your Mac. |
| **Aegis** | A **separate** Python app in the same repo. It has text WebSocket and a stub audio WebSocket. It is **not** the server the ESP32 uses. | `aegis/` in this repo | No one in the hardware flow. You can run aegis for text-only testing. |

**Bridge does not talk to aegis.** They are two different applications. For hardware (ESP32 pendant), you run **bridge** only. Aegis is not "uploaded" anywhere; bridge is the server that runs on your Mac and the ESP32 connects to it over WiFi.

---

## 2. What Is Bridge?

- **Role:** Server that runs on your Mac (or any host). Listens on port 8000.
- **Code:** `bridge/main.py`, `bridge/claude_client.py`, `bridge/llm_router.py`, `bridge/tools/`, `bridge/stt.py`, `bridge/tts.py`, etc.
- **Run it:** From project root, `python -m bridge.main` (with bridge deps installed, e.g. `source bridge/.venv/bin/activate`).
- **What it does:**
  - Accepts WebSocket at `/ws/audio` from the ESP32 (binary PCM in, binary TTS out, chimes).
  - STT (faster-whisper) → text.
  - LLM (Claude by default, or Gemini or Ollama via env) → streaming text + tool calls.
  - Tool calling (health, wealth, insight tools) is implemented **inside bridge**.
  - TTS (Piper) → PCM back to ESP32.
  - Optional dashboard (`/`), mDNS for ESP32 discovery.

So: **bridge is the server and bridge does the tool calling.** The ESP32 talks only to bridge.

---

## 3. What Is Aegis?

- **Role:** A second, separate Python package in the same repo. It was the planned "target" package (e.g. "rename bridge → aegis" in docs).
- **Code:** `aegis/main.py`, `aegis/claude_client.py`, `aegis/config.py`, `aegis/db.py`, etc.
- **Run it:** `python -m aegis` (or `aegis serve` if the CLI is set up).
- **What it does:**
  - `/ws/text` — text-only WebSocket; works for testing Claude without hardware.
  - `/ws/audio` — **stub only**: accepts connection but returns "Audio pipeline not yet implemented. Use /ws/text for testing."
  - No mDNS, no full voice pipeline.

So: **aegis is not the server for the ESP32.** For hardware you use bridge. Aegis is for future use or text-only testing.

---

## 4. Does Bridge Talk to Aegis?

**No.** Bridge does not call aegis. Bridge has its own LLM client, tools, STT, and TTS. The flow is:

```
ESP32  →  bridge (your Mac)  →  Claude / Gemini / Ollama (API or local)
                ↓
         bridge tools (health, wealth, insight)
                ↓
         bridge TTS  →  ESP32
```

Aegis is a separate app you could run instead of bridge for text-only; it does not sit in between the ESP32 and the LLM.

---

## 5. LLM Order: Anthropic First, Then Optional Ollama

All of this is **inside bridge** (via `bridge/llm_router.py`):

1. **Default (production):** Claude (Anthropic). Set `ANTHROPIC_API_KEY` in `.env`. No other env needed.
2. **Budget testing:** Set `USE_GEMINI_FOR_TESTING=true` and `GEMINI_API_KEY`. Bridge uses Gemini instead of Claude.
3. **Local / no API key:** Set `USE_LOCAL_MODEL=true`. Bridge uses **Ollama** (must be running locally, e.g. `ollama serve`). No Anthropic or Gemini key needed.

So: **First get it working with Anthropic.** If that works, then you can optionally run Ollama and set `USE_LOCAL_MODEL=true` to test the same pipeline with a local model. Bridge does not "upload" aegis; bridge is the server, and you choose which LLM bridge talks to (Claude, Gemini, or Ollama) via env.

---

## 6. Where Is Aegis "Uploaded"?

Aegis is **not** uploaded to a device. It is just another app in this repo that you can run on your Mac (e.g. `python -m aegis`) for text WebSocket testing. The **firmware** (ESP32) is uploaded to the ESP32 via PlatformIO (`pio run -t upload`). The **bridge** runs on your Mac and listens for the ESP32. So:

- **ESP32:** firmware from `firmware/` is **flashed** to the board.
- **Mac:** you **run** `python -m bridge.main`; that process is the server the ESP32 connects to.
- **Aegis:** optional; run `python -m aegis` if you want the text-only app. It is not used in the hardware path.

---

## 7. Quick Reference

| I want to… | Use |
|------------|-----|
| Run the voice pendant with ESP32 | Run **bridge**: `python -m bridge.main` |
| Use Claude (default) | Set `ANTHROPIC_API_KEY`; run bridge. |
| Use local Ollama instead | Set `USE_LOCAL_MODEL=true`, run `ollama serve`, then run bridge. |
| Test without hardware (text only) | Run **aegis** and use `/ws/text`, or run bridge and use dashboard. |
| Know who does tool calling | **Bridge** (and aegis has its own tools, but bridge is what the ESP32 uses). |

---

## 8. Improvements / To-Do

| Item | Status | Notes |
|------|--------|--------|
| Claude streaming | Done | Bridge uses `AsyncAnthropic` so `async with messages.stream()` works. |
| WebSocket disconnect | Done | Bridge handles post-disconnect `RuntimeError` without traceback. |
| STT often empty (VAD strips all audio) | Optional | Set `STT_VAD_FILTER=false` in `.env` if faster-whisper VAD removes all audio; then STT will transcribe without VAD. |
| Relax VAD instead of disabling | Optional | Can tune `vad_parameters` in faster-whisper if needed (see bridge/stt.py). |

## 9. Related Docs

- **ESP32 connection and demo:** `docs/ESP32_CONNECTION_AND_DEMO.md`
- **System overview and model I/O:** `docs/SYSTEM_OVERVIEW.md`
- **First-read testing context:** `docs/memory-bank/first-read-testing-context.md`
