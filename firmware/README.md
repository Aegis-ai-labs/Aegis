# AEGIS1 Firmware (ESP32 Voice Pendant)

Firmware for the AEGIS1 voice pendant. Connects to the AEGIS1 bridge at `BRIDGE_HOST:BRIDGE_PORT/ws/audio` and streams mic audio to the bridge; receives TTS PCM and plays on the speaker.

**Source:** Main logic adapted from the AEGIS prototype (`/Users/apple/aegis`) — `test_5_openclaw_voice` — which was flashed and tested on hardware.

---

## Hardware

- **Board:** ESP32 DevKit V1 (DOIT)
- **Mic:** INMP441 I2S (BCLK=13, LRCLK=14, DIN=33)
- **Speaker:** PAM8403 on DAC1 (GPIO 25). Connect speaker to amp **right channel** (R+ and R-) for mono output.
- **LED:** GPIO 2
- **Button:** GPIO 0 (BOOT)

**Volume / crackling:** The PAM8403 is strong; a small speaker can sound cracked or distorted. In `config.h`: (1) `PLAYBACK_VOLUME_PERCENT` (default 20) sets overall level—lower if still too loud, raise if too quiet. (2) `PLAYBACK_MAX_PEAK_PERCENT` (default 70) caps peaks so the DAC never hits full scale, which reduces harsh clipping and crackling. Use 100 for no cap.

---

## Setup

1. **Copy and edit config**
   - Copy `config.h.template` to `config.h` if you use a template workflow, or edit `config.h` directly.
   - Set `WIFI_SSID`, `WIFI_PASSWORD`, and `BRIDGE_HOST` (your Mac/laptop IP).  
   - Get IP: `ifconfig | grep "inet " | grep -v 127.0.0.1`

2. **Install PlatformIO** (CLI or VS Code extension)
   - CLI: `pip install platformio`

3. **Build**
   ```bash
   cd firmware
   pio run
   ```

4. **Upload**
   - Put ESP32 in download mode: hold BOOT, press RST, release.
   ```bash
   pio run -t upload
   ```

5. **Serial monitor**
   ```bash
   pio device monitor
   ```
   Expect: `Version: 1.0.0` (or current `AEGIS1_FIRMWARE_VERSION` in `src/main.cpp`), then `[OK] WiFi ...`, `[OK] AEGIS1 bridge connected` after the bridge is running. Use the version line to confirm which build is flashed.

---

## Bridge

Start the AEGIS1 bridge before or after flashing:

```bash
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
python3 -m bridge.main
```

Bridge serves WebSocket at `ws://0.0.0.0:8000/ws/audio`. Set `BRIDGE_HOST` in `config.h` to your machine’s LAN IP so the ESP32 can connect.

---

## Contract (Firmware ↔ Bridge)

- **Path:** `/ws/audio`
- **ESP32 → Bridge:** Binary PCM chunks (16 kHz, 16-bit mono). Chunk size 320 bytes (10 ms) in this firmware.
- **Bridge → ESP32:** First message JSON `{"type":"connected", ...}`; then binary PCM (TTS) and optional JSON status.
- **Config:** Bridge sends `sample_rate` (16000) and `chunk_size_ms` (200) in the connected message.

---

## Tests (from project root)

Firmware main file is checked by the hardware integration RED tests:

```bash
pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v
pytest tests/test_firmware_main.py -v
```

See `docs/HARDWARE_CHECK.md` and `docs/HARDWARE_RED_PHASE.md`.
