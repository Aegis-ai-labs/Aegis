# AEGIS1 — Technical Context

## Tech Stack

| Layer         | Technology                             | Version           | Purpose                                                    |
| ------------- | -------------------------------------- | ----------------- | ---------------------------------------------------------- |
| Hardware      | ESP32 DevKit V1                        | —                 | Wearable pendant (mic, speaker, LED, button)               |
| Firmware      | Arduino/PlatformIO                     | —                 | ESP32 audio capture, WebSocket client, state machine       |
| Bridge Server | Python + FastAPI                       | 3.10+             | WebSocket server, pipeline orchestrator, ADPCM codec       |
| LLM           | Anthropic Claude API                   | anthropic>=0.40.0 | Haiku 4.5 (fast) + Opus 4.6 (deep) + parallel Opus pattern |
| STT           | Moonshine Streaming Tiny               | >=0.7.0           | Primary: 27M/26MB, 5x faster, native streaming             |
| STT Fallback  | faster-whisper                         | >=1.0.0           | Fallback: proven, stable, local                            |
| TTS           | Kokoro-82M                             | >=0.7.0           | Primary: 82M/350MB, Apache 2.0, ONNX, high quality         |
| TTS Fallback  | Piper + edge-tts                       | >=1.2.0 / >=6.1.0 | Ultra-low latency (<10ms) or Microsoft Edge fallback       |
| VAD           | Silero VAD                             | via torch.hub     | <1ms voice activity detection                              |
| Local LLM     | Phi-3-mini (Ollama)                    | >=0.1.0           | ~4GB RAM, <200ms simple queries                            |
| Memory        | sqlite-vec                             | >=0.1.0           | <50ms cosine similarity search, conversation recall        |
| Audio Codec   | ADPCM                                  | Built-in          | 4x compression (256kbps → 64kbps), PCM ↔ WAV               |
| Database      | SQLite (WAL mode) + user_profile table | Built-in          | Health logs, expenses, conversations, user settings        |
| Config        | pydantic-settings                      | >=2.0.0           | Typed env-based configuration                              |
| Transport     | WebSockets + ADPCM                     | >=12.0            | Binary PCM (ADPCM) + JSON control messages                 |

## Python Dependencies (`aegis/requirements.txt`)

```
fastapi>=0.104.0          # HTTP + WebSocket server
uvicorn[standard]>=0.24.0 # ASGI server
websockets>=12.0          # WebSocket protocol
pydantic-settings>=2.0.0  # Typed configuration from .env
anthropic>=0.40.0         # Claude API client
moonshine-onnx>=0.7.0     # Moonshine STT (streaming, ONNX)
faster-whisper>=1.0.0     # STT fallback (CTranslate2 backend)
kokoro>=0.7.0             # Kokoro TTS (ONNX, high quality)
edge-tts>=6.1.0           # TTS fallback (Microsoft Edge API)
silero-vad                # Voice activity detection (<1ms)
sqlite-vec>=0.1.0         # SQLite + vector embeddings for memory
soundfile>=0.12.0         # WAV I/O for audio processing
numpy>=1.24.0             # Numerical operations
python-dotenv>=1.0.0      # .env file loading
```

## Development Environment

### Prerequisites

- **Python 3.10+** (Kokoro TTS requirement)
- **espeak-ng** system library (Kokoro g2p phoneme support)
  - macOS: `brew install espeak-ng`
  - Ubuntu/Debian: `sudo apt-get install espeak-ng`
- **Ollama** (optional, for local LLM Phi-3-mini)
  - Download from [ollama.ai](https://ollama.ai); then `ollama pull phi3:mini`
- **Anthropic API key** (`ANTHROPIC_API_KEY`)
- **PlatformIO** (for ESP32 firmware modifications only)

### Setup

```bash
cd aegis/
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other config
```

### Running AEGIS

```bash
# Start WebSocket server (connects to ESP32 pendant)
python -m aegis serve

# Run text-mode REPL (test Claude tools without audio)
python -m aegis terminal

# Import Apple Health data
python -m aegis import-health ~/Downloads/apple_health_export/export.xml

# Seed demo data
python -m aegis seed

# Show all commands
python -m aegis --help
```

### Environment Variables (`.env`)

```
# Claude API (required)
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001
CLAUDE_OPUS_MODEL=claude-opus-4-6
CLAUDE_MAX_TOKENS=300

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Audio
SAMPLE_RATE=16000

# STT (Moonshine Streaming Tiny)
STT_BEAM_SIZE=1                   # Beam search width (1=greedy)
SILENCE_CHUNKS_TO_STOP=8          # Chunks of silence to end recording
MAX_RECORDING_TIME_MS=10000        # Max utterance length (10s)

# TTS (Kokoro)
KOKORO_VOICE=af_heart             # Kokoro voice name
KOKORO_SPEED=1.0                  # Speech rate
KOKORO_LANG=a                     # Language code

# Database
DB_PATH=aegis1.db

# Local LLM (optional)
OLLAMA_HOST=http://localhost:11434  # Phi-3-mini endpoint
```

## Hardware (ESP32 DevKit V1)

### Pin Assignments (Tested Working)

| Component         | Pin           | Notes                    |
| ----------------- | ------------- | ------------------------ |
| INMP441 Mic BCLK  | GPIO13        | I2S bit clock            |
| INMP441 Mic LRCLK | GPIO14        | I2S word select          |
| INMP441 Mic DIN   | GPIO33        | I2S data in              |
| PAM8403 Speaker   | GPIO25 (DAC1) | Analog output            |
| Status LED        | GPIO2         | Built-in blue LED        |
| Button            | GPIO0         | BOOT button (active low) |

### Audio Format

- Sample rate: 16kHz
- Bit depth: 16-bit signed
- Channels: Mono
- Chunk size: 200ms (~6400 bytes per chunk)
- Format: Raw PCM (little-endian)

## Repository Structure

```
aegis1/
├── aegis/                           # Python bridge server (AEGIS portable system)
│   ├── __init__.py
│   ├── __main__.py                  # CLI entry point (serve/terminal/import-health/seed)
│   ├── config.py                    # pydantic-settings (Kokoro, STT, server config)
│   ├── db.py                        # SQLite schema, CRUD, user_profile table
│   ├── context.py                   # Health context builder (7-day snapshot)
│   ├── health_import.py             # Apple Health XML parser
│   ├── claude_client.py             # Claude streaming + parallel Opus pattern
│   ├── audio.py                     # PCM/WAV utils, ADPCM codec
│   ├── stt.py                       # Moonshine STT wrapper (w/ faster-whisper fallback)
│   ├── tts.py                       # Kokoro TTS engine (w/ edge-tts fallback)
│   ├── vad.py                       # Silero VAD (voice activity detection)
│   ├── main.py                      # FastAPI WebSocket server + orchestrator
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Config template
│   └── tools/
│       ├── __init__.py
│       ├── registry.py              # Tool definitions (7 tools) + dispatch
│       ├── health.py                # Health tracking (3 functions)
│       └── wealth.py                # Expense tracking (3 functions)
├── firmware/                        # ESP32 Arduino code (tested, stable)
├── docs/                            # Documentation
│   ├── research.md                  # Tech research + model comparisons
│   ├── architecture.md              # System architecture + flow diagrams
│   ├── plan.md                      # Implementation plan (phases 1-5)
│   ├── specs/                       # Phase-by-phase technical specs
│   └── memory-bank/                 # Project context + memory files
├── tests/                           # Python unit/integration tests
└── CLAUDE.md                        # Claude Code instructions
```
