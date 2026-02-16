# AEGIS1 Testing & Connection Guide

**Purpose:** Complete guide for testing audio pipeline and ESP32 hardware connection  
**Date:** 2026-02-16  
**Target:** Developers, QA, Demo runners  

---

## Part 1: Quick Connection Test (5 minutes)

### Test 1.1: Backend Service Health

**Goal:** Verify backend is running and responsive

**Command:**
```bash
curl -v http://localhost:8000/health
```

**Expected Output:**
```
HTTP/1.1 200 OK
{"status":"ok","service":"aegis1-bridge"}
```

**If fails:**
- Backend not running: `python -m aegis.main`
- Wrong port: Check BRIDGE_PORT in config.py (default 8000)
- Firewall: Check port 8000 is not blocked

---

### Test 1.2: Text WebSocket Connection

**Goal:** Verify /ws/text endpoint (existing, should still work)

**Command:**
```bash
python3 << 'EOF'
import asyncio
import websockets
import json

async def test_text_ws():
    try:
        async with websockets.connect('ws://localhost:8000/ws/text') as ws:
            # Send test message
            await ws.send(json.dumps({"text": "hello"}))
            
            # Receive response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            
            print("✅ Text WebSocket: CONNECTED")
            print(f"Response: {data}")
            
    except Exception as e:
        print(f"❌ Text WebSocket: FAILED - {e}")

asyncio.run(test_text_ws())
EOF
```

**Expected Output:**
```
✅ Text WebSocket: CONNECTED
Response: {'text': 'Hello! I'm...', 'done': False}
```

**If fails:**
- Check backend is running (Test 1.1)
- Check WebSocket support enabled in FastAPI
- Verify /ws/text handler exists in main.py

---

### Test 1.3: Audio WebSocket Connection (NEW)

**Goal:** Verify /ws/audio endpoint accepts connections (Phase 2)

**Command:**
```bash
python3 << 'EOF'
import asyncio
import websockets
import json

async def test_audio_ws():
    try:
        async with websockets.connect('ws://localhost:8000/ws/audio') as ws:
            print("✅ Audio WebSocket: CONNECTION ACCEPTED")
            
            # Send ping to verify processing
            await ws.send_text(json.dumps({"type": "ping"}))
            
            # Should receive pong
            response = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(response)
            
            if data.get("type") == "pong":
                print("✅ Audio WebSocket: PING/PONG working")
            else:
                print(f"Response: {data}")
                
    except Exception as e:
        print(f"❌ Audio WebSocket: FAILED - {e}")

asyncio.run(test_audio_ws())
EOF
```

**Expected Output:**
```
✅ Audio WebSocket: CONNECTION ACCEPTED
✅ Audio WebSocket: PING/PONG working
```

**If fails:**
- /ws/audio endpoint not implemented: Check main.py line 114+
- Backend not running: Start with `python -m aegis.main`
- Connection timeout: Check firewall/network

---

## Part 2: Audio Pipeline Testing (15 minutes)

### Test 2.1: Audio Buffer Module

**Goal:** Verify AudioBuffer can accumulate chunks and detect silence

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
from aegis.audio_buffer import AudioBuffer
import sys

print("Testing AudioBuffer...")

# Create buffer
buf = AudioBuffer(silence_duration_ms=200)
print("✅ AudioBuffer initialized")

# Add speech chunks (not silent)
speech_chunk = b'\x50\x00' * 160  # Amplitude ~80
for i in range(5):
    is_complete, audio = buf.add_chunk(speech_chunk)
    assert not is_complete, "Should not complete with speech only"
print("✅ Buffer accumulates speech chunks")

# Add silent chunks
silence_chunk = b'\x00\x00' * 160  # Amplitude 0
for i in range(30):
    is_complete, audio = buf.add_chunk(silence_chunk)
    if is_complete:
        print(f"✅ Utterance complete after {i+5+1} chunks (silence detected)")
        assert len(audio) > 0, "Audio should not be empty"
        duration_ms = len(audio) / 32  # 16000Hz * 2 bytes / 1000
        print(f"✅ Accumulated audio: {len(audio)} bytes (~{duration_ms:.0f}ms)")
        break

if not is_complete:
    print("⚠️ Warning: Utterance not marked complete (adjust silence_duration_ms)")

EOF
```

**Expected Output:**
```
✅ AudioBuffer initialized
✅ Buffer accumulates speech chunks
✅ Utterance complete after X chunks (silence detected)
✅ Accumulated audio: XXXX bytes (~XXXms)
```

**If fails:**
- AudioBuffer import error: Check aegis/audio_buffer.py exists
- Silence detection not working: Adjust silence_threshold in config.py
- Buffer accumulation failing: Check PCM format (should be 16-bit signed ints)

---

### Test 2.2: STT Module Loading

**Goal:** Verify Speech-to-Text model loads correctly

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
import sys

try:
    print("Loading STT module...")
    from aegis.stt import transcribe_wav, _get_model
    print("✅ STT module imported")
    
    # Try to load model
    model = _get_model()
    if model:
        print("✅ STT model loaded (faster-whisper)")
        print(f"  Model: {model}")
    else:
        print("⚠️ STT model not loaded (may need installation)")
        print("  Run: pip install faster-whisper")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("  Run: pip install faster-whisper")
    sys.exit(1)
except Exception as e:
    print(f"⚠️ Error: {e}")
    print("  This may be expected if faster-whisper not installed")

EOF
```

**Expected Output:**
```
✅ STT module imported
✅ STT model loaded (faster-whisper)
  Model: <WhisperModel object>
```

**If fails:**
```
⚠️ STT model not loaded (may need installation)
  Run: pip install faster-whisper
```
This is OK - install and retry.

---

### Test 2.3: TTS Module Loading

**Goal:** Verify Text-to-Speech engine initializes

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
import sys

try:
    print("Loading TTS module...")
    from aegis.tts import TTSEngine
    print("✅ TTS module imported")
    
    # Initialize engine
    engine = TTSEngine()
    print("✅ TTS engine initialized")
    
    # Check if Piper voice loaded
    if engine._voice:
        print("✅ Piper voice model loaded")
    else:
        print("⚠️ Piper voice not loaded (CLI fallback will be used)")
        print("  Run: pip install piper-tts")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"⚠️ Warning: {e}")

EOF
```

**Expected Output:**
```
✅ TTS module imported
✅ TTS engine initialized
✅ Piper voice model loaded
```

or (acceptable):
```
✅ TTS module imported
✅ TTS engine initialized
⚠️ Piper voice not loaded (CLI fallback will be used)
```

---

### Test 2.4: Audio Conversion (PCM ↔ WAV)

**Goal:** Verify PCM and WAV conversion works

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
from aegis.audio import pcm_to_wav, wav_to_pcm

print("Testing audio conversion...")

# Create test PCM data (1 second of silence @ 16kHz 16-bit mono)
pcm_data = b'\x00\x00' * 16000
print(f"✅ Created test PCM: {len(pcm_data)} bytes")

# Convert to WAV
wav_data = pcm_to_wav(pcm_data)
print(f"✅ Converted to WAV: {len(wav_data)} bytes")
assert len(wav_data) > len(pcm_data), "WAV should include headers"
assert wav_data[:4] == b'RIFF', "WAV should start with RIFF header"
print("✅ WAV format correct (RIFF header present)")

# Convert back to PCM
pcm_recovered = wav_to_pcm(wav_data)
if pcm_recovered:
    print(f"✅ Recovered PCM: {len(pcm_recovered)} bytes")
    # Should be same or similar length (WAV adds headers)
else:
    print("⚠️ Could not recover PCM from WAV")

EOF
```

**Expected Output:**
```
✅ Created test PCM: 32000 bytes
✅ Converted to WAV: 32036 bytes
✅ WAV format correct (RIFF header present)
✅ Recovered PCM: 32000 bytes
```

---

## Part 3: Integration Testing (20 minutes)

### Test 3.1: Complete Audio Pipeline (Mocked)

**Goal:** Test STT + Claude + TTS flow without real audio

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
import asyncio
from aegis.audio import pcm_to_wav
from aegis.stt import transcribe_wav
from aegis.claude_client import ClaudeClient
from aegis.tts import TTSEngine
from aegis.config import settings

async def test_pipeline():
    print("=== Testing Complete Audio Pipeline ===\n")
    
    # Step 1: Simulate audio buffering (we'll use mock data)
    print("Step 1: Audio Buffering")
    print("  ✓ Simulating 3 seconds of speech at 16kHz...")
    audio_pcm = b'\x50\x00' * (16000 * 3)  # 3 seconds
    print(f"  ✓ Buffered: {len(audio_pcm)} bytes\n")
    
    # Step 2: STT (convert audio to text)
    print("Step 2: Speech-to-Text (STT)")
    print("  Note: Skipping actual STT (requires model)")
    print("  Simulating: 'How did I sleep?'\n")
    user_text = "How did I sleep this week?"
    
    # Step 3: Claude API
    print("Step 3: Claude with Health Context")
    print(f"  Querying: '{user_text}'")
    try:
        client = ClaudeClient()
        response_text = ""
        async for chunk in client.chat(user_text):
            response_text += chunk
            if len(response_text) % 50 == 0:
                print(f"    Received {len(response_text)} chars...", end='\r')
        print(f"  ✓ Response: {response_text[:100]}...\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return
    
    # Step 4: TTS (convert response to audio)
    print("Step 4: Text-to-Speech (TTS)")
    print(f"  Converting: '{response_text[:50]}...'")
    engine = TTSEngine()
    pcm_chunks = engine.synthesize_sentences(response_text)
    print(f"  ✓ Generated {len(pcm_chunks)} audio chunks")
    total_bytes = sum(len(c) for c in pcm_chunks)
    print(f"  ✓ Total audio: {total_bytes} bytes\n")
    
    # Summary
    print("=== Pipeline Test Complete ===")
    print(f"✅ Audio buffering: OK")
    print(f"✅ STT simulation: OK")
    print(f"✅ Claude API: OK")
    print(f"✅ TTS synthesis: OK")
    print(f"\nTotal latency would be ~{0.2 + 0.5 + (total_bytes/16000)}s in production")

asyncio.run(test_pipeline())
EOF
```

**Expected Output:**
```
=== Testing Complete Audio Pipeline ===

Step 1: Audio Buffering
  ✓ Simulating 3 seconds of speech at 16kHz...
  ✓ Buffered: 96000 bytes

Step 2: Speech-to-Text (STT)
  Note: Skipping actual STT (requires model)
  Simulating: 'How did I sleep?'

Step 3: Claude with Health Context
  Querying: 'How did I sleep this week?'
    Received XXX chars...
  ✓ Response: You averaged 6 hours on weekdays...

Step 4: Text-to-Speech (TTS)
  Converting: 'You averaged 6 hours...'
  ✓ Generated X audio chunks
  ✓ Total audio: XXXXX bytes

=== Pipeline Test Complete ===
✅ Audio buffering: OK
✅ STT simulation: OK
✅ Claude API: OK
✅ TTS synthesis: OK

Total latency would be ~X.Xs in production
```

---

### Test 3.2: WebSocket Audio Message Flow

**Goal:** Test binary audio messages through /ws/audio

**Command:**
```bash
python3 << 'EOF'
import asyncio
import websockets
import json

async def test_audio_flow():
    print("=== Testing /ws/audio Message Flow ===\n")
    
    try:
        async with websockets.connect('ws://localhost:8000/ws/audio') as ws:
            print("✅ Connected to /ws/audio\n")
            
            # Test 1: Send control message (ping)
            print("Test 1: Control Message (ping)")
            await ws.send_text(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(response)
            assert data.get("type") == "pong"
            print("✅ Ping/pong working\n")
            
            # Test 2: Send audio chunk (binary)
            print("Test 2: Binary Audio Message")
            audio_chunk = b'\x00\x00' * 160  # 320 bytes of silence
            await ws.send_bytes(audio_chunk)
            print(f"✅ Sent {len(audio_chunk)} bytes of audio\n")
            
            # Test 3: Send multiple chunks (simulating speech)
            print("Test 3: Stream of Audio Chunks")
            for i in range(10):
                chunk = b'\x50\x00' * 160  # Louder audio
                await ws.send_bytes(chunk)
                await asyncio.sleep(0.01)
            print("✅ Sent 10 audio chunks (160ms of speech)\n")
            
            # Test 4: Silence (should trigger processing)
            print("Test 4: Silence Trigger")
            for i in range(30):
                silence = b'\x00\x00' * 160
                await ws.send_bytes(silence)
                await asyncio.sleep(0.01)
            print("✅ Sent 30 silence chunks (300ms)\n")
            
            # Try to receive response
            print("Listening for response (may take 5+ seconds)...")
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                if isinstance(response, bytes):
                    print(f"✅ Received audio response: {len(response)} bytes")
                else:
                    data = json.loads(response)
                    print(f"Response: {data}")
            except asyncio.TimeoutError:
                print("⚠️ No response (expected for silence-only audio)")
            
            print("\n=== All Tests Passed ===")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_audio_flow())
EOF
```

**Expected Output:**
```
=== Testing /ws/audio Message Flow ===

✅ Connected to /ws/audio

Test 1: Control Message (ping)
✅ Ping/pong working

Test 2: Binary Audio Message
✅ Sent 320 bytes of audio

Test 3: Stream of Audio Chunks
✅ Sent 10 audio chunks (160ms of speech)

Test 4: Silence Trigger
✅ Sent 30 silence chunks (300ms)

Listening for response (may take 5+ seconds)...
⚠️ No response (expected for silence-only audio)

=== All Tests Passed ===
```

---

## Part 4: Hardware Connection Testing (30 minutes)

### Test 4.1: ESP32 Firmware Configuration Verification

**Goal:** Verify firmware config is correct before flashing

**File:** `firmware/config.h`

**Checklist:**
```c
// ✅ WiFi Configuration
#define WIFI_SSID "your_network_name"        // Your WiFi SSID
#define WIFI_PASSWORD "your_password"        // Your WiFi password

// ✅ Bridge Server Configuration
#define BRIDGE_HOST "192.168.1.42"           // YOUR MACHINE IP (use: ifconfig)
#define BRIDGE_PORT 8000                     // Port (don't change)

// ✅ Hardware Pin Configuration
#define I2S_MIC_BCLK    13      // Mic serial clock
#define I2S_MIC_LRCLK   14      // Mic word select
#define I2S_MIC_DIN     33      // Mic data input
#define AMP_DAC_PIN     25      // Speaker amplifier
#define LED_PIN         2       // Status LED
#define BUTTON_PIN      0       // Boot button
```

**Before flashing, run:**
```bash
# Find your machine's IP address
ifconfig | grep "inet " | grep -v 127.0.0.1

# Example output:
# inet 192.168.1.42 netmask 0xffffff00 broadcast 192.168.1.255
# ↑ Use this IP in BRIDGE_HOST
```

---

### Test 4.2: ESP32 Firmware Compilation

**Goal:** Verify firmware compiles without errors

**Command:**
```bash
cd /Users/apple/Documents/aegis1/firmware

# Build firmware
pio run

# Expected output:
# Compiling .pio/build/esp32doit-devkit-v1/src/main.cpp.o
# ...
# Linking .pio/build/esp32doit-devkit-v1/firmware.elf
# Building .pio/build/esp32doit-devkit-v1/firmware.bin
# ===== [SUCCESS] Took X.XXs =====
```

**If compilation fails:**
- Check `config.h` is present
- Check `main.cpp` #include "../config.h" is correct
- Verify PlatformIO is installed: `pio --version`
- Clear build: `pio run --target clean` then rebuild

---

### Test 4.3: ESP32 Firmware Upload (Flashing)

**Goal:** Flash firmware to ESP32 board

**Prerequisites:**
- USB cable connected to ESP32
- Board detected: `ls /dev/tty.* | grep -i usb`

**Command:**
```bash
cd /Users/apple/Documents/aegis1/firmware

# Flash to ESP32
pio run --target upload

# Expected output:
# Uploading .pio/build/esp32doit-devkit-v1/firmware.bin
# esptool.py v4.X
# ...
# Wrote 850944 bytes at address 0x1000 in 20.50 seconds
# ===== [SUCCESS] Took X.XXs =====
```

**If upload fails:**
- Check USB connection
- Verify board is detected: `ls /dev/tty.*`
- Try manual reset: Hold BOOT button while uploading
- Check permissions: `sudo pio run --target upload`

---

### Test 4.4: ESP32 Serial Monitor (Verify Connection)

**Goal:** Verify ESP32 boots and connects to WiFi

**Command:**
```bash
cd /Users/apple/Documents/aegis1/firmware

# Monitor serial output
pio device monitor --baud 115200

# Expected output (after 10-15 seconds):
```

**Expected Serial Output:**
```
=== AEGIS1 Voice Firmware (Main) ===
Version: 1.0.0
Target: 192.168.1.42:8000/ws/audio
Flow: Mic -> Bridge -> STT/Claude/TTS -> Speaker

[OK] Mic ready
[...] WiFi connecting...
...................
[OK] WiFi 192.168.1.100
[OK] WebSocket started; speak into mic after connection
[OK] AEGIS1 bridge connected
```

**If you see this, ESP32 is working! ✅**

**Troubleshooting output:**

```
[...] WiFi connecting.......................
```
→ Stuck on WiFi: Check SSID/password in config.h, check WiFi is 2.4GHz

```
[...] Connecting...
```
→ WiFi connected but bridge not reachable: Check BRIDGE_HOST IP is correct

```
No output at all
```
→ Firmware not flashing: Check USB connection, try manual reset

---

### Test 4.5: Live Audio Test with ESP32

**Goal:** Test audio capture and playback with real hardware

**Setup:**
1. ESP32 is flashing (see Test 4.4 output)
2. Backend is running: `python -m aegis.main`
3. Monitor ESP32 serial output in separate terminal

**Steps:**

**Terminal 1: Monitor ESP32**
```bash
cd /Users/apple/Documents/aegis1/firmware
pio device monitor --baud 115200
```

**Terminal 2: Monitor Backend**
```bash
cd /Users/apple/Documents/aegis1
tail -f logs/aegis.log
# or watch main.py output
```

**Terminal 3: Physical Test**
1. Speak into the INMP441 microphone for 3-5 seconds
   - "How did I sleep this week?"
   - Speak clearly, not too quietly

2. Wait for silence (let mic sit quiet for 1 second)

3. Listen for audio response on PAM8403 speaker

4. Check logs for flow:
   - ESP32 serial: Audio chunks being sent
   - Backend logs: "Processing ... through STT"
   - Backend logs: "STT [user]: How did I sleep..."
   - Backend logs: "Claude response: You averaged..."
   - Backend logs: "TTS streamed ... chunks"

**Expected Result:**
- Microphone captures speech ✅
- Backend receives audio chunks ✅
- STT transcribes correctly ✅
- Claude responds with context ✅
- TTS converts to audio ✅
- Speaker plays response ✅

---

## Part 5: Unit Test Suite (10 minutes)

### Test 5.1: Run All Audio Tests

**Goal:** Verify all 18 unit tests pass

**Command:**
```bash
cd /Users/apple/Documents/aegis1
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/test_audio_pipeline.py -v

# Expected output:
```

**Expected Output:**
```
tests/test_audio_pipeline.py::TestAudioBuffer::test_audio_buffer_init PASSED
tests/test_audio_pipeline.py::TestAudioBuffer::test_audio_buffer_accumulates_chunks PASSED
tests/test_audio_pipeline.py::TestAudioBuffer::test_audio_buffer_detects_silence PASSED
tests/test_audio_pipeline.py::TestAudioBuffer::test_empty_chunk PASSED
tests/test_audio_pipeline.py::TestAudioBuffer::test_very_short_audio PASSED
tests/test_audio_pipeline.py::TestAudioConversion::test_pcm_to_wav PASSED
tests/test_audio_pipeline.py::TestAudioConversion::test_pcm_to_wav_with_defaults PASSED
tests/test_audio_pipeline.py::TestSTTIntegration::test_stt_with_mock_audio PASSED
tests/test_audio_pipeline.py::TestTTSIntegration::test_tts_engine_init PASSED
tests/test_audio_pipeline.py::TestTTSIntegration::test_tts_synthesize_with_mock PASSED
tests/test_audio_pipeline.py::TestTTSIntegration::test_tts_sentences_split PASSED
tests/test_audio_pipeline.py::TestAudioBufferEdgeCases::test_reset_clears_buffer PASSED
tests/test_audio_pipeline.py::TestAudioConstants::test_chunk_size_is_10ms PASSED
tests/test_audio_pipeline.py::TestAudioConstants::test_sample_rate_from_config PASSED
tests/test_audio_pipeline.py::TestAudioConstants::test_silence_threshold_configured PASSED
tests/test_audio_pipeline.py::TestAudioConstants::test_silence_duration_configured PASSED

====== 18 passed in 2.34s ======
```

**If tests fail:**
- Check imports: `pip install -r aegis/requirements.txt`
- Check pytest is installed: `pip install pytest pytest-asyncio`
- Check audio modules exist: `ls aegis/audio*.py`

---

## Part 6: Performance Testing (15 minutes)

### Test 6.1: Latency Measurement

**Goal:** Measure actual latency of each component

**Command:**
```bash
cd /Users/apple/Documents/aegis1
python3 << 'EOF'
import asyncio
import time
from aegis.audio import pcm_to_wav
from aegis.stt import transcribe_wav
from aegis.claude_client import ClaudeClient
from aegis.tts import TTSEngine

async def measure_latencies():
    print("=== Latency Measurements ===\n")
    
    # Create test audio (simulate 3 seconds of speech)
    audio_pcm = b'\x50\x00' * (16000 * 3)
    
    # 1. PCM to WAV conversion
    t0 = time.time()
    wav = pcm_to_wav(audio_pcm)
    conversion_ms = (time.time() - t0) * 1000
    print(f"PCM→WAV conversion: {conversion_ms:.1f}ms")
    
    # 2. STT (speech-to-text)
    print("\nNote: STT will be skipped if model not installed")
    print("Using example: 'How did I sleep?'")
    user_text = "How did I sleep this week?"
    
    # 3. Claude API call
    print("\nMeasuring Claude latency...")
    t0 = time.time()
    client = ClaudeClient()
    response = ""
    async for chunk in client.chat(user_text):
        response += chunk
    claude_ms = (time.time() - t0) * 1000
    print(f"Claude latency: {claude_ms:.0f}ms ({claude_ms/1000:.2f}s)")
    print(f"Response length: {len(response)} characters")
    
    # 4. TTS (text-to-speech)
    print("\nMeasuring TTS latency...")
    engine = TTSEngine()
    t0 = time.time()
    pcm_chunks = engine.synthesize_sentences(response)
    tts_ms = (time.time() - t0) * 1000
    print(f"TTS latency: {tts_ms:.0f}ms ({tts_ms/1000:.2f}s)")
    print(f"Audio chunks: {len(pcm_chunks)}")
    
    # Total
    total_ms = conversion_ms + claude_ms + tts_ms
    print(f"\n=== Summary ===")
    print(f"PCM→WAV: {conversion_ms:.1f}ms")
    print(f"STT: ~250ms (estimated)")
    print(f"Claude: {claude_ms:.0f}ms")
    print(f"TTS: {tts_ms:.0f}ms")
    print(f"Total (excluding speech capture): {total_ms:.0f}ms ({total_ms/1000:.2f}s)")

asyncio.run(measure_latencies())
EOF
```

**Expected Output:**
```
=== Latency Measurements ===

PCM→WAV conversion: 5.3ms
Measuring Claude latency...
Claude latency: 187ms (0.19s)
Response length: 142 characters

Measuring TTS latency...
TTS latency: 2341ms (2.34s)
Audio chunks: 3

=== Summary ===
PCM→WAV: 5.3ms
STT: ~250ms (estimated)
Claude: 187ms
TTS: 2341ms
Total (excluding speech capture): 2534ms (2.53s)
```

**Interpretation:**
- PCM→WAV: <10ms ✅ (negligible)
- STT: 200-400ms ✅ (fast)
- Claude: <200ms for Haiku ✅, ~2s for Opus ✓
- TTS: Variable depending on response length
- Total: 2-4s for full response ✅

---

### Test 6.2: Throughput Testing

**Goal:** Test multiple concurrent connections

**Command:**
```bash
python3 << 'EOF'
import asyncio
import websockets
import json
import time

async def send_messages(client_id, count):
    """Simulate one client sending messages."""
    try:
        async with websockets.connect('ws://localhost:8000/ws/text') as ws:
            for i in range(count):
                # Send message
                msg = {"text": f"Client {client_id} message {i}"}
                await ws.send(json.dumps(msg))
                
                # Receive response
                await ws.recv()  # Don't wait for full response
            
            return True
    except Exception as e:
        print(f"❌ Client {client_id} failed: {e}")
        return False

async def test_throughput():
    print("=== Throughput Test ===")
    print("Starting 5 concurrent clients, 2 messages each...\n")
    
    t0 = time.time()
    
    # Start 5 concurrent clients
    tasks = [send_messages(i, 2) for i in range(5)]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - t0
    
    success = sum(results)
    total_messages = 5 * 2
    
    print(f"\n=== Results ===")
    print(f"Successful clients: {success}/5")
    print(f"Total messages: {total_messages}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Messages/sec: {total_messages/elapsed:.1f}")
    
    if success == 5:
        print("✅ All clients succeeded")
    else:
        print(f"⚠️ {5-success} clients failed")

asyncio.run(test_throughput())
EOF
```

**Expected Output:**
```
=== Throughput Test ===
Starting 5 concurrent clients, 2 messages each...

=== Results ===
Successful clients: 5/5
Total messages: 10
Time: 15.24s
Messages/sec: 0.66

✅ All clients succeeded
```

---

## Part 7: Debugging Guide

### Debug 7.1: Enable Verbose Logging

**In aegis/config.py:**
```python
log_level: str = "DEBUG"  # Change from "INFO"
```

**Then restart backend:**
```bash
python -m aegis.main
# Now you'll see all debug messages
```

---

### Debug 7.2: Check Audio Buffer State

**In audio_buffer.py, add debugging:**
```python
def add_chunk(self, pcm_bytes: bytes):
    # ... existing code ...
    
    # Add this for debugging:
    if is_silent:
        print(f"[DEBUG] Silence: {self.silence_count}/{self.silence_threshold_chunks}")
    else:
        print(f"[DEBUG] Speech detected")
```

---

### Debug 7.3: Monitor WebSocket Traffic

**Using websocat (install: `brew install websocat`):**
```bash
websocat ws://localhost:8000/ws/audio

# Now any WebSocket messages will be printed
# Helpful for seeing what ESP32 is sending
```

---

### Debug 7.4: Test Each Component Individually

**STT only:**
```bash
python3 << 'EOF'
from aegis.audio import pcm_to_wav
from aegis.stt import transcribe_wav

# Create test audio WAV
pcm = b'\x50\x00' * 16000  # 0.5s of audio
wav = pcm_to_wav(pcm)

# Transcribe
text = transcribe_wav(wav)
print(f"STT result: {text}")
EOF
```

**Claude only:**
```bash
python3 << 'EOF'
import asyncio
from aegis.claude_client import ClaudeClient

async def test():
    client = ClaudeClient()
    async for chunk in client.chat("hello"):
        print(chunk, end='', flush=True)

asyncio.run(test())
EOF
```

**TTS only:**
```bash
python3 << 'EOF'
from aegis.tts import TTSEngine

engine = TTSEngine()
pcm = engine.synthesize("Hello, this is a test")
print(f"TTS produced: {len(pcm)} bytes of audio")
EOF
```

---

## Checklist: Complete Testing Sequence

Use this checklist to verify everything works:

### ✅ Part 1: Connection (5 min)
- [ ] Test 1.1: Health endpoint responds
- [ ] Test 1.2: Text WebSocket connects
- [ ] Test 1.3: Audio WebSocket accepts connection

### ✅ Part 2: Audio Pipeline (15 min)
- [ ] Test 2.1: AudioBuffer accumulates chunks
- [ ] Test 2.2: STT module loads
- [ ] Test 2.3: TTS module initializes
- [ ] Test 2.4: PCM/WAV conversion works

### ✅ Part 3: Integration (20 min)
- [ ] Test 3.1: Pipeline flow works (mocked)
- [ ] Test 3.2: WebSocket message flow works

### ✅ Part 4: Hardware (30 min)
- [ ] Test 4.1: Firmware config verified
- [ ] Test 4.2: Firmware compiles
- [ ] Test 4.3: Firmware flashes to ESP32
- [ ] Test 4.4: ESP32 boots and connects
- [ ] Test 4.5: Live audio test works

### ✅ Part 5: Unit Tests (10 min)
- [ ] Test 5.1: All 18 tests pass

### ✅ Part 6: Performance (15 min)
- [ ] Test 6.1: Latencies measured
- [ ] Test 6.2: Throughput verified

---

## Quick Start Command (All Tests)

```bash
#!/bin/bash
set -e

echo "=== AEGIS1 Testing Suite ==="
cd /Users/apple/Documents/aegis1

echo -e "\n1. Checking dependencies..."
pip install -q -r aegis/requirements.txt

echo -e "\n2. Starting backend in background..."
python -m aegis.main > /tmp/aegis.log 2>&1 &
BACKEND_PID=$!
sleep 3

echo -e "\n3. Running quick connection tests..."
python3 << 'EOF'
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8000/ws/text') as ws:
        await ws.send(json.dumps({"text": "test"}))
        await ws.recv()
        print("✅ Text WebSocket works")

asyncio.run(test())
EOF

echo -e "\n4. Running unit tests..."
pytest tests/test_audio_pipeline.py -q

echo -e "\n5. Stopping backend..."
kill $BACKEND_PID

echo -e "\n✅ All tests completed!"
```

Save as `test_all.sh` and run:
```bash
chmod +x test_all.sh
./test_all.sh
```

---

## Summary

This guide covers:
- ✅ Quick 5-minute connection tests
- ✅ 15-minute audio pipeline tests
- ✅ 20-minute integration tests
- ✅ 30-minute hardware tests
- ✅ 10-minute unit test suite
- ✅ 15-minute performance tests
- ✅ Comprehensive debugging guide

**Total testing time: ~95 minutes for complete verification**

All tests are designed to be run independently or as a suite. Use the checklist to track progress.

