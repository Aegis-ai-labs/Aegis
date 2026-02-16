# AEGIS1 Hardware Setup - Quick Checklist

**Estimated Time:** 25-35 minutes

---

## ✅ WIRING CHECKLIST

### INMP441 Microphone to ESP32
- [ ] GND (pin 6)   → ESP32 GND
- [ ] 3.3V (pin 2)  → ESP32 3.3V
- [ ] BCLK (pin 5)  → ESP32 GPIO 13
- [ ] LRCLK (pin 3) → ESP32 GPIO 14
- [ ] DIN (pin 1)   → ESP32 GPIO 33
- [ ] L/R (pin 4)   → ESP32 GND

### PAM8403 Speaker Amp to ESP32
- [ ] GND           → ESP32 GND
- [ ] VCC (5V)      → USB 5V Power
- [ ] IN+           → GPIO 25 (with 10k resistor)
- [ ] IN-           → ESP32 GND
- [ ] Speaker       → Amp right channel (R+ and R-) for mono

---

## 📝 SOFTWARE STEPS

### STEP 1: Get Firmware Code
```bash
cd /Users/apple/Documents/aegis1
python3 -c "from bridge.esp32_config import ESP32_FIRMWARE_SNIPPET; print(ESP32_FIRMWARE_SNIPPET)"
```

### STEP 2: Update WiFi (CRITICAL!)
Find these lines around 15-16:
```cpp
const char* WIFI_SSID = "YOUR_NETWORK";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
```

### STEP 3: Arduino IDE
- Arduino → Preferences
- Add: https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
- Tools → Board Manager → Search "esp32" → Install
- Tools → Board → ESP32 Dev Module
- Tools → Port → /dev/cu.usbserial-XXXX
- Tools → Upload Speed → 921600

### STEP 4: Flash Firmware
- Sketch → Verify (check no errors)
- Hold BOOT button
- Press RST while holding BOOT (2 seconds)
- Sketch → Upload
- Wait for: "Leaving... Hard resetting..."

### STEP 5: Start Server (New Terminal)
**For FREE testing:**
```bash
export USE_LOCAL_MODEL=true
python3 -m bridge.main
```

**For Production:**
```bash
python3 -m bridge.main
```

### STEP 6: Check Connection
- Arduino → Tools → Serial Monitor
- Set speed: 9600
- Look for: "WebSocket connected to AEGIS1"

### STEP 7: Test!
- Speak into microphone
- Listen for speaker response
- Check: http://localhost:8000/

---

## ✨ SUCCESS SIGNS

### Serial Monitor should show:
```
Connected! IP: 192.168.x.x
Found server: 192.168.x.x:8000
WebSocket connected to AEGIS1
```

### Then:
- [ ] Speaker plays your response
- [ ] Dashboard shows message
- [ ] Latency metrics visible

---

## 🔧 QUICK FIXES

### No port in Arduino?
→ Restart IDE, check USB driver

### Upload fails?
→ Hold BOOT, press RST, try again

### WiFi won't connect?
→ Check SSID/password (case-sensitive!)

### No audio response?
→ Check all speaker wires

### "Server not found"?
→ Run: `nslookup aegis1.local`

### Ollama error?
→ Run: `ollama serve` (in another terminal)

---

## ⏱️ TIMING

- Wiring:        10-15 minutes
- Arduino Setup: 5 minutes
- Firmware:      2-3 minutes
- Server:        5 seconds
- Connection:    5-10 seconds
- **TOTAL:       25-35 minutes**

---

## 🎯 Success Checklist

- [ ] All wires connected
- [ ] Firmware code obtained
- [ ] WiFi credentials updated
- [ ] Arduino IDE configured
- [ ] Firmware compiled without errors
- [ ] ESP32 in download mode
- [ ] Firmware uploaded successfully
- [ ] Server started
- [ ] Serial monitor shows "WebSocket connected"
- [ ] Dashboard loads
- [ ] Audio test successful (microphone input → speaker output)

---

**Good luck! 🎤**
