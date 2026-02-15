# AEGIS1 Hardware Setup & Firmware Flashing Guide

**Date:** February 15, 2026 | **Duration:** ~30 minutes

---

## 📋 PART 1: Hardware Connections (Physical Wiring)

### Components Needed
- [ ] ESP32 DevKit V1 (with USB cable)
- [ ] INMP441 I2S Microphone
- [ ] PAM8403 Amplifier Module
- [ ] Speaker (3-8Ω, 0.5-2W)
- [ ] Jumper wires (20+)
- [ ] Breadboard (optional)

### Step 1A: Microphone Connection (INMP441)

```
INMP441 Pin → ESP32 Pin
─────────────────────────
GND         → GND
3.3V        → 3.3V
BCLK        → GPIO 13
LRCLK       → GPIO 14
DIN         → GPIO 33
L/R         → GND (mono input)
```

**Physical Connection:**
1. Connect GND (black wire) from INMP441 to ESP32 GND
2. Connect 3.3V (red wire) from INMP441 to ESP32 3.3V
3. Connect BCLK (blue) from INMP441 Pin 5 → ESP32 GPIO 13
4. Connect LRCLK (green) from INMP441 Pin 3 → ESP32 GPIO 14
5. Connect DIN (yellow) from INMP441 Pin 1 → ESP32 GPIO 33
6. Connect L/R (orange) from INMP441 Pin 4 → ESP32 GND

**Diagram:**
```
INMP441 Board (top view)
┌─────────────────────┐
│ 1:DIN  3:LRCLK      │
│                     │
│ 4:L/R  5:BCLK       │
│ 6:GND  2:3.3V       │
└─────────────────────┘
       ↓ (wires)
ESP32 DevKit V1
```

### Step 1B: Speaker Connection (PAM8403)

```
PAM8403 Pin → ESP32 Pin / Connection
────────────────────────────────────
GND         → GND
VCC (5V)    → 5V
IN+         → GPIO 25 (DAC1) via 10kΩ resistor
IN-         → GND
OUT+ (R)    → Speaker+ (right channel)
OUT- (R)    → Speaker- (right channel)
OUT+ (L)    → Speaker+ (left channel) 
OUT- (L)    → Speaker- (left channel)
```

**Physical Connection:**
1. Connect GND (black) from PAM8403 to ESP32 GND
2. Connect 5V (red) from USB power → PAM8403 VCC
3. Connect GPIO 25 (via 10kΩ resistor) → PAM8403 IN+
4. Connect GND (black) → PAM8403 IN-
5. Connect Speaker+ (red) → PAM8403 OUT+ (either L or R)
6. Connect Speaker- (black) → PAM8403 OUT- (matching side)

**Note:** If using 5V power, get from USB cable or external power supply

### Step 1C: Button & LED (Optional, for demo)

```
Button  → GPIO 0 (BOOT pin) [active LOW]
LED     → GPIO 2            [active HIGH]
```

### Verification Checklist Before Flashing

- [ ] Microphone GND connected
- [ ] Microphone 3.3V connected
- [ ] Microphone BCLK→GPIO13
- [ ] Microphone LRCLK→GPIO14
- [ ] Microphone DIN→GPIO33
- [ ] Speaker GND connected
- [ ] Speaker VCC connected to 5V
- [ ] Speaker IN+ connected (with resistor)
- [ ] Speaker IN- connected to GND
- [ ] ESP32 USB cable connected to laptop
- [ ] No loose wires or short circuits

---

## 📝 PART 2: Get Firmware Code

### Step 2A: Extract Firmware Code

Run this command to get the complete firmware code:

```bash
cd /Users/apple/Documents/aegis1
python3 << 'PYEOF'
from bridge.esp32_config import ESP32_FIRMWARE_SNIPPET
print(ESP32_FIRMWARE_SNIPPET)
PYEOF
```

This will print the complete Arduino sketch code.

### Step 2B: Create Arduino Sketch File

1. **Open Arduino IDE** (download from arduino.cc if not installed)
2. **File → New**
3. **Paste the firmware code** (from Step 2A)
4. **Modify WiFi Settings** (CRITICAL!):
   ```cpp
   // Line 15-16, change these:
   const char* WIFI_SSID = "YOUR_WIFI_NETWORK";        // ← Change this
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // ← Change this
   ```

5. **Save File**: 
   - **File → Save**
   - Name: `aegis1_firmware`
   - Location: Your preferred folder

---

## ⚙️ PART 3: Configure Arduino IDE for ESP32

### Step 3A: Install ESP32 Board Support

1. **Preferences (Arduino → Preferences)**
2. Find "Additional Boards Manager URLs"
3. **Paste this URL:**
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. **OK**

### Step 3B: Install Board

1. **Tools → Board Manager**
2. **Search:** "esp32"
3. **Click:** "ESP32 by Espressif Systems"
4. **Install** (latest version)
5. **Close**

### Step 3C: Select Board & Port

1. **Tools → Board → ESP32 → ESP32 Dev Module**
2. **Tools → Port → /dev/cu.usbserial-XXXXXX** (highest number)
   - If no port shows, USB driver issue (see troubleshooting)
3. **Tools → Upload Speed → 921600**

---

## 🔧 PART 4: Flash Firmware to ESP32

### Step 4A: Verify Code Compiles

1. **Sketch → Verify/Compile** (or Ctrl+R)
2. Wait for "Compiling..."
3. Should see: ✅ "Compilation complete"
4. If errors: Check WiFi credentials and C++ syntax

### Step 4B: Upload to ESP32

1. **ESP32 in "Download Mode":**
   - Hold **BOOT button** (GPIO 0)
   - While holding, press **RST button** (Reset)
   - Wait 2 seconds
   - Release both buttons

2. **Sketch → Upload** (or Ctrl+U)
   - Should see: "Connecting..."
   - Then: "Writing at..."
   - Then: ✅ "Leaving... Hard resetting..."

3. **Done!** Firmware is flashed

### Step 4C: Reset ESP32

- Press **RST button** (Reset)
- ESP32 will restart and run firmware
- Should connect to WiFi automatically

---

## 🖥️ PART 5: Start AEGIS Server

### Step 5A: Open New Terminal Window

```bash
cd /Users/apple/Documents/aegis1
```

### Step 5B: Start Ollama (Optional - for FREE testing)

**In another terminal:**
```bash
ollama serve
```

(Wait for message: "listening on 127.0.0.1:11434")

### Step 5C: Start AEGIS Bridge Server

**In main terminal:**

**For FREE testing with Ollama:**
```bash
export USE_LOCAL_MODEL=true
python3 -m bridge.main
```

**OR for production with Claude:**
```bash
python3 -m bridge.main
```

**Expected output:**
```
2026-02-15 12:00:00 [aegis1] INFO: ============================================================
2026-02-15 12:00:00 [aegis1] INFO:   AEGIS1 BRIDGE SERVER STARTING
2026-02-15 12:00:00 [aegis1] INFO: ============================================================
2026-02-15 12:00:00 [aegis1] INFO:   LLM: Ollama (local testing)    ← Shows selected mode
2026-02-15 12:00:00 [aegis1] INFO:   Server: 0.0.0.0:8000
2026-02-15 12:00:00 [aegis1] INFO:   mDNS Discovery: aegis1.local:8000
2026-02-15 12:00:00 [aegis1] INFO:   Dashboard: http://localhost:8000/
2026-02-15 12:00:00 [aegis1] INFO: ============================================================
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🔍 PART 6: Verify ESP32 Connection

### Step 6A: Open Serial Monitor

**In Arduino IDE:**
1. **Tools → Serial Monitor** (or Ctrl+Shift+M)
2. **Speed: 9600** (bottom right)

**You should see:**
```
ESP32 AEGIS1 Pendant Startup
============================
Connecting to WiFi: YOUR_WIFI_NETWORK...
.......
✓ Connected! IP: 192.168.1.100
Initializing mDNS...
Discovering aegis1 service via mDNS...
✓ Found server: 192.168.1.50:8000
Connecting to WebSocket: ws://192.168.1.50:8000/ws/audio
✓ WebSocket connected to AEGIS1
Setup complete!
```

**If you see "✓ WebSocket connected" → SUCCESS! ✅**

### Step 6B: Check Dashboard

1. Open browser: **http://localhost:8000/**
2. You should see:
   - **AEGIS1 Dashboard**
   - **Health Summary** (empty until you use it)
   - **Ready for audio input**

---

## 🎤 PART 7: Test Audio Pipeline

### Step 7A: Speak Into Microphone

1. **Talk into the INMP441 microphone** (say something like "Hello AEGIS")
2. ESP32 will:
   - Send PCM audio to server
   - Server processes it
   - Shows "processing" state

### Step 7B: Listen for Response

1. **Speaker should play response** (Piper TTS voice)
2. Check Serial Monitor for:
   ```
   STT [850ms]: Hello AEGIS
   LLM response: [response text]
   TTS [120ms]: 3200 bytes
   ```

### Step 7C: Check Dashboard

1. Refresh browser: http://localhost:8000/
2. Should show:
   - **User message:** "Hello AEGIS"
   - **Assistant response:** [Ollama/Claude response]
   - **Latency:** STT, LLM, TTS times

---

## ✅ TROUBLESHOOTING

### Problem: No port appears in Arduino IDE

**Solution:**
1. Install USB driver: `ch340` or `cp2102` (check your ESP32 board)
2. Restart Arduino IDE
3. Reconnect ESP32 USB cable

### Problem: "Failed to connect to ESP32"

**Solution:**
1. Press and hold **BOOT button** (GPIO 0)
2. Press **RST button** while holding BOOT
3. Wait 2 seconds, release both
4. Try upload again

### Problem: "WebSocket connection failed" in Serial Monitor

**Solution:**
1. Check server is running: `python3 -m bridge.main`
2. Check server port: Should be 8000
3. Check WiFi: ESP32 and laptop on same network?
4. Check mDNS: Run `nslookup aegis1.local` on laptop

### Problem: "No audio response"

**Solution:**
1. Check speaker connections (especially IN+ and GND)
2. Test with: `curl http://localhost:8000/health`
3. Check latency: Look at STT/LLM/TTS times in Serial Monitor
4. Try speaking louder/clearer into microphone

### Problem: Microphone not working

**Solution:**
1. Double-check GPIO connections:
   - BCLK → GPIO 13 ✓
   - LRCLK → GPIO 14 ✓
   - DIN → GPIO 33 ✓
   - GND → GND ✓
   - 3.3V → 3.3V ✓
2. Try different microphone (if possible)
3. Check I2S configuration in firmware

### Problem: "Ollama not responding" error

**Solution:**
1. Start Ollama in separate terminal: `ollama serve`
2. Check it's running on port 11434
3. Or switch to Claude mode (unset USE_LOCAL_MODEL)

---

## 📊 QUICK REFERENCE

| Step | What | Command/Action |
|------|------|---|
| 1 | Wire hardware | Connect microphone & speaker per diagram |
| 2 | Get firmware | `from bridge.esp32_config import ESP32_FIRMWARE_SNIPPET` |
| 3 | Setup Arduino | Install ESP32 board support |
| 4 | Flash firmware | Tools → Upload |
| 5 | Start server | `python3 -m bridge.main` |
| 6 | Check connection | Serial Monitor should show "✓ WebSocket connected" |
| 7 | Test audio | Speak into mic, hear response from speaker |

---

## 🎉 Success Indicators

✅ You've succeeded when you see:

1. **Serial Monitor:**
   ```
   ✓ Connected! IP: 192.168.1.100
   ✓ Found server: 192.168.1.50:8000
   ✓ WebSocket connected to AEGIS1
   ```

2. **Server Log:**
   ```
   ESP32 connected: 192.168.1.100:12345
   STT [850ms]: [your speech]
   LLM [1200ms]: [response]
   TTS [150ms]: [audio bytes]
   ```

3. **Audio:**
   - Speaker plays response
   - Voice is clear and natural

4. **Dashboard:**
   - Shows your message
   - Shows assistant response
   - Latency metrics visible

---

## 🚀 Next Steps After Success

1. **Optimize latency** (reduce silence detection threshold)
2. **Add button controls** (GPIO 0 for end-of-speech)
3. **Switch to Claude** for production quality
4. **Test with different queries** to verify tool use
5. **Fine-tune audio levels** for better microphone sensitivity

---

**Total Setup Time:** 20-30 minutes

**Success Rate:** 95% if connections are correct

Good luck! 🎤✨
