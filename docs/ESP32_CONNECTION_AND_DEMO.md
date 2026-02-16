# ESP32 Connection and Real-Time Demo

**Purpose:** Clarify which software connects to the ESP32, how auto-connect works, and how to run a real-time hardware demo on your Mac.

---

## 1. Bridge vs Aegis: One Software for Hardware

Both run on the Mac. They are **not** the same server.

| | **bridge** | **aegis** |
|---|------------|-----------|
| **Entry** | `python -m bridge.main` | `aegis serve` or `python -m aegis` then `serve` |
| **App** | `bridge.main:app` | `aegis.main:app` |
| **/ws/audio** | Full pipeline: PCM in → STT → Claude/Gemini/Ollama → TTS → PCM out, chimes | Stub: accepts connection, returns "Audio pipeline not yet implemented" |
| **mDNS** | Yes (ESP32 auto-discovery) | No |
| **Dashboard** | Yes (`/`, `static/index.html`) | No |
| **Use for ESP32** | **Yes** — this is the only server that talks to hardware end-to-end | No — use for text-only testing (`/ws/text`) |

**Conclusion:** There is only **one** server that connects to the ESP32 for full voice: **bridge**. For hardware demos and real-time testing, always run **bridge**, not aegis.

For a plain-language explanation of what bridge and aegis are and who does what (including tool calling and LLM order), see **`docs/BRIDGE_VS_AEGIS.md`**.

---

## 2. Which Files Auto-Connect the Hardware

Auto-connect means: the ESP32 can find and connect to the server with minimal manual config (e.g. mDNS) or with one manual step (set BRIDGE_HOST).

### 2.1 Server side (Mac)

| File | Role |
|------|------|
| **bridge/main.py** | On startup (`startup_event`), if `SERVER_DISCOVERY` is true, registers mDNS service `aegis1._tcp.local` on `bridge_port` (8000). ESP32 can discover `aegis1.local:8000` on the same LAN. |
| **bridge/config.py** | `server_discovery_enabled` (env `SERVER_DISCOVERY`, default True), `mdns_service_name` (env `MDNS_SERVICE_NAME`, default `aegis1`), `bridge_port` (8000). |
| **.env** | Optional: `SERVER_DISCOVERY=false` to disable mDNS; `BRIDGE_PORT=8000`. |

So: **bridge** is what does auto-connect (mDNS). **aegis** has no mDNS.

### 2.2 Firmware side (ESP32)

| File | Role |
|------|------|
| **firmware/config.h** | `BRIDGE_HOST` — IP of the Mac (e.g. from `ifconfig \| grep "inet " \| grep -v 127.0.0.1`). If you use mDNS on the ESP32 (separate snippet in bridge/esp32_config.py), it can discover the host; the main firmware in `firmware/src/main.cpp` uses a fixed `BRIDGE_HOST`. |
| **firmware/src/main.cpp** | Connects to `BRIDGE_HOST:BRIDGE_PORT` path `/ws/audio`; sends binary PCM; receives binary TTS. |

So: **auto-connect** is either (a) mDNS on server + ESP32 firmware that does mDNS lookup, or (b) manual: set `BRIDGE_HOST` in firmware to your Mac’s IP. Current **firmware in aegis1** uses (b); the **snippet in bridge/esp32_config.py** describes (a).

---

## 3. Single Command to Run the Server for Hardware

From the project root, with the **bridge** venv (so all deps including zeroconf are available):

```bash
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
python -m bridge.main
```

Or if your default Python/venv already has bridge deps:

```bash
cd /Users/apple/Documents/aegis1
python -m bridge.main
```

Run from **project root** so `static/index.html` is found (bridge opens `"static/index.html"` relative to the current working directory).

You should see in the log:

- Server: `0.0.0.0:8000`
- WebSocket: `ws://localhost:8000/ws/audio`
- mDNS: `aegis1.local:8000` (if SERVER_DISCOVERY is true)

---

## 4. Real-Time Demo: Connect ESP32 and Test

### 4.1 Prerequisites

- ESP32 flashed with firmware from `firmware/` (see `firmware/README.md`).
- `firmware/config.h`: `WIFI_SSID`, `WIFI_PASSWORD`, and **BRIDGE_HOST** = your Mac’s LAN IP (e.g. `10.0.0.5`). Get it: `ifconfig | grep "inet " | grep -v 127.0.0.1`.

### 4.2 Step 1: Start the bridge (Mac)

```bash
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
python -m bridge.main
```

Leave this running. Confirm in the log: WebSocket and (if enabled) mDNS.

### 4.3 Step 2: Power ESP32 and connect

- Power the ESP32 (USB or battery).
- It connects to WiFi, then to `BRIDGE_HOST:8000/ws/audio`.
- Serial monitor (e.g. 115200): you should see something like `[OK] WiFi ...` then `[OK] AEGIS1 bridge connected`.

### 4.4 Step 3: Open dashboard (Mac)

In a browser:

```
http://localhost:8000/
```

You should see the AEGIS1 dashboard (live transcript, status, etc.) when the ESP32 is connected and you speak.

### 4.5 Step 4: Test voice

- Speak into the ESP32 mic (e.g. “How did I sleep this week?”).
- Bridge: records until silence, runs STT → LLM → TTS, sends PCM back.
- ESP32: plays listening chime, then TTS, then success chime.
- Dashboard: shows user message, assistant message, and latency.

### 4.6 Optional: Disable mDNS

If you don’t want mDNS (e.g. zeroconf not installed or firewall issues):

```bash
export SERVER_DISCOVERY=false
python -m bridge.main
```

Then the ESP32 **must** use a fixed IP in `BRIDGE_HOST` (no auto-discovery).

---

## 5. Quick Reference

| Goal | Command / action |
|------|-------------------|
| Run the only server that connects to ESP32 | `python -m bridge.main` (from project root, bridge venv) |
| Get Mac IP for BRIDGE_HOST | `ifconfig \| grep "inet " \| grep -v 127.0.0.1` |
| Dashboard | `http://localhost:8000/` |
| Health | `http://localhost:8000/health` |
| Disable mDNS | `export SERVER_DISCOVERY=false` before starting bridge |
| Text-only test (no hardware) | Run **aegis** instead: `aegis serve` then `aegis terminal` (aegis has /ws/text; bridge does not). For hardware demos use bridge only. |

---

## 6. Summary

- **Bridge** and **aegis** are two different apps on the same Mac. Only **bridge** implements the full /ws/audio pipeline and mDNS for the ESP32.
- **One software for hardware:** run **bridge** (`python -m bridge.main`) for ESP32 connection and real-time demos.
- **Auto-connect:** bridge registers mDNS (`aegis1._tcp.local`); firmware can use mDNS (see bridge/esp32_config.py) or a fixed **BRIDGE_HOST** in `firmware/config.h`.
- **Real-time demo:** start bridge → set BRIDGE_HOST in firmware → power ESP32 → open dashboard → speak and verify.
