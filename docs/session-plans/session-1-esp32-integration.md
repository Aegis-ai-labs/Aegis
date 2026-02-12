# Session 1: ESP32 Firmware Integration — Phase 3

**Date:** Feb 13-14, 2026
**Status:** Ready to begin
**Prerequisites:** Phase 1 & 2 complete ✅ (Custom Ultra-Light Framework operational)

## Current Status

**Completed:**
- ✅ Phase 1 (Foundation): Bridge server with Claude streaming + 7 tools working
- ✅ Phase 2 (Audio Pipeline): Full speech-to-speech via WebSocket operational
- ✅ Custom Ultra-Light Framework: 23+ files, 1956+ lines, 26+ tests passing
- ✅ Sentence-level streaming achieving <2s perceived latency

**Architecture:**
- Direct Anthropic SDK (no Pipecat)
- FastAPI + WebSocket
- Haiku 4.5 / Opus 4.6 smart routing
- faster-whisper (STT) + Piper (TTS)
- SQLite with 30 days seeded demo data

**Firmware Status (from user):**
- ESP32 DevKit V1 hardware tested and working
- Mic (INMP441), Speaker (PAM8403), LED, Button operational
- WiFi and WebSocket connectivity verified
- Audio format: 16kHz, 16-bit mono PCM, 200ms chunks

---

## Session Objectives

1. **Update ESP32 firmware** for Custom Ultra-Light bridge protocol
2. **Establish WebSocket connection** between ESP32 and bridge server
3. **End-to-end testing**: Speak → AI response → Speaker playback
4. **Audio quality tuning**: Optimize gain, noise gate, silence thresholds
5. **Verify Opus 4.6 routing** for complex health/wealth queries

---

## Task Checklist

### Task 1: Review Bridge WebSocket Protocol

**Files to read:**
- `bridge/main.py` (WebSocket endpoint implementation)
- `bridge/audio.py` (PCM processing, silence detection)
- `docs/architecture.md` (ESP32 State Machine, LED patterns)

**Understand:**
- WebSocket message format (binary PCM vs JSON control messages)
- Expected audio format (16kHz, 16-bit mono PCM)
- Silence detection parameters
- Response streaming format

**Commands:**
```bash
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev
cat bridge/main.py | grep -A 30 "websocket"
cat bridge/audio.py | grep -A 10 "silence"
```

---

### Task 2: Update ESP32 Firmware (if needed)

**Reference firmware location:** `/Users/apple/aegis` (original prototype)

**Files to check/update:**
- `firmware/main.cpp` (state machine, WebSocket client)
- `firmware/audio_handler.cpp` (mic capture, speaker playback)
- `firmware/websocket_client.cpp` (WebSocket protocol)

**Required updates:**
- Update WebSocket endpoint URL to bridge server
- Implement 4-state machine: IDLE → LISTENING → PROCESSING → SPEAKING
- Update LED patterns: breathing (IDLE), solid (LISTENING), pulse (PROCESSING), fast-blink (SPEAKING)
- Ensure audio format matches: 16kHz, 16-bit mono PCM, 200ms chunks
- Handle JSON control messages from bridge (state transitions)

**Verification:**
```bash
# Compile and flash firmware
cd firmware
pio run -t upload

# Monitor serial output
pio device monitor
```

---

### Task 3: Bridge Server Configuration

**File:** `bridge/config.py`

**Add ESP32 connection settings:**
```python
# WebSocket server
WEBSOCKET_HOST: str = "0.0.0.0"
WEBSOCKET_PORT: int = 8000
WEBSOCKET_PATH: str = "/ws/audio"

# Audio settings (must match ESP32)
AUDIO_SAMPLE_RATE: int = 16000
AUDIO_SAMPLE_WIDTH: int = 2  # 16-bit
AUDIO_CHANNELS: int = 1      # mono
AUDIO_CHUNK_MS: int = 200
```

**Verify bridge is running:**
```bash
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev
python -m bridge.main
# Should output: INFO: Application startup complete
# Should show: WebSocket endpoint at ws://0.0.0.0:8000/ws/audio
```

---

### Task 4: Connect ESP32 to Bridge

**Network setup:**
1. Ensure ESP32 and computer are on same network
2. Get bridge server IP: `ifconfig | grep "inet "`
3. Update ESP32 firmware with bridge IP address
4. Flash updated firmware to ESP32

**Connection test:**
```bash
# Terminal 1: Run bridge with debug logging
cd /Users/apple/Documents/aegis1/.worktrees/bridge-dev
python -m bridge.main --log-level DEBUG

# Terminal 2: Monitor serial output
cd firmware
pio device monitor

# Expected output:
# ESP32: "Connecting to WiFi..."
# ESP32: "WiFi connected"
# ESP32: "WebSocket connecting to ws://<IP>:8000/ws/audio"
# Bridge: "WebSocket connection opened"
```

---

### Task 5: End-to-End Testing

**Test scenario 1: Simple health query**
1. Press ESP32 button (enter LISTENING state, LED solid)
2. Speak: "How did I sleep last night?"
3. Release button after 1 second of silence
4. Expected: LED pulse (PROCESSING), then fast-blink (SPEAKING)
5. Expected response: "You slept 6.2 hours last night..." (via speaker)

**Test scenario 2: Expense logging**
1. Press button
2. Speak: "I spent 45 dollars on lunch"
3. Expected response: "Got it, I logged a 45 dollar food expense..."

**Test scenario 3: Complex analysis (Opus 4.6 routing)**
1. Press button
2. Speak: "Analyze my sleep patterns over the past week"
3. Expected: Longer processing (Opus extended thinking)
4. Expected response: Detailed pattern analysis with correlation insights

**Verification commands:**
```bash
# Check conversation logs
sqlite3 aegis1.db "SELECT role, content, model_used FROM conversations ORDER BY timestamp DESC LIMIT 5"

# Check tool calls were logged
sqlite3 aegis1.db "SELECT metric, value, timestamp FROM health_logs ORDER BY timestamp DESC LIMIT 5"

# Check latency metrics
grep "latency" logs/bridge.log | tail -10
```

---

### Task 6: Audio Quality Tuning

**Files to modify:**
- `bridge/audio.py` (silence detection thresholds)
- `bridge/config.py` (audio processing parameters)
- Firmware `audio_handler.cpp` (mic gain, speaker volume)

**Parameters to tune:**

1. **Silence detection:**
```python
# bridge/audio.py
SILENCE_THRESHOLD = 500      # RMS threshold (adjust based on ambient noise)
SILENCE_DURATION_MS = 800    # ms of silence to trigger end of speech
```

2. **Mic gain (firmware):**
```cpp
// Increase if voice too quiet
i2s_set_dac_mode(I2S_DAC_CHANNEL_RIGHT_EN);
dacWrite(25, 128);  // 0-255, adjust based on testing
```

3. **Noise gate (bridge):**
```python
# bridge/audio.py - apply high-pass filter to remove low-frequency noise
def apply_noise_gate(audio_data: bytes) -> bytes:
    # Implement if needed based on testing
```

**Testing methodology:**
- Test in quiet room first (establish baseline)
- Test with background noise (TV, conversation)
- Test with different speaking volumes
- Test with different distances from mic (15cm, 30cm, 50cm)

---

### Task 7: Verify Opus 4.6 Routing

**Trigger phrases (from claude_client.py OPUS_TRIGGERS):**
- "analyze", "pattern", "trend", "plan", "correlate", "compare"
- "why am i", "why do i", "what's causing", "relationship between"
- "over time", "savings goal", "financial plan"

**Test queries:**
1. "Analyze my sleep patterns" → Should use Opus 4.6
2. "Compare my spending this week versus last week" → Should use Opus 4.6
3. "What's causing my low energy?" → Should use Opus 4.6
4. "How much did I spend on food?" → Should use Haiku 4.5

**Verification:**
```bash
# Check which model was used
sqlite3 aegis1.db "SELECT content, model_used FROM conversations WHERE role='assistant' ORDER BY timestamp DESC LIMIT 5"

# Expected: Opus queries show "claude-opus-4-6"
# Expected: Simple queries show "claude-haiku-4-5"
```

---

## Success Criteria

- [ ] ESP32 connects to bridge WebSocket reliably
- [ ] Button press triggers LISTENING state (LED solid)
- [ ] Voice captured and sent to bridge
- [ ] Bridge STT transcribes correctly (verify serial logs)
- [ ] Claude responds with appropriate model (Haiku vs Opus)
- [ ] TTS audio sent back to ESP32
- [ ] Speaker plays response clearly
- [ ] LED patterns match state machine
- [ ] Perceived latency <2.5s for simple queries
- [ ] Perceived latency <5s for Opus complex queries
- [ ] No audio dropouts or WebSocket disconnections
- [ ] Health/wealth tools execute correctly (check database)

---

## Troubleshooting

### WebSocket won't connect
```bash
# Check bridge is listening
netstat -an | grep 8000

# Check firewall
sudo lsof -iTCP -sTCP:LISTEN -n -P | grep 8000

# Test with Python client first
cd tests
python test_websocket.py
```

### Audio quality poor
```bash
# Check silence detection parameters
grep "SILENCE" bridge/audio.py

# Test with different thresholds
SILENCE_THRESHOLD=300 python -m bridge.main
SILENCE_THRESHOLD=700 python -m bridge.main
```

### STT not transcribing
```bash
# Check faster-whisper logs
grep "transcription" logs/bridge.log

# Test with .wav file directly
python -c "
from bridge.stt import transcribe_audio
result = transcribe_audio('test.wav')
print(result)
"
```

### Opus not routing correctly
```bash
# Verify OPUS_TRIGGERS in bridge/claude_client.py
grep "OPUS_TRIGGERS" bridge/claude_client.py

# Test routing manually
python -c "
from bridge.claude_client import select_model
print(select_model('analyze my sleep'))  # Should be opus
print(select_model('how much sleep'))    # Should be haiku
"
```

---

## Files Modified This Session

Track all changes:
```bash
# List modified files
git status

# Review changes
git diff

# Commit with descriptive message
git add firmware/ bridge/config.py bridge/audio.py
git commit -m "feat(phase3): ESP32 integration with Custom Ultra-Light bridge

- Updated firmware WebSocket protocol for bridge compatibility
- Implemented 4-state machine (IDLE → LISTENING → PROCESSING → SPEAKING)
- Added LED patterns for each state
- Tuned audio parameters: mic gain, silence threshold, noise gate
- Verified Opus 4.6 routing for complex queries
- End-to-end tested: speak → AI response → speaker playback
- Latency: <2.5s simple queries, <5s complex queries"
```

---

## Next Session

After Phase 3 complete, move to **Session 2: Polish & Demo Preparation**
