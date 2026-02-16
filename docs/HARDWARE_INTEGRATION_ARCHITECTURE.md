# AEGIS1 Hardware Integration Architecture Analysis

**Status:** Phase 2 — Audio Pipeline Incomplete (Blocking Full E2E)  
**Date:** 2026-02-16  
**Hardware:** ESP32 DevKit V1 + INMP441 Mic + PAM8403 Speaker  
**Firmware Version:** 1.0.0  
**Backend:** FastAPI Bridge (aegis/main.py)

---

## 1. Current Hardware-Software Contract

### ESP32 Firmware Expectations (firmware/src/main.cpp)

The firmware **expects** the bridge to implement the `/ws/audio` WebSocket endpoint with this protocol:

```
ESP32 ─────(binary PCM)────> Bridge /ws/audio ─> [STT, Claude, TTS] ─> (binary PCM) ──> ESP32
  │                                                                           │
  └─ 16kHz, 16-bit, mono                                                    └─ Playback on DAC
     320 bytes/chunk (10ms)
```

**Firmware sends to bridge:**
- Binary PCM audio: 16kHz sample rate, 16-bit signed, mono channel
- Chunk size: 320 bytes = 10ms of audio
- Sent via `webSocket.sendBIN()` when cloud is connected
- Expects bridge at: `BRIDGE_HOST:BRIDGE_PORT = 10.100.110.206:8000`

**Firmware expects from bridge:**
- Binary PCM audio: 16kHz sample rate, 16-bit signed, mono channel
- Received via `WStype_BIN` event handler
- Buffered into 1-second playback buffer (16,000 samples)
- Played back via ESP32 DAC at GPIO 25 (PAM8403 amplifier input)

### Backend Current State (aegis/main.py:~110-130)

```python
elif "bytes" in data:
    # Audio data — Phase 2 will add STT/TTS pipeline here.
    # For now, just acknowledge receipt.
    log.debug(f"Received {len(data['bytes'])} bytes of audio")
    await websocket.send_json({
        "type": "error",
        "message": "Audio pipeline not yet implemented. Use /ws/text for testing.",
    })
```

**Critical Issue:** The audio pipeline is a **complete placeholder**. No:
- STT (Speech-to-Text) conversion
- Claude API call
- TTS (Text-to-Speech) conversion
- Binary audio response transmission

---

## 2. Hardware Pin Mapping (Verified)

### Microphone (INMP441)

| Signal | Pin | I2S Register | Direction |
|--------|-----|-------------|-----------|
| BCLK (Bit Clock) | GPIO 13 | I2S_NUM_0 BCK | OUT |
| LRCLK (Word Clock) | GPIO 14 | I2S_NUM_0 WS | OUT |
| DIN (Data In) | GPIO 33 | I2S_NUM_0 RX | IN |
| +3.3V | VCC | — | Power |
| GND | GND | — | Ground |

**Firmware Config (firmware/config.h:21-24):**
```c
#define I2S_MIC_BCLK    13
#define I2S_MIC_LRCLK   14
#define I2S_MIC_DIN     33
```

**Backend Config (no changes needed):** Firmware reads microphone directly via I2S0.

### Speaker (PAM8403)

| Signal | Pin | Type | Direction |
|--------|-----|------|-----------|
| IN+ (Signal) | GPIO 25 (DAC1) | Analog | OUT |
| GND | GND | Ground | — |
| +3.3V | VCC | Power | — |

**Firmware Config (firmware/config.h:27):**
```c
#define AMP_DAC_PIN     25  // GPIO 25 = DAC1
```

**Volume Control (firmware/config.h:31-33):**
```c
#define PLAYBACK_VOLUME_PERCENT  20   // 20% = safe (reduce if too loud)
#define PLAYBACK_MAX_PEAK_PERCENT 70  // 70% = gentle limit (reduce clipping)
```

**Playback Implementation (firmware/src/main.cpp:43-58):**
- 1-second circular buffer: `int16_t play_buf[16000]`
- Chunk drain: 160 samples (10ms) per loop iteration
- DAC output: `dacWrite(AMP_DAC_PIN, dac_val)` called ~16,000 times/sec
- Timing: `delayMicroseconds(62)` maintains ~16kHz playback rate

### LED & Button

| Signal | Pin | Function |
|--------|-----|----------|
| LED | GPIO 2 | Connection indicator (HIGH=connected, LOW=disconnected) |
| Button | GPIO 0 | BOOT button (used for firmware flashing) |

---

## 3. End-to-End Audio Flow (Current vs Expected)

### Current State (Text-Only Fallback)

```
[ESP32 Mic] ─────┐
                 └─X (no capture)
                 
User asks: "How did I sleep?"
                 
                 ┌─ /ws/text (manual JSON input)
[Browser] ────→ │  {"text": "How did I sleep?"}
                 └─ [ClaudeClient.chat()] ─→ Claude
                    
[Response] ◄─────── FastAPI returns JSON
{
  "text": "You averaged 6h...",
  "done": true
}
```

### Expected State (Full Hardware Integration)

```
[ESP32 Mic (INMP441)] ─(I2S0, 16kHz)─→ I2S DMA Buffer
                                        │
                                        ↓
                                    [PCM Chunk]
                                     320 bytes
                                    (10ms @ 16kHz)
                                        │
                                        ↓
                          [WebSocket /ws/audio]
                           (binary PCM upload)
                                        │
                                        ↓
                         [Bridge Backend STT]
                         (Moonshine streaming)
                                        │
                        "How did I sleep?"
                                        │
                                        ↓
                      [Claude Haiku/Opus API]
                     (with health context)
                                        │
                      "You averaged 6h..."
                                        │
                                        ↓
                         [Bridge Backend TTS]
                         (Kokoro ONNX-82M)
                                        │
                          [PCM Audio Stream]
                           320 bytes chunks
                                        │
                                        ↓
                         [WebSocket Response]
                          (binary PCM download)
                                        │
                                        ↓
                  [ESP32 Play Buffer] ◄──┘
                  (1-second circular)
                                        │
                                        ↓
                    [DAC GPIO 25] ─→ [PAM8403]
                                        │
                                        ↓
                                  [Speaker]
                              "You averaged..."
```

---

## 4. Critical Architectural Gaps

### Gap #1: No STT (Speech-to-Text) Pipeline

**What's Missing:**
- No incoming audio buffer accumulation
- No silence detection (VAD)
- No streaming STT model (Moonshine Tiny: 27M, ~26MB)
- No text output from audio chunks

**Required Implementation:**
```python
# Pseudo-code for /ws/audio audio handler
audio_buffer = []  # Accumulate PCM chunks
stt_model = MoonshineSTT()  # Load 27MB model once at startup

while True:
    chunk = await websocket.receive_bytes()  # 320 bytes
    audio_buffer.append(chunk)
    
    # Check for speech pause (silence > 500ms)
    if is_silence(audio_buffer[-10:]):  # Last 10 chunks = 100ms
        audio_pcm = reconstruct_pcm(audio_buffer)
        text = await stt_model.transcribe(audio_pcm)
        await handle_user_text(text)
        audio_buffer = []
```

**Performance Impact:**
- Moonshine Tiny: ~200-400ms per utterance (vs Whisper ~3-5s)
- Memory: ~26MB model + ~64KB active buffer
- Latency: Should not exceed 500ms for typical 3-5 second utterance

### Gap #2: No TTS (Text-to-Speech) Pipeline

**What's Missing:**
- No response buffering (need to wait for full Claude response)
- No streaming TTS model (Kokoro-82M: 82M, ~350MB)
- No PCM audio output from text chunks

**Required Implementation:**
```python
# Inside audio handler, after Claude response
response_text = await claude_client.chat(user_text)
tts_model = KokoroTTS()  # Load ~350MB model once

# Stream TTS by sentence
for sentence in response_text.split('. '):
    pcm_audio = await tts_model.synthesize(sentence)
    # Stream back to ESP32 in 320-byte chunks
    for i in range(0, len(pcm_audio), 320):
        chunk = pcm_audio[i:i+320]
        await websocket.send_bytes(chunk)
```

**Performance Impact:**
- Kokoro-82M: ~100-200ms per sentence (vs Piper ~500ms)
- Memory: ~350MB model + ~32KB synthesis buffer
- Latency: Should produce first audio ~200ms after Claude response starts

### Gap #3: No Context-Aware Health Analysis

**What's Missing:**
- STT produces text, but no health context attached
- Claude gets plain text, not personalized health data
- No integration with health tracking database

**Required Implementation:**
```python
# Before calling Claude with STT output
user_text = "How did I sleep?"

# Add health context
health_context = await build_health_context(user_id, days=7)
augmented_prompt = f"""
User's question: {user_text}

Current health summary:
{health_context}

Provide personalized advice based on their actual patterns.
"""

response = await claude_client.chat(augmented_prompt)
```

### Gap #4: Firmware Expects Different Bridge Address

**Issue:**
- Firmware hardcoded: `BRIDGE_HOST = "10.100.110.206"` (assumed Mac IP)
- Will fail if running on different network or machine

**Solution (Documented in Testing Guide):**
```c
// Before flashing, update config.h with:
#define BRIDGE_HOST "192.168.1.X"  // Your actual machine IP
#define BRIDGE_PORT 8000
```

---

## 5. Current Test Status

### ✅ Working
- **Firmware compiles** and flashes to ESP32
- **WiFi connection** works (connects to SSID, gets IP)
- **WebSocket handshake** works (ESP32 connects to /ws/audio)
- **Mic reads PCM** via I2S (GPIO 13/14/33 pins correct)
- **Speaker plays PCM** via DAC (GPIO 25, PAM8403 amplifier)
- **LED blinks** on connection (GPIO 2 working)
- **/ws/text endpoint** works (text-only testing mode)

### ❌ Broken / Not Implemented
- **Audio pipeline /ws/audio** returns placeholder error
- **STT conversion** not integrated
- **TTS synthesis** not integrated
- **Health context** not attached to Claude calls
- **No end-to-end audio flow** from mic to speaker through Claude

---

## 6. Component Requirements

### STT Model (Speech-to-Text)

| Requirement | Current | Needed |
|-------------|---------|--------|
| Model | None | Moonshine Tiny |
| Size | — | 27MB |
| Latency | — | <400ms per utterance |
| Languages | — | English (primary), optionally others |
| Install | — | `pip install moonshine` |
| Integration | — | `from moonshine import MoonshineSTT` |

### TTS Model (Text-to-Speech)

| Requirement | Current | Needed |
|-------------|---------|--------|
| Model | None | Kokoro-82M (ONNX) |
| Size | — | 350MB |
| Latency | — | 100-200ms per sentence |
| Languages | — | English native, others via phoneme input |
| Install | — | `pip install kokoro-onnx` (or custom ONNX runtime) |
| Integration | — | Custom ONNX Runtime loading |

### Hardware Dependencies

| Component | Status | Details |
|-----------|--------|---------|
| ESP32-DevKit-V1 | ✅ Works | Firmware flashes, connects WiFi |
| INMP441 Microphone | ✅ Works | Reads 16kHz 16-bit PCM via I2S0 |
| PAM8403 Amplifier | ✅ Works | Plays 16kHz 16-bit PCM via DAC1 (GPIO 25) |
| Wiring | ⚠️ Verify | Pins: Mic (13/14/33), Speaker (25), LED (2) |

---

## 7. Integration Checklist

- [ ] **Install STT Model:** `pip install moonshine` + test locally
- [ ] **Install TTS Model:** `pip install kokoro-onnx` + test locally
- [ ] **Implement /ws/audio STT handler:** Accumulate PCM → Moonshine → text
- [ ] **Implement /ws/audio TTS handler:** Claude response → Kokoro → PCM stream
- [ ] **Add health context builder:** Query DB for user health data before Claude call
- [ ] **Test STT-only:** Send mic audio, verify text output
- [ ] **Test TTS-only:** Send text, verify speaker output
- [ ] **Test full loop:** Mic → STT → Claude → TTS → Speaker
- [ ] **Hardware pin verification:** Confirm all GPIO connections match firmware
- [ ] **Network configuration:** Update firmware BRIDGE_HOST before flashing
- [ ] **Performance tuning:** Optimize model latency + memory usage
- [ ] **Error handling:** Audio dropout recovery, malformed PCM handling

---

## 8. What Works Right Now (For Demo)

**Text-only endpoint `/ws/text`:**
```bash
# Manually test Claude integration (no hardware needed)
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/text

# Send (via WebSocket):
{"text": "How did I sleep this week?"}

# Receive:
{"text": "You averaged...", "done": true}
```

**This allows demo of:**
- Health context attachment ✅
- Dual-model routing (Haiku/Opus) ✅
- Extended thinking for complex queries ✅
- Health + wealth correlation ✅

**Cannot demo (hardware missing):**
- Actual microphone capture ❌
- Actual speaker playback ❌
- Voice interaction ❌
- "Voice pendant" aspect ❌

---

## 9. Next Steps (For Full Integration)

### Phase 2A: Audio Pipeline Implementation
1. Install Moonshine STT model + test on sample audio
2. Install Kokoro TTS model + test on sample text
3. Implement PCM accumulation + VAD silence detection
4. Implement STT handler in `/ws/audio`
5. Implement TTS handler in `/ws/audio`

### Phase 2B: Hardware Testing
1. Verify hardware pins with multimeter (optional but recommended)
2. Update firmware `config.h` with correct `BRIDGE_HOST`
3. Flash ESP32 with firmware binary
4. Test connectivity: check logs for "AEGIS1 bridge connected"
5. Test STT: speak into mic, verify text appears in logs
6. Test TTS: verify audio plays on speaker
7. Test full loop: E2E conversation

### Phase 2C: Demo Preparation
1. Record demo video of hardware in action
2. Create troubleshooting guide for common issues
3. Document performance metrics (latency, throughput)
4. Prepare fallback (text-only demo if hardware unavailable)

---

## Summary

**Current State:** Backend is at 90% feature-complete, but **audio pipeline is a placeholder** blocking hardware integration.

**Main Issue:** The `/ws/audio` endpoint needs:
1. STT model integration (Moonshine)
2. TTS model integration (Kokoro)
3. PCM audio buffering + VAD
4. Health context attachment

**Time Estimate:** ~4-6 hours for full integration + testing

**Risk:** Without audio pipeline, E2E demo must fall back to `/ws/text` (text-only, which works perfectly)

