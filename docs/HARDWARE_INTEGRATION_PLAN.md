# HARDWARE INTEGRATION PLAN - AEGIS1 Audio Pipeline Implementation

**Phase:** Phase 2 (Audio Pipeline Implementation)  
**Timeline:** 8-12 hours total  
**Status:** Blocking full E2E hardware demo  
**Date:** 2026-02-16  
**Backend:** FastAPI Bridge (aegis/main.py:110-130)

---

## Current State

**What Works:**
- ✅ ESP32 firmware compiles and flashes
- ✅ WiFi connects
- ✅ WebSocket `/ws/audio` endpoint exists
- ✅ Text-only `/ws/text` endpoint works (health context, Claude API, dual-model routing)
- ✅ All 10 Claude tools implemented and tested
- ✅ Hardware pins verified (GPIO 13, 14, 33 for mic; GPIO 25 for speaker)

**What's Blocked:**
- ❌ `/ws/audio` endpoint returns placeholder error
- ❌ No STT (Speech-to-Text) model integrated
- ❌ No TTS (Text-to-Speech) model integrated
- ❌ No audio buffering or streaming logic
- ❌ E2E audio flow: Mic → Cloud → Speaker doesn't work

---

## Architecture: What Needs to be Built

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESP32 Firmware (Complete)                     │
│  I2S Mic (GPIO 13/14/33) → WebSocket → /ws/audio → DAC Speaker  │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Backend Bridge /ws/audio Handler               │
│                      (NEEDS IMPLEMENTATION)                      │
│                                                                  │
│  Step 1: Receive binary PCM ← Firmware sends 320-byte chunks   │
│           ↓                                                      │
│  Step 2: Buffer audio + VAD ← Accumulate until silence detected │
│           ↓                                                      │
│  Step 3: Run STT (Moonshine) ← Convert 3-5s audio → text       │
│           ↓                                                      │
│  Step 4: Query Claude API ← Chat with health context            │
│           ↓                                                      │
│  Step 5: Run TTS (Kokoro) ← Convert response → 16kHz PCM        │
│           ↓                                                      │
│  Step 6: Stream back PCM ← Send 320-byte chunks to firmware     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan (3 Phases, 12 Steps)

### PHASE 1: STT (Speech-to-Text) Integration - 4 hours

**Goal:** Convert captured audio from ESP32 into text

#### Step 1.1: Install & Test Moonshine STT Locally [0.5h]

**What:** Download and test Moonshine Tiny (27MB) speech recognition model

**Files to Create:**
- `tests/test_stt_moonshine.py` - Unit test for STT model

**Code:**
```python
# tests/test_stt_moonshine.py
import asyncio
from moonshine import MoonshineSTT
from aegis.audio import load_wav_16k

async def test_moonshine_inference():
    # Load model (27MB, downloads on first run)
    stt = MoonshineSTT("tiny")
    
    # Test with sample audio (create test_audio.wav with your voice)
    audio_16k = load_wav_16k("tests/audio_samples/test_audio.wav")
    
    # Run inference
    text = await stt.transcribe(audio_16k)
    
    assert "sleep" in text.lower() or len(text) > 0
    print(f"✓ STT working: {text}")
```

**Execution:**
```bash
cd /Users/apple/Documents/aegis1
pip install moonshine
# Create test_audio.wav with recorded speech
# Record 5 seconds of "How did I sleep this week"
python -m pytest tests/test_stt_moonshine.py -v
```

**Success Criteria:**
- Model loads in <2s on second run (cached)
- Transcription latency <400ms for 5-second audio
- Transcription accuracy >90% for clear speech

#### Step 1.2: Create Audio Buffering Module [1h]

**What:** Accumulate 320-byte PCM chunks into complete utterances using VAD

**Files to Create:**
- `aegis/audio_buffer.py` - PCM accumulation + silence detection

**Code Outline:**
```python
# aegis/audio_buffer.py
import numpy as np
from silero_vad import load_silero_vad

class AudioBuffer:
    def __init__(self, sample_rate=16000, silence_threshold_ms=500):
        self.sample_rate = sample_rate
        self.silence_threshold_samples = silence_threshold_ms * sample_rate // 1000
        self.buffer = []
        self.vad_model = load_silero_vad()
        self.silence_count = 0
    
    def add_chunk(self, pcm_bytes: bytes) -> tuple[bool, bytes]:
        """Add 320-byte chunk. Returns (is_utterance_complete, pcm_audio)"""
        # Convert bytes to int16 array
        pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
        self.buffer.append(pcm)
        
        # Check for silence using Silero VAD
        is_speech = self.vad_model(torch.from_numpy(pcm), self.sample_rate)
        
        if not is_speech:
            self.silence_count += 1
        else:
            self.silence_count = 0
        
        # If silence for 500ms, utterance is complete
        if self.silence_count >= self.silence_threshold_samples // 320:
            audio = np.concatenate(self.buffer)
            self.buffer = []
            self.silence_count = 0
            return (True, audio.tobytes())
        
        return (False, None)
```

**Tests to Add:**
- `tests/test_audio_buffer.py` - 3 tests:
  - Empty buffer returns no utterance
  - Continuous audio accumulates
  - Silence triggers utterance completion

**Success Criteria:**
- Buffer accumulates 320-byte chunks correctly
- VAD detects silence within 500ms
- No memory leaks with continuous audio

#### Step 1.3: Integrate STT into /ws/audio Handler [2.5h]

**What:** Update `aegis/main.py` `/ws/audio` endpoint to receive audio and run STT

**Files to Modify:**
- `aegis/main.py` - Replace audio handler placeholder

**Code Outline:**
```python
# aegis/main.py (replace lines 110-130)
from aegis.audio_buffer import AudioBuffer
from aegis.stt_module import STTModule

@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    """Audio WebSocket for ESP32 pendant."""
    await websocket.accept()
    client = ClaudeClient()
    audio_buf = AudioBuffer()
    stt = STTModule()  # Loads Moonshine on startup
    
    log.info("Audio WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive()
            
            if "bytes" in data:
                # Accumulate PCM audio
                is_complete, audio_pcm = audio_buf.add_chunk(data["bytes"])
                
                if is_complete:
                    # Run STT
                    text = await stt.transcribe(audio_pcm)
                    log.info(f"STT: {text}")
                    
                    # Query Claude
                    response = await client.chat(text)
                    log.info(f"Claude: {response}")
                    
                    # (Phase 2) TTS goes here
                    
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        log.info("Audio WebSocket disconnected")
```

**Tests:**
- `tests/test_audio_ws_stt.py` - Test /ws/audio receives binary, runs STT, returns text

**Success Criteria:**
- /ws/audio accepts binary audio
- Runs STT when silence detected
- Logs transcribed text
- <800ms latency (320ms buffering + 400ms STT + 80ms overhead)

---

### PHASE 2: TTS (Text-to-Speech) Integration - 4 hours

**Goal:** Convert Claude responses into audio and stream back to ESP32

#### Step 2.1: Install & Test Kokoro TTS Locally [0.5h]

**What:** Download and test Kokoro-82M (350MB) text-to-speech model

**Code:**
```python
# tests/test_tts_kokoro.py
import asyncio
from kokoro import KokoroTTS

async def test_kokoro_inference():
    # Load model (350MB)
    tts = KokoroTTS()
    
    # Synthesize text
    text = "You averaged six hours of sleep on weekdays versus seven hours on weekends."
    pcm_audio = await tts.synthesize(text)  # Returns 16kHz 16-bit PCM bytes
    
    assert len(pcm_audio) > 0
    # Expect ~5 seconds * 16k samples * 2 bytes = 160k bytes
    assert len(pcm_audio) > 100000
    print(f"✓ TTS working: {len(pcm_audio)} bytes generated")
```

**Execution:**
```bash
pip install kokoro  # Or kokoro-onnx depending on package
python -m pytest tests/test_tts_kokoro.py -v
```

**Success Criteria:**
- Model loads in <3s on second run
- Synthesis latency 100-200ms per sentence
- Audio quality is clear (no robotic artifacts)
- Output is correct sample rate (16kHz) and format (16-bit PCM)

#### Step 2.2: Create TTS Streaming Module [1h]

**What:** Chunk TTS output into 320-byte PCM chunks for ESP32

**Files to Create:**
- `aegis/tts_stream.py` - Stream TTS output

**Code Outline:**
```python
# aegis/tts_stream.py
class TTSStreamer:
    def __init__(self, sample_rate=16000, chunk_size=320):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size  # 10ms @ 16kHz
    
    async def stream_text(self, text: str, websocket):
        """Stream TTS output to WebSocket in 320-byte chunks."""
        tts = KokoroTTS()
        
        # Split by sentences for faster response start
        sentences = text.split('. ')
        
        for sentence in sentences:
            # Synthesize one sentence
            pcm = await tts.synthesize(sentence)
            
            # Stream in 320-byte chunks
            for i in range(0, len(pcm), self.chunk_size):
                chunk = pcm[i:i+self.chunk_size]
                await websocket.send_bytes(chunk)
                await asyncio.sleep(0.01)  # Rate limit to match playback speed
```

**Tests:**
- `tests/test_tts_stream.py` - Verify chunks are correct size

#### Step 2.3: Integrate TTS into /ws/audio Handler [2.5h]

**What:** Add TTS to audio handler after Claude response

**Files to Modify:**
- `aegis/main.py` - Add TTS to `/ws/audio`

**Code Outline:**
```python
# In /ws/audio handler, after Claude response
if is_complete:
    text = await stt.transcribe(audio_pcm)
    response = await client.chat(text)  # Gets response text
    
    # NEW: Stream TTS back to ESP32
    await tts_streamer.stream_text(response, websocket)
    
    log.info(f"TTS streamed {len(response)} chars")
```

**Tests:**
- `tests/test_audio_e2e.py` - Send mock audio, verify PCM response

**Success Criteria:**
- /ws/audio sends binary PCM back after Claude response
- Chunks are exactly 320 bytes (except last chunk)
- Total latency <2s (400ms STT + 500ms Claude + 200ms TTS + overhead)

---

### PHASE 3: Integration & Testing - 4 hours

**Goal:** Full end-to-end testing with real ESP32 hardware

#### Step 3.1: Hardware Connection Verification [1h]

**What:** Verify all GPIO pins are correctly wired

**Steps:**
1. Review firmware pin configuration (`firmware/config.h`)
2. Check physical wiring with multimeter (optional)
3. Flash firmware with correct BRIDGE_HOST
4. Monitor serial output

**Success Criteria:**
- Serial shows: `[OK] WiFi connected`
- Serial shows: `[OK] AEGIS1 bridge connected`
- Blue LED (GPIO 2) is ON

#### Step 3.2: STT-Only Testing [1h]

**What:** Test audio capture → STT pipeline without TTS

**Steps:**
1. Start backend
2. Monitor serial output
3. Speak into microphone for 3-5 seconds: "How did I sleep this week?"
4. Watch logs for STT transcription

**Expected Output:**
```
[OK] AEGIS1 bridge connected
[...] Recording audio...
[OK] STT: How did I sleep this week
```

**Success Criteria:**
- Audio is captured
- STT produces accurate transcription
- No crashes or disconnects

#### Step 3.3: Full E2E Testing [2h]

**What:** Complete audio pipeline: Mic → STT → Claude → TTS → Speaker

**Steps:**
1. Speak into microphone: "How did I sleep this week?"
2. Listen for audio response on speaker

**Expected Behavior:**
- 3-5s: Record audio (user speaking)
- 0.4s: STT converts audio to text
- 0.5s: Claude generates response
- 0.2s: TTS converts response to audio
- 2-5s: Speaker plays response

**Total Time:** ~7-13 seconds wall-clock

**Success Criteria:**
- Audio is captured correctly
- Response is played back clearly
- No audio dropouts or distortion
- Health context is used (response mentions specific sleep data)

#### Step 3.4: Demo Readiness [Optional final hour]

**What:** Prepare for live demonstration

**Steps:**
1. Test 3-5 different queries
2. Verify consistent performance
3. Record demo video
4. Prepare backup (text-only mode)

**Demo Queries:**
1. "How did I sleep this week?" → Should show sleep pattern analysis
2. "I spent $50 on coffee" → Should acknowledge expense, show budget context
3. "What's my budget status?" → Should show spending summary
4. "Help me train for a 5K" → Should combine health + wealth insights
5. "Tell me about yesterday" → Should summarize health data

---

## Dependency Management

### Required Python Packages

```bash
# STT
pip install moonshine

# TTS (choose one)
pip install kokoro
# OR
pip install kokoro-onnx

# VAD (Voice Activity Detection)
pip install silero-vad

# Existing (already installed)
pip install fastapi uvicorn
pip install anthropic
pip install numpy
```

### Model Download Sizes

| Model | Size | Download Time | Cache Location |
|-------|------|---------|--------|
| Moonshine Tiny | 27MB | ~30s | ~/.cache/moonshine |
| Kokoro-82M | 350MB | ~5min | ~/.cache/kokoro |
| Silero VAD | 4MB | ~10s | ~/.cache/silero_vad |

**Note:** Models are downloaded on first use and cached locally. Subsequent runs load from cache in <2s.

---

## Risk Assessment

### High Risk
- **Model latency:** If Moonshine takes >500ms or Kokoro >300ms, E2E latency will exceed 3 seconds (poor UX)
  - *Mitigation:* Test locally first, have fallback text-only mode
- **Memory overflow:** ESP32 has limited RAM (4MB). If TTS buffer grows too large, ESP32 may reset
  - *Mitigation:* Stream TTS in small chunks (320 bytes), don't buffer entire response

### Medium Risk
- **Audio dropout:** WiFi interference or WebSocket jitter could cause audio glitches
  - *Mitigation:* Add error handling, implement audio buffer underrun detection
- **Firmware changes needed:** If STT/TTS output format differs, firmware audio handler may break
  - *Mitigation:* Verify PCM format (16kHz, 16-bit, mono) matches firmware expectations

### Low Risk
- **Database queries:** Health context queries should be fast (<100ms)
  - *Mitigation:* Already tested and working

---

## Rollback Plan (If Integration Fails)

1. **Revert `/ws/audio` to text-only:** Keep /ws/text working, /ws/audio returns error (current state)
2. **Demo fallback:** Use `/ws/text` endpoint for hackathon demo (text WebSocket works perfectly)
3. **Document blocker:** Create HARDWARE_INTEGRATION_BLOCKER.md explaining what's needed

---

## Success Criteria

### Phase 1 Success: STT Working
- [ ] Moonshine model loads and runs locally
- [ ] /ws/audio accepts binary audio from ESP32
- [ ] Audio buffering works (accumulates chunks, detects silence)
- [ ] STT transcription is accurate (>90%)
- [ ] Latency <400ms for typical 3-5 second utterance
- [ ] Tests pass: 8/8 in `tests/test_stt_*.py`

### Phase 2 Success: TTS Working
- [ ] Kokoro model loads and runs locally
- [ ] /ws/audio sends binary PCM back to ESP32
- [ ] PCM format matches firmware expectations (16kHz, 16-bit, mono)
- [ ] Chunks are exactly 320 bytes (10ms)
- [ ] Audio quality is clear and understandable
- [ ] Latency 100-200ms per sentence
- [ ] Tests pass: 8/8 in `tests/test_tts_*.py`

### Phase 3 Success: Full E2E Working
- [ ] ESP32 captures audio from microphone
- [ ] STT converts audio to text
- [ ] Claude responds with health-aware answer
- [ ] TTS converts response to audio
- [ ] Speaker plays response clearly
- [ ] End-to-end latency <3 seconds (ideal) or <5 seconds (acceptable)
- [ ] 3+ queries tested and working

---

## Timeline Summary

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1.1 | Install & test Moonshine | 0.5h | Pending |
| 1.2 | Create audio buffering | 1h | Pending |
| 1.3 | Integrate STT handler | 2.5h | Pending |
| **Phase 1 Total** | **STT Complete** | **4h** | **Pending** |
| 2.1 | Install & test Kokoro | 0.5h | Pending |
| 2.2 | Create TTS streaming | 1h | Pending |
| 2.3 | Integrate TTS handler | 2.5h | Pending |
| **Phase 2 Total** | **TTS Complete** | **4h** | **Pending** |
| 3.1 | Hardware verification | 1h | Ready |
| 3.2 | STT-only testing | 1h | Ready |
| 3.3 | Full E2E testing | 2h | Pending |
| 3.4 | Demo prep (optional) | 1h | Optional |
| **Phase 3 Total** | **Testing Complete** | **4-5h** | **Pending** |
| **TOTAL** | **Full Hardware Integration** | **12-13h** | **8-12h remaining** |

---

## What to Do Next

### Option A: Implement Full Audio Pipeline (12 hours)
1. Do Phase 1 (STT) in parallel with Phase 2 (TTS)
2. Do Phase 3 (testing) once both are ready
3. Full E2E demo with real voice interaction

### Option B: Deliver Text-Only Demo (Now)
1. Current `/ws/text` endpoint works perfectly
2. Shows all AEGIS1 features (health context, dual-model routing, extended thinking)
3. Hardware is connected but using text fallback
4. Clearly explain "audio pipeline coming in Phase 2"

**Recommendation:** Deliver Option B for hackathon (guaranteed to work, impressive even without audio), Plan Option A for post-hackathon (hardware voice interaction is 12-hour sprint).

---

## References

- **Architecture Analysis:** `docs/HARDWARE_INTEGRATION_ARCHITECTURE.md`
- **Setup Guide:** `docs/HARDWARE_SETUP_AND_TESTING.md`
- **Current Code:** `aegis/main.py:110-130` (placeholder /ws/audio handler)
- **Firmware:** `firmware/src/main.cpp` (complete, just needs backend)

