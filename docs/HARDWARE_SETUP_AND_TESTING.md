# AEGIS1 Hardware Setup & Testing Guide

**Target Hardware:** ESP32 DevKit V1 + INMP441 Mic + PAM8403 Speaker  
**Firmware:** AEGIS1 v1.0.0  
**Backend:** FastAPI Bridge  
**Expected Time:** 30 minutes (setup) + 15 minutes (testing)  
**Date:** 2026-02-16

---

## Part 1: Hardware Assembly (15 minutes)

### Prerequisites

**Equipment Needed:**
- ESP32 DevKit V1 board
- INMP441 I2S MEMS microphone module
- PAM8403 analog amplifier module
- Small 8Ω speaker
- Jumper wires (M-M, M-F)
- USB cable (for ESP32 programming + serial console)
- Multimeter (optional, for pin verification)

### Wiring Diagram

```
ESP32 DevKit V1       INMP441 Mic Module
─────────────────     ──────────────────
GPIO 13 (BCLK)  ────→ SCK
GPIO 14 (LRCLK) ────→ WS
GPIO 33 (DIN)   ←──── SD
GND             ────→ GND
3.3V            ────→ VCC

                      PAM8403 Amplifier
                      ─────────────────
GPIO 25 (DAC1)  ────→ IN+ (Signal)
GND             ────→ GND
3.3V            ────→ VCC

                      Speaker
                      ───────
PAM8403 OUT+    ────→ Speaker +
PAM8403 OUT-    ────→ Speaker -
```

### Step-by-Step Wiring

#### 1. Microphone Connections (INMP441)

| INMP441 Pin | ESP32 GPIO | Wire Color |
|-------------|-----------|-----------|
| SCK | 13 | Red |
| WS | 14 | Yellow |
| SD | 33 | Green |
| GND | GND | Black |
| VCC | 3.3V | Orange |

**Steps:**
1. Attach jumper wire to INMP441 SCK → plug into ESP32 GPIO 13
2. Attach jumper wire to INMP441 WS → plug into ESP32 GPIO 14
3. Attach jumper wire to INMP441 SD → plug into ESP32 GPIO 33
4. Attach GND wire → plug into any ESP32 GND pin
5. Attach 3.3V wire → plug into ESP32 3.3V pin

#### 2. Speaker Amplifier Connections (PAM8403)

| PAM8403 Pin | ESP32 GPIO | Purpose |
|-----------|-----------|---------|
| IN+ | 25 (DAC1) | Audio signal input |
| GND | GND | Ground |
| VCC | 3.3V | Power |
| OUT+ | Speaker+ | Speaker output |
| OUT- | Speaker- | Speaker output |

**Steps:**
1. Attach jumper wire to PAM8403 IN+ → plug into ESP32 GPIO 25
2. Attach jumper wire to PAM8403 GND → plug into ESP32 GND
3. Attach jumper wire to PAM8403 VCC → plug into ESP32 3.3V
4. Attach speaker wires to PAM8403 OUT+ and OUT-
5. Verify all connections are secure

#### 3. LED Connection (Optional Status Indicator)

| LED | ESP32 GPIO | Purpose |
|-----|-----------|---------|
| Anode (+) | 2 | Blue LED (connection status) |
| Cathode (-) | GND | Ground |

**Note:** ESP32 DevKit V1 has built-in blue LED on GPIO 2 (no additional wiring needed if using onboard LED).

### Verification Checklist

- [ ] Microphone SCK connected to GPIO 13
- [ ] Microphone WS connected to GPIO 14
- [ ] Microphone SD connected to GPIO 33
- [ ] Microphone GND and VCC properly connected
- [ ] Amplifier IN+ connected to GPIO 25
- [ ] Amplifier GND connected to ESP32 GND
- [ ] Amplifier VCC connected to 3.3V
- [ ] Speaker wires connected to amplifier outputs
- [ ] All jumper wires are secure and not loose
- [ ] No crossed wires (short circuits)

---

## Part 2: Firmware Configuration & Flashing (15 minutes)

### Step 1: Update Firmware Config

Before flashing, update `firmware/config.h` with your network details:

```c
// firmware/config.h
#define WIFI_SSID "your_ssid"           // Your WiFi network name
#define WIFI_PASSWORD "your_password"   // Your WiFi password

#define BRIDGE_HOST "YOUR_IP_ADDRESS"   // Your Mac/laptop IP
#define BRIDGE_PORT 8000                // AEGIS1 Bridge port (don't change)
```

**Find your Mac/Laptop IP:**
```bash
# On Mac:
ifconfig | grep "inet " | grep -v 127.0.0.1

# On Linux:
hostname -I

# On Windows:
ipconfig | findstr "IPv4"
```

**Example:**
```c
#define WIFI_SSID "MyHome"
#define WIFI_PASSWORD "secure123"
#define BRIDGE_HOST "192.168.1.42"  // Your actual IP
#define BRIDGE_PORT 8000
```

### Step 2: Install PlatformIO

If not already installed:

```bash
# Install PlatformIO CLI
pip install platformio

# Verify installation
pio --version
```

### Step 3: Connect ESP32 via USB

1. Plug ESP32 DevKit V1 into computer via USB cable
2. Check if recognized:
```bash
# On Mac/Linux:
ls -la /dev/tty.* | grep -i usb

# On Windows:
# Device Manager → Ports (COM & LPT) → should see "USB UART"
```

### Step 4: Build Firmware

```bash
cd /Users/apple/Documents/aegis1/firmware
pio run
```

Expected output:
```
Building in release mode
Compiling .pio/build/esp32doit-devkit-v1/src/main.cpp.o
...
Linking .pio/build/esp32doit-devkit-v1/firmware.elf
Creating firmware binary .pio/build/esp32doit-devkit-v1/firmware.bin
```

**If build fails:**
- Check that `config.h` exists in `firmware/` directory
- Verify `#include "../config.h"` is in `firmware/src/main.cpp`
- Run `pio lib install` to ensure all dependencies are downloaded

### Step 5: Upload Firmware to ESP32

```bash
cd /Users/apple/Documents/aegis1/firmware
pio run --target upload
```

Expected output:
```
Uploading .pio/build/esp32doit-devkit-v1/firmware.bin
Configuring upload protocol...
Detected ESP32 on COM3/ttyUSB0
...
Wrote 850944 bytes to address 0x1000 in 20.50 seconds
```

**If upload fails:**
- Check USB connection
- Verify ESP32 appears in device list (from Step 3)
- Try pressing BOOT button while uploading
- Check baud rate: `pio run --target upload -- --baud 115200`

### Step 6: Monitor Serial Output

```bash
pio device monitor --baud 115200
```

Expected output after successful flash:
```
=== AEGIS1 Voice Firmware (Main) ===
Version: 1.0.0
Target: 192.168.1.42:8000/ws/audio
Flow: Mic -> Bridge -> STT/Claude/TTS -> Speaker

[OK] Mic ready
[...] WiFi connecting...
....................
[OK] WiFi 192.168.1.100
[OK] WebSocket started; speak into mic after connection
```

**Troubleshooting:**
- If WiFi fails: Check SSID/password in `config.h`
- If bridge connection fails: Verify `BRIDGE_HOST` IP is correct and bridge is running
- If no serial output: Check USB cable and board drivers

---

## Part 3: Backend Bridge Setup (10 minutes)

### Step 1: Start Backend Bridge

In a separate terminal (not the serial monitor):

```bash
cd /Users/apple/Documents/aegis1

# Activate venv (if not already)
source .venv/bin/activate

# Start backend (use bridge, not aegis)
cd bridge
python -m bridge.main
```

Expected output:
```
INFO:     Started server process [1234]
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Verify Backend is Running

In another terminal:

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
{"status": "ok", "service": "aegis1-bridge"}
```

### Step 3: Check ESP32 Connection

In the ESP32 serial monitor (from Part 2, Step 6), you should see:

```
[OK] AEGIS1 bridge connected
```

If still showing `[...] Connecting...`:
- Verify bridge is running (from Step 1)
- Verify `BRIDGE_HOST` in firmware `config.h` matches your machine IP
- Check that both devices are on same WiFi network
- Try restarting ESP32 (press RESET button)

---

## Part 4: Testing (15 minutes)

### Test 1: Microphone Input Verification

**Objective:** Confirm ESP32 is reading audio from INMP441 mic

**Steps:**
1. Look at ESP32 serial monitor output
2. Speak into the microphone for 3 seconds
3. Watch serial monitor for audio chunk logs

**Expected Output:**
```
[OK] AEGIS1 bridge connected
[...] Recording audio...
```

**If not working:**
- Check GPIO pins 13, 14, 33 are securely connected
- Verify INMP441 microphone is powered (3.3V, GND)
- Try adjusting microphone orientation (some MEMS mics are directional)
- Check firmware I2S configuration: `I2S_SAMPLE_RATE = 16000`

### Test 2: Speaker Output Verification

**Objective:** Confirm ESP32 can play audio on PAM8403 speaker

**Steps:**
1. Via text WebSocket (for now, since audio pipeline not implemented):
```bash
# Terminal 1: WebSocket with bridge
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/text
```

2. Send (paste into terminal):
```json
{"text": "Hello, this is AEGIS1 testing"}
```

3. Backend should respond with text
4. (Audio playback requires TTS implementation - not yet done)

**Expected Output:**
```
{"text": "Hello, this is...", "done": true}
```

**If speaker doesn't play:**
- Check GPIO 25 (DAC) connection to PAM8403 IN+
- Verify amplifier power: 3.3V to VCC, GND to GND
- Check speaker polarity: OUT+ to speaker + (red), OUT- to speaker - (black)
- Verify volume is set correctly: `PLAYBACK_VOLUME_PERCENT = 20` in config.h
- Try adjusting volume higher if no sound: increase to 40, then 60, then 80

### Test 3: LED Status Indicator

**Objective:** Confirm LED blinks on bridge connection

**Steps:**
1. Observe ESP32 blue LED (GPIO 2)
2. Verify LED is ON when "bridge connected" message appears
3. Verify LED turns OFF if bridge disconnects

**Expected Behavior:**
- LED OFF at startup
- LED blinks while connecting to WiFi
- LED steady ON when bridge connected
- LED OFF when bridge disconnects

**If LED not blinking:**
- Check GPIO 2 is not shorted
- Verify firmware is running (check serial output)
- Try adjusting LED brightness: modify `digitalWrite(LED_PIN, value)`

### Test 4: WebSocket Connection (Text-Only)

**Objective:** Verify backend can receive and respond to text queries

**Steps:**

**Terminal 1 - Start Backend:**
```bash
cd /Users/apple/Documents/aegis1/bridge
python -m bridge.main
```

**Terminal 2 - Test WebSocket:**
```bash
# Connect to text WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/text
```

**Terminal 2 - Send Test Message:**
```json
{"text": "How did I sleep this week?"}
```

**Expected Response:**
```json
{"text": "You averaged 6 hours on weekdays...", "done": false}
{"text": "", "done": true}
```

**If connection refused:**
- Check bridge is running: `curl http://localhost:8000/health`
- Verify correct port: `http://localhost:8000`
- Check firewall isn't blocking port 8000

### Test 5: Full End-to-End Audio Flow (When Audio Pipeline Implemented)

**Prerequisites:**
- STT model (Moonshine) installed
- TTS model (Kokoro) installed
- Backend `/ws/audio` handler updated with STT/TTS logic

**Test Steps (For Future Implementation):**
1. ESP32 captures audio: firmware records mic input
2. Firmware sends PCM to bridge: `/ws/audio` receives binary chunks
3. Bridge runs STT: converts audio to text
4. Bridge queries Claude: health-aware response
5. Bridge runs TTS: converts response to audio
6. Bridge sends PCM back: ESP32 receives binary chunks
7. ESP32 plays audio: speaker produces output

**Expected Duration:**
- Audio capture: 3-5 seconds (user speaks)
- STT latency: <400ms (Moonshine Tiny)
- Claude latency: <500ms (Haiku) or ~2s (Opus)
- TTS latency: 100-200ms per sentence (Kokoro)
- Speaker playback: 2-5 seconds (response length)
- **Total E2E:** ~7-13 seconds wall-clock time

---

## Part 5: Troubleshooting

### Issue: ESP32 Can't Connect to WiFi

**Symptoms:**
- Serial monitor shows `[...] WiFi connecting...` forever
- LED blinks but never stays on

**Fixes:**
1. Verify SSID/password in `firmware/config.h`
2. Check WiFi network is 2.4GHz (ESP32 doesn't support 5GHz only)
3. Verify correct WiFi password (case-sensitive)
4. Check router isn't blocking device MAC address
5. Try restarting ESP32: press RESET button

### Issue: WebSocket Connection Refused

**Symptoms:**
- Serial monitor shows `[...] Connecting...`
- Backend logs show no connection attempt

**Fixes:**
1. Verify `BRIDGE_HOST` in `firmware/config.h` is correct
```bash
# Check your IP:
ifconfig | grep "inet "
```
2. Verify backend is running:
```bash
curl http://localhost:8000/health
```
3. Check ESP32 can reach backend:
```bash
# From ESP32 serial, you'll see if WebSocket connection is attempted
# Check for error logs
```
4. Try with localhost instead if on same machine:
```c
#define BRIDGE_HOST "127.0.0.1"  // Or your actual IP
```
5. Verify firewall isn't blocking port 8000:
```bash
# On Mac:
lsof -i :8000
```

### Issue: Microphone Not Reading Audio

**Symptoms:**
- Serial monitor shows `[OK] Mic ready`
- But no audio being captured/sent
- No message when speaking into mic

**Fixes:**
1. Check I2S pin connections:
   - GPIO 13 (SCK) ← INMP441 SCK
   - GPIO 14 (WS) ← INMP441 WS
   - GPIO 33 (SD) ← INMP441 SD
2. Verify microphone is powered: check 3.3V and GND
3. Try recording silence first, then with loud sound
4. Check microphone orientation: some MEMS mics are directional
5. Increase I2S_SAMPLE_RATE if getting weird audio
6. Check `I2S_BUF_COUNT = 8` and `I2S_BUF_LEN = 512` settings

### Issue: Speaker Not Playing Audio

**Symptoms:**
- No sound from speaker when response is sent
- Serial monitor shows text being processed
- But speaker is silent

**Fixes:**
1. Check PAM8403 connections:
   - GPIO 25 (DAC) → IN+
   - GND → GND
   - 3.3V → VCC
2. Check speaker wires are connected correctly (+ and -)
3. Verify amplifier is powered with 3.3V (check with multimeter)
4. Try increasing volume: change `PLAYBACK_VOLUME_PERCENT` from 20 to 60
5. Verify speaker is not broken: test with battery directly
6. Check GPIO 25 DAC is configured correctly in firmware

### Issue: Persistent Audio Dropout or Crackling

**Symptoms:**
- Audio plays but cuts out frequently
- Speaker produces crackling/distorted sound
- WebSocket connection drops intermittently

**Fixes:**
1. Reduce volume to prevent clipping: lower `PLAYBACK_VOLUME_PERCENT`
2. Adjust peak capping: lower `PLAYBACK_MAX_PEAK_PERCENT` to 50
3. Increase WiFi signal: move closer to router
4. Reduce other WiFi interference: turn off 2.4GHz devices
5. Verify I2S clock is stable: check `SEND_CHUNK_BYTES = 320` (10ms chunks)
6. Check PCM buffer isn't overflowing: monitor `play_len` in firmware

---

## Part 6: Demo Walkthrough (5 minutes)

### Setup (1 minute)

```bash
# Terminal 1: Start backend bridge
cd /Users/apple/Documents/aegis1/bridge
python -m bridge.main

# Terminal 2: Monitor ESP32 serial
pio device monitor --baud 115200

# Terminal 3: Test text WebSocket (optional)
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/text
```

### Demo Script (4 minutes)

**Part A: Show Hardware (1 minute)**
1. Point to ESP32 board
2. Point to INMP441 microphone module
3. Point to PAM8403 amplifier
4. Point to speaker
5. Explain the wiring: "Microphone on left, speaker on right, all connected to this board here"

**Part B: Show Connection (1 minute)**
1. Observe serial monitor
2. Point out: "WiFi connecting... connected!"
3. Point out: "WebSocket connected to bridge!"
4. Show LED is on: "Blue LED indicates active connection"

**Part C: Show Text Interaction (1 minute)**
1. Send WebSocket message: `{"text": "How did I sleep this week?"}`
2. Show response appearing in terminal
3. Show health context being used: "Notice it gives specific numbers about MY sleep patterns"
4. Explain: "Without audio pipeline implemented yet, we're testing via text. Full voice coming soon."

**Part D: Explain Architecture (1 minute)**
1. Point to serial monitor
2. Say: "Here's the full pipeline: Microphone → WebSocket → Cloud (Claude) → Response → Speaker"
3. Explain: "Right now we're at 90% complete. Need to add STT and TTS models for full voice support."
4. Show HARDWARE_INTEGRATION_ARCHITECTURE.md explaining what's needed

---

## Checklist for Full Demo Readiness

- [ ] Hardware wiring complete and verified
- [ ] Firmware configured with correct WiFi SSID/password
- [ ] Firmware configured with correct BRIDGE_HOST IP
- [ ] Firmware flashed to ESP32
- [ ] Serial monitor shows "WiFi connected"
- [ ] Serial monitor shows "AEGIS1 bridge connected"
- [ ] LED is ON (GPIO 2)
- [ ] Backend bridge is running (`python -m bridge.main`)
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] Text WebSocket test works: message sent, response received
- [ ] All three terminals ready (backend, serial monitor, curl/test)
- [ ] Demo script prepared (see Part 6 above)

---

## Next Steps (After Hardware Testing Works)

1. **Implement STT Pipeline** (4-6 hours)
   - Install Moonshine model
   - Add audio buffering + VAD to `/ws/audio`
   - Test STT locally with recorded audio samples

2. **Implement TTS Pipeline** (4-6 hours)
   - Install Kokoro model
   - Add TTS handler to `/ws/audio`
   - Stream PCM back to ESP32

3. **Full E2E Testing** (2-3 hours)
   - Test mic → STT → Claude → TTS → speaker
   - Record demo video
   - Prepare fallback (text-only) if audio fails during demo

4. **Demo Video Recording** (1-2 hours)
   - Record full conversation (3-5 minutes)
   - Show health context being used
   - Show response appearing on speaker

---

## References

- **Firmware:** `/Users/apple/Documents/aegis1/firmware/src/main.cpp`
- **Backend:** `/Users/apple/Documents/aegis1/bridge/main.py` (or `aegis/main.py`)
- **Architecture Analysis:** `docs/HARDWARE_INTEGRATION_ARCHITECTURE.md`
- **Hardware Specs:** Firmware `config.h` and `main.cpp`

