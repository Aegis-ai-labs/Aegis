# ESP32 Connection Guide

## Hardware Setup (Tested Working)
- **Board:** ESP32 DevKit V1
- **Mic (INMP441):** BCLK=GPIO13, LRCLK=GPIO14, DIN=GPIO33
- **Speaker (PAM8403):** DAC1=GPIO25
- **LED:** GPIO2
- **Button:** GPIO0 (BOOT)

## Bridge Server Connection

### 1. Start Bridge Server
```bash
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev
source .venv/bin/activate
python -m bridge.main
```

Server starts on `ws://localhost:8000/ws/audio`

### 2. ESP32 Configuration
Update ESP32 firmware with:
- Bridge server IP (get from `ifconfig en0 | grep inet`)
- WebSocket URL: `ws://<YOUR_IP>:8000/ws/audio`

### 3. Test Connection
1. Press BOOT button on ESP32
2. Speak: "How did I sleep this week?"
3. ESP32 should:
   - Play listening chime
   - Stream audio to bridge
   - Receive thinking tone
   - Play AI response
   - Play success chime

### 4. Dashboard Monitoring
Open `http://localhost:8000` in browser to see:
- Live transcript
- Model used (Haiku vs Opus)
- Tool calls
- Latency metrics
- 7-day health chart

## Fallback: Laptop Audio
If ESP32 connection fails, use laptop mic+speaker:
```bash
python test_terminal.py
```
Still demonstrates:
- Claude streaming
- Tool use
- Model routing
- Body-aware responses

## Expected Behavior
- **Simple query** ("I spent $12 on coffee") → Haiku ~500ms → Tool call → Response
- **Complex query** ("Why am I tired on weekdays?") → Opus ~2s → Multiple tools → Deep analysis
- **Thinking visible** in logs when Opus analyzes patterns

## Troubleshooting
- **No connection:** Check IP address, verify ESP32 WiFi
- **No audio:** Check speaker gain, verify DAC output
- **Choppy audio:** Reduce chunk size or increase buffer
- **No response:** Check ANTHROPIC_API_KEY in .env
