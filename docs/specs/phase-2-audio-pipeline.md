# Phase 2 Specification — Audio Pipeline

**Goal:** Full speech-to-speech working via WebSocket
**Timeline:** Feb 13 (Day 2)
**Depends on:** Phase 1 verified

---

## Scope

Add audio processing to the Phase 1 intelligence layer:
1. Receive raw PCM audio via WebSocket
2. Convert to text via faster-whisper
3. Process through Claude (already built in Phase 1)
4. Convert response to speech via Piper TTS
5. Stream audio back via WebSocket

---

## Components

### 1. Audio Processing — `bridge/audio.py`

Four functions, all operating on raw bytes:

| Function | Input | Output | Purpose |
|----------|-------|--------|---------|
| `pcm_to_wav(pcm_data, sample_rate, channels)` | Raw PCM bytes | WAV bytes | STT needs WAV format |
| `wav_to_pcm(wav_data)` | WAV bytes | Raw PCM bytes (or None) | Extract PCM from WAV |
| `detect_silence(pcm_chunk, threshold=500)` | PCM chunk | bool | End-of-speech detection |
| `calculate_rms(pcm_chunk)` | PCM chunk | float | Audio level monitoring |

**Audio format:** 16kHz, 16-bit signed, mono, little-endian.

**Silence detection:** Average absolute amplitude of all samples < threshold (default 500).

### 2. Speech-to-Text — `bridge/stt.py`

**Pattern:** Lazy singleton model loading.

```python
_model = None  # Loaded on first use

def _get_model():
    # Load WhisperModel once, with int8/cpu or float16/cuda
    ...

def transcribe_wav(audio_wav_bytes) -> Optional[str]:
    # Write to temp file → model.transcribe() → join segments → return text
    ...
```

**Configuration:**
- Model: `settings.stt_model` (default "base")
- Device: `settings.stt_device` (default "cpu")
- Compute type: int8 (CPU) or float16 (GPU)
- Language: `settings.stt_language` (default "en")
- VAD filter: always enabled
- Beam size: `settings.stt_beam_size` (needs to be added to config)

**Graceful degradation:** If `faster-whisper` not installed, `FASTER_WHISPER_AVAILABLE = False` and `transcribe_wav` returns `None`.

### 3. Text-to-Speech — `bridge/tts.py`

**Class:** `TTSEngine`

Two synthesis methods with automatic fallback:

1. **Piper Python API** (preferred) — Uses `PiperVoice.load()` if model path configured
2. **Piper CLI** (fallback) — Runs `piper --output-raw` subprocess

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `synthesize(text)` | Text string | PCM bytes (or None) | Single utterance |
| `synthesize_sentences(text)` | Text string | List of PCM bytes | Pre-split for streaming |

**Output format:** Raw 16-bit PCM (Piper's native format when using `--output-raw`).

### 4. WebSocket Server — `bridge/main.py`

**Endpoints:**
- `GET /health` → `{"status": "healthy", "version": "0.1.0"}`
- `GET /api/status` → Connection count + latency stats (avg/min/max per stage)
- `WS /ws/audio` → Audio streaming endpoint

**WebSocket protocol:**

ESP32 → Bridge:
- Binary: PCM audio chunks (~6400 bytes each)
- JSON: `{"type": "end_of_speech"}` or `{"type": "reset"}`

Bridge → ESP32:
- Binary: TTS PCM audio (chunked at 6400 bytes, 10ms between chunks)
- JSON: Status messages (`connected`, `status`, `done`)

**Connection lifecycle:**
1. Accept connection, send `{"type": "connected", ...}`
2. Buffer incoming PCM bytes
3. Detect end-of-speech (8 silent chunks OR explicit `end_of_speech` message OR 10s timeout)
4. Run `process_pipeline()`
5. Send `{"type": "idle"}`, wait for next utterance

### 5. Pipeline Orchestrator — `process_pipeline()` in `bridge/main.py`

The sentence-level streaming design:

```
pcm_to_wav(audio) → transcribe_wav(wav) → claude.get_response(text) → ...
                                                    │
                                    for each text chunk:
                                         │
                                    buffer += chunk
                                         │
                                    split on sentence boundary (. ! ?)
                                         │
                              ┌──── complete sentences ────┐
                              │                            │
                        tts.synthesize()             keep incomplete
                              │                      part in buffer
                        send PCM chunks
                        to ESP32
```

**Latency logging:** `stt`, `llm`, `tts`, `perceived` (end-of-speech → first audio sent), `total`.

---

## Latency Targets

| Stage | Target | Notes |
|-------|--------|-------|
| STT | <300ms | base model, beam_size=1, VAD filter |
| Claude first token | <200ms | Haiku 4.5 streaming |
| TTS per sentence | <150ms | Piper local |
| Perceived (speech → first audio) | <750ms | Sentence-level streaming |
| Full pipeline | <2.0s | Including all TTS sentences |

---

## Verification Plan

```bash
# Test 1: Audio module
python -c "
from bridge.audio import pcm_to_wav, wav_to_pcm, detect_silence
import struct

# Create 1s of silence
silence = struct.pack('<' + 'h' * 16000, *([0] * 16000))
wav = pcm_to_wav(silence)
assert len(wav) > 44  # WAV header + data
assert detect_silence(silence)

# Create 1s of tone
import math
tone = struct.pack('<' + 'h' * 16000, *[int(10000 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(16000)])
assert not detect_silence(tone)
print('Audio module OK')
"

# Test 2: STT (requires faster-whisper installed)
python -c "
from bridge.stt import transcribe_wav, FASTER_WHISPER_AVAILABLE
print(f'faster-whisper available: {FASTER_WHISPER_AVAILABLE}')
# Full test requires a real WAV file
"

# Test 3: TTS (requires piper-tts installed)
python -c "
from bridge.tts import TTSEngine
engine = TTSEngine()
pcm = engine.synthesize('Hello world')
print(f'TTS output: {len(pcm) if pcm else 0} bytes')
"

# Test 4: Full pipeline via WebSocket
python -c "
import asyncio, websockets, json, struct

async def test():
    async with websockets.connect('ws://localhost:8000/ws/audio') as ws:
        # Read connected message
        msg = json.loads(await ws.recv())
        print(f'Connected: {msg}')

        # Send 2s of audio (would need real recorded audio)
        # Then send end_of_speech
        await ws.send(json.dumps({'type': 'end_of_speech'}))

        # Read response
        while True:
            data = await asyncio.wait_for(ws.recv(), timeout=10)
            if isinstance(data, str):
                msg = json.loads(data)
                print(f'JSON: {msg}')
                if msg.get('type') == 'done':
                    break
            else:
                print(f'Audio: {len(data)} bytes')

asyncio.run(test())
"
```
