# AEGIS1 — Project Research & Technical Analysis

## 1. Project Context & Motivation

### The Problem
Health and wealth tracking apps suffer from **friction fatigue**. Users download apps, log data for two weeks, then abandon them. The core issue: pulling out your phone, opening an app, and typing data is too much friction for something you need to do 5-10 times daily.

### The Insight
Voice removes friction. A wearable pendant you press and speak to — "I slept 7 hours" or "spent $12 on lunch" — has near-zero friction. Combined with an AI that can analyze patterns across your data, it becomes more than a logger: it becomes an advisor.

### Hackathon Fit
This project is purpose-built to showcase Claude's strengths:
- **Tool use** — 6 real tools (health + wealth) that query a database, not canned responses
- **Model routing** — Haiku 4.5 for speed, Opus 4.6 for deep analysis with extended thinking
- **Streaming** — Sentence-level streaming for <2s perceived latency
- **Multi-turn context** — Conversation history for follow-up questions

## 2. Technology Stack Analysis

### Claude API (Core)
**Choice:** Direct Anthropic SDK (`anthropic>=0.40.0`)
**Rationale:** Maximum control over streaming, tool use loop, and model routing. Frameworks like Pipecat were considered but add latency and abstraction overhead for a hackathon.

### Haiku 4.5 + Opus 4.6 Dual-Model Strategy
**Choice:** Keyword-based routing with extended thinking on Opus
**Rationale:**
- Haiku handles 80% of interactions (logging, simple lookups) in <200ms to first token
- Opus handles complex queries (pattern analysis, financial planning) with deeper reasoning
- Extended thinking (`budget_tokens=2048`) gives Opus room to reason about correlations
- This is a natural showcase of the judging criterion "Opus 4.6 Use (25%)"

### faster-whisper (STT)
**Choice:** Local STT via CTranslate2 backend
**Rationale:**
- No API key needed (Whisper API would add latency + cost)
- `base` model with `beam_size=1` and `vad_filter=True` targets <300ms
- CPU inference is sufficient for single-user demo
- Alternatives considered: OpenAI Whisper API (too slow), Deepgram (requires API key)

### Piper TTS
**Choice:** Local TTS with Python API + CLI fallback
**Rationale:**
- Free and open-source (no API costs)
- Low latency (<150ms for short sentences)
- Runs locally on CPU
- Alternatives considered: OpenAI TTS (quality is higher but adds ~300ms network latency), ElevenLabs (cost), espeak (quality too low)

### FastAPI + WebSocket
**Choice:** FastAPI as the bridge server
**Rationale:**
- Native WebSocket support for binary audio streaming
- Async-capable for handling concurrent connections
- Built-in Swagger docs for debugging
- Lightweight — no ORM, no session management overhead

### SQLite
**Choice:** Embedded SQLite with WAL mode
**Rationale:**
- Zero setup (no database server to run)
- WAL mode for concurrent read/write
- Perfect for single-user hackathon demo
- Auto-seeded with 30 days of realistic demo data

## 3. Competitive Landscape

| Approach | Pros | Cons | Why Not |
|----------|------|------|---------|
| Siri/Alexa health skills | Existing platform | No custom tools, no deep analysis | Can't showcase Claude |
| ChatGPT voice mode | Good voice quality | No custom hardware, no persistent data | Not a pendant, no tool use |
| Dedicated health apps | Polished UI | High friction, no voice | Defeats our thesis |
| AEGIS1 | Voice-first, custom tools, dual-model | Hackathon quality | **Our approach** |

## 4. Risk Assessment

### High Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| Perceived latency >3s | Demo feels slow | Sentence-level streaming, not waiting for full response |
| ESP32 audio quality poor | Unintelligible STT | Tested independently — INMP441 mic quality is adequate |
| Piper voice quality jarring | Demo feels amateur | Choose best available voice model, keep responses short |

### Medium Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude tool use errors | Wrong data logged/returned | Max 5 tool rounds, error JSON returned to Claude |
| faster-whisper accuracy | Misheard commands | VAD filter, English-only, short utterances |
| WiFi reliability | Connection drops | WebSocket reconnect in firmware, connection state tracking |

### Low Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite concurrency | Data corruption | WAL mode, single-user demo |
| API rate limits | Requests blocked | Single user, low request rate |
| Memory leaks | Server crashes | Conversation history capped at 20 turns |

## 5. Key Technical Decisions

| # | Decision | Alternatives Considered | Rationale |
|---|----------|------------------------|-----------|
| 1 | Claude-native (no framework) | Pipecat, LangChain, direct WebSocket | Fastest implementation, lowest latency, maximum control |
| 2 | Piper TTS | OpenAI TTS, ElevenLabs, espeak | Free, local, <150ms, no API dependency |
| 3 | Button-press activation | Wake word (Porcupine), always-on | Saves 2+ days of implementation |
| 4 | SQLite | PostgreSQL, MongoDB, DynamoDB | Zero setup, embedded, hackathon-appropriate |
| 5 | Sentence-level streaming | Wait for full response, word-level | Best latency/quality tradeoff |
| 6 | Keyword-based model routing | Embedding similarity, Claude self-routing | Simple, fast, good enough for demo queries |
| 7 | Sync Anthropic client | AsyncAnthropic | Tool loop is inherently sequential; async wrapper in generator |
| 8 | Demo data auto-seed | Manual data entry, API import | Reproducible (`random.seed(42)`), instant setup |

## 6. References

- **Anthropic Claude API docs** — Tool use, streaming, extended thinking
- **faster-whisper GitHub** — CTranslate2 Whisper implementation
- **Piper TTS GitHub** — Local neural TTS engine
- **FastAPI WebSocket docs** — Binary + JSON multiplexing
- **ESP32 I2S audio** — INMP441 mic + DAC output
- **Original prototype** — `/Users/apple/aegis` (OpenClaw-based, used for architectural reference)
