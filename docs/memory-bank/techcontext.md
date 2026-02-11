# AEGIS1 — Technical Context

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Hardware | ESP32 DevKit V1 | — | Wearable pendant (mic, speaker, LED, button) |
| Firmware | Arduino/PlatformIO | — | ESP32 audio capture, WebSocket client, state machine |
| Bridge Server | Python + FastAPI | 3.11+ | WebSocket server, pipeline orchestrator |
| LLM | Anthropic Claude API | anthropic>=0.40.0 | Haiku 4.5 (fast) + Opus 4.6 (deep) |
| STT | faster-whisper | >=1.0.0 | Local speech-to-text (no API key) |
| TTS | Piper TTS | >=1.2.0 | Local text-to-speech (no API key) |
| Database | SQLite (WAL mode) | Built-in | Health logs, expenses, conversations |
| Config | pydantic-settings | >=2.0.0 | Typed env-based configuration |
| Transport | WebSockets | >=12.0 | Binary PCM + JSON control messages |

## Python Dependencies (`bridge/requirements.txt`)

```
fastapi>=0.104.0          # HTTP + WebSocket server
uvicorn[standard]>=0.24.0 # ASGI server
websockets>=12.0          # WebSocket protocol
pydantic-settings>=2.0.0  # Typed configuration from .env
anthropic>=0.40.0         # Claude API client
faster-whisper>=1.0.0     # Local STT (CTranslate2 backend)
pydub>=0.25.0             # Audio processing utilities
numpy>=1.24.0             # Numerical operations
piper-tts>=1.2.0          # Local TTS engine
python-dotenv>=1.0.0      # .env file loading
aiosqlite>=0.20.0         # Async SQLite (available but sync used currently)
```

## Development Environment

### Prerequisites
- Python 3.11+
- PlatformIO (for ESP32 firmware, if modifying)
- Anthropic API key (`ANTHROPIC_API_KEY`)

### Setup
```bash
cd bridge/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
```

### Running the Bridge
```bash
python -m bridge.main
# Server starts at ws://0.0.0.0:8000/ws/audio
```

### Environment Variables (`.env`)
```
ANTHROPIC_API_KEY=sk-ant-xxxxx    # Required
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001
CLAUDE_OPUS_MODEL=claude-opus-4-6
CLAUDE_MAX_TOKENS=300
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8000
SAMPLE_RATE=16000
STT_MODEL=base                    # faster-whisper model size
STT_DEVICE=cpu                    # cpu or cuda
STT_LANGUAGE=en
PIPER_MODEL_PATH=                 # Path to .onnx voice model
PIPER_CONFIG_PATH=                # Path to voice config JSON
DB_PATH=aegis1.db
LOG_LEVEL=INFO
```

## Hardware (ESP32 DevKit V1)

### Pin Assignments (Tested Working)
| Component | Pin | Notes |
|-----------|-----|-------|
| INMP441 Mic BCLK | GPIO13 | I2S bit clock |
| INMP441 Mic LRCLK | GPIO14 | I2S word select |
| INMP441 Mic DIN | GPIO33 | I2S data in |
| PAM8403 Speaker | GPIO25 (DAC1) | Analog output |
| Status LED | GPIO2 | Built-in blue LED |
| Button | GPIO0 | BOOT button (active low) |

### Audio Format
- Sample rate: 16kHz
- Bit depth: 16-bit signed
- Channels: Mono
- Chunk size: 200ms (~6400 bytes per chunk)
- Format: Raw PCM (little-endian)

## Repository Structure

```
aegis1/
├── bridge/                  # Python bridge server
│   ├── __init__.py
│   ├── config.py           # pydantic-settings configuration
│   ├── db.py               # SQLite schema, CRUD, demo data seeding
│   ├── claude_client.py    # Claude streaming client + model routing
│   ├── audio.py            # PCM/WAV conversion, silence detection
│   ├── stt.py              # faster-whisper STT wrapper
│   ├── tts.py              # Piper TTS engine (Python API + CLI fallback)
│   ├── main.py             # FastAPI WebSocket orchestrator
│   ├── requirements.txt
│   ├── .env.example
│   └── tools/
│       ├── __init__.py
│       ├── registry.py     # Tool definitions + dispatch
│       ├── health.py       # Health tracking tools (3 functions)
│       └── wealth.py       # Wealth management tools (3 functions)
├── firmware/                # ESP32 Arduino code (tested, stable)
├── docs/                    # Documentation suite
│   ├── research.md
│   ├── architecture.md
│   ├── plan.md
│   ├── specs/              # Phase-by-phase specifications
│   └── memory-bank/        # Project context files
└── CLAUDE.md               # Claude Code instructions
```
