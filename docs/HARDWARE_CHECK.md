# Hardware Check — Wiring, Firmware Load, Server, Test

Single flow: wire hardware, obtain and load firmware, start bridge, run hardware RED tests.

**Time:** ~25–35 min (wiring + Arduino + server + tests).

---

## 1. Wiring Checklist

Use this before flashing. Full details: `HARDWARE_SETUP_GUIDE.md`, `HARDWARE_QUICK_CHECKLIST.md`.

### INMP441 mic → ESP32

- [ ] GND → GND  
- [ ] 3.3V → 3.3V  
- [ ] BCLK (pin 5) → GPIO 13  
- [ ] LRCLK (pin 3) → GPIO 14  
- [ ] DIN (pin 1) → GPIO 33  
- [ ] L/R (pin 4) → GND  

### PAM8403 speaker → ESP32

- [ ] GND → GND  
- [ ] VCC (5V) → USB 5V  
- [ ] IN+ → GPIO 25 (via 10k resistor)  
- [ ] IN- → GND  
- [ ] OUT+/OUT- → speaker  

### Optional

- [ ] Button → GPIO 0 (BOOT)  
- [ ] LED → GPIO 2  

---

## 2. Get and Load Firmware

**Preferred:** Use the AEGIS1 firmware in this repo (from AEGIS prototype, tested on hardware).

### 2.1 Firmware location

- **Path:** `aegis1/firmware/` — PlatformIO project with `src/main.cpp` (voice pipeline: mic → bridge → speaker).
- **Config:** Edit `firmware/config.h`: set `WIFI_SSID`, `WIFI_PASSWORD`, `BRIDGE_HOST` (your Mac/laptop IP).

### 2.2 Build and flash (PlatformIO)

```bash
cd /Users/apple/Documents/aegis1/firmware
pio run
pio run -t upload
```

(ESP32 in download mode: hold BOOT, press RST, then upload.)

### 2.3 Alternative: Arduino IDE

If you prefer Arduino IDE:

1. Open `firmware/src/main.cpp` (and ensure `firmware/config.h` is in the same parent so `#include "../config.h"` works, or adjust include path).
2. Install ESP32 board support and WebSockets library (links2004/WebSockets).
3. Set **Board:** ESP32 Dev Module, **Port:** /dev/cu.usbserial-XXXX, **Upload speed:** 115200.
4. Put ESP32 in download mode; Sketch → Upload.

### 2.4 Flash ESP32

1. Put ESP32 in download mode: hold BOOT, press RST, release after ~2 s.  
2. Run `pio run -t upload` (or Sketch → Upload in Arduino IDE).  
3. Wait for "Leaving... Hard resetting...".  
4. Press RST to run.

---

## 3. Start Bridge Server

```bash
cd /Users/apple/Documents/aegis1
source bridge/.venv/bin/activate
# Optional (free testing): export USE_LOCAL_MODEL=true
python3 -m bridge.main
```

Confirm in log:

- Server: `0.0.0.0:8000`  
- WebSocket: `ws://localhost:8000/ws/audio`  
- Dashboard: `http://localhost:8000/`  

---

## 4. Verify ESP32 Connection

- **Serial Monitor:** 9600 baud.  
- Expected: `Connected! IP: ...`, `Found server: ...`, `WebSocket connected to AEGIS1`.  
- **Dashboard:** Open `http://localhost:8000`; use for live transcript and status.

---

## 5. Run Hardware and Firmware Tests

### Firmware main file (contract match)

```bash
cd /Users/apple/Documents/aegis1
python3 -m pytest tests/test_firmware_main.py -v
```

Expect: 15 passed.

### Hardware RED — firmware snippet (no server)

```bash
python3 -m pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v
```

Expect: 5 passed.

### Full hardware integration (with bridge venv)

```bash
source bridge/.venv/bin/activate
python3 -m pytest tests/test_hardware_integration_red.py -v
```

Expect (GREEN): 13 passed. If any fail, treat as RED and fix bridge or firmware until green.

---

## 6. Quick Reference

| Step | Command / action |
|------|-------------------|
| Wiring | See §1 and HARDWARE_QUICK_CHECKLIST.md |
| Firmware | `aegis1/firmware/` — edit config.h, then `cd firmware && pio run -t upload` |
| Start server | `source bridge/.venv/bin/activate && python3 -m bridge.main` |
| Firmware main tests | `pytest tests/test_firmware_main.py -v` |
| Hardware RED (snippet) | `pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v` |
| All hardware tests | `source bridge/.venv/bin/activate && pytest tests/test_hardware_integration_red.py -v` |

---

## 7. Troubleshooting

- **No port:** Restart Arduino IDE; check USB cable/driver.  
- **Upload fails:** Hold BOOT, press RST, retry upload.  
- **WiFi fails:** Check SSID/password (case-sensitive).  
- **Server not found (mDNS):** Use bridge IP in firmware: `ws://<IP>:8000/ws/audio`.  
- **Tests segfault:** Run full suite inside bridge venv (`source bridge/.venv/bin/activate`).
