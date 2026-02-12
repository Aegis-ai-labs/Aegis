<<<<<<< HEAD
# AEGIS1 — Project Research & Technical Analysis

*Last updated: Feb 12, 2026 (Day 3)*

## 1. Project Context & Motivation

### The Problem
Health and wealth tracking apps suffer from **friction fatigue**. Users download apps, log data for two weeks, then abandon them. The core issue: pulling out your phone, opening an app, and typing data is too much friction for something you need to do 5-10 times daily.

### The Insight
Voice removes friction. A wearable pendant you press and speak to — "I slept 7 hours" or "spent $12 on lunch" — has near-zero friction. Combined with an AI that can analyze patterns across your data and adapt to your body's unique patterns, it becomes more than a logger: it becomes a personalized health advisor.

### Hackathon Fit (Judging Criteria Alignment)
**Impact (25%)**: Targets ages 30-65 with disposable income and health awareness — a large demographic that struggles with tracking consistency.

**Opus 4.6 Use (25%)**: Dual-model architecture showcases both speed (Haiku) and depth (Opus):
- Parallel Opus pattern: Haiku immediate ack → async Opus deep analysis via `asyncio.create_task()`
- Extended thinking: `interleaved-thinking-2025-05-14` beta with 10,000 token budget
- Health personalization: Dynamic system prompts regenerated per call with user's health context

**Depth & Execution (20%)**: Edge-optimized tech stack targeting 440ms perceived latency for simple queries:
- Moonshine Streaming Tiny STT (5x faster than faster-whisper)
- Kokoro-82M TTS (local, Apache 2.0, 82M params)
- Silero VAD (<1ms voice activity detection)
- Phi-3-mini local LLM (<200ms for simple queries)
- sqlite-vec memory (<50ms cosine similarity)
- ADPCM codec (4x audio compression)

**Demo (30%)**: Compelling narrative showing:
1. Voice interaction (button press → speak → instant response)
2. Body-aware intelligence (Claude knows your sleep patterns, exercise trends, spending habits)
3. Extended thinking showcase (Opus reasoning about health correlations across weeks)

## 2. Technology Stack Analysis

### 2.1 Core Architecture

**Choice:** Direct Anthropic SDK (`anthropic>=0.41.0`) + FastAPI WebSocket server  
**Rationale:** Maximum control over streaming, tool use loop, and model routing. Frameworks like Pipecat were considered but add latency, abstraction overhead, and complexity for a hackathon scope. Direct SDK allows:
- True streaming via `messages.stream()` (not `messages.create()` with streaming wrapper)
- Parallel Opus pattern (Haiku ack + async Opus deep analysis)
- Custom system prompt injection (3-layer: static cached persona + dynamic health context + static tool directives)
- Ephemeral prompt caching on static layers to reduce latency

### 2.2 Dual-Model Strategy

**Haiku 4.5 (Fast Path — 80% of queries)**
- Use case: Logging, simple lookups, conversational acknowledgment
- Target latency: <200ms to first token
- Streaming: Immediate sentence-level streaming to TTS
- Example queries: "I slept 7 hours", "track $12 lunch", "how much did I spend this week?"

**Opus 4.6 (Deep Path — 20% of queries)**
- Use case: Pattern analysis, correlations, financial planning, health insights
- Extended thinking: `interleaved-thinking-2025-05-14` beta with `budget_tokens=10000`
- Parallel pattern: Haiku sends quick ack → Opus runs async deep analysis → stream results later
- Example queries: "analyze my sleep patterns", "why am I always tired on Mondays?", "create a savings plan"

**Routing Logic:**
- Keyword-based (fast, deterministic)
- Keywords triggering Opus: "analyze", "why", "correlation", "pattern", "plan", "explain", "should I"
- Default to Haiku for speed

### 2.3 Speech-to-Text (STT)

**Choice:** Moonshine Streaming Tiny (primary) + faster-whisper (fallback)

**Moonshine Streaming Tiny**
- Params: 27M (vs faster-whisper base 74M)
- Size: 26MB ONNX model
- License: MIT
- Speed: 5x faster than faster-whisper
- Unique feature: Native streaming (processes audio chunks incrementally, not batch-only)
- Inference: CPU sufficient for single-user demo
- Accuracy: Optimized for short-form conversational speech

**faster-whisper (fallback)**
- Use case: Backup if Moonshine accuracy insufficient for certain accents/environments
- Config: `base` model, `beam_size=1`, `vad_filter=True`, `language="en"`
- Expected latency: ~300ms for 3-5 second utterances

**Alternatives Considered:**
- OpenAI Whisper API: Too slow (~500-800ms network + inference)
- Deepgram: Requires API key, costs, network dependency
- Whisper.cpp: Fast but lacks Python bindings quality

### 2.4 Text-to-Speech (TTS)

**Choice:** Kokoro-82M (primary) + Piper/edge-tts (fallback)

**Kokoro-82M**
- Params: 82M
- Size: 350MB ONNX model
- License: Apache 2.0 (suitable for commercial use)
- Quality: Natural prosody, low robotic artifacts
- Speed: <100ms for short sentences on CPU
- Voices: Multiple voice options (am_adam, am_michael, af_bella, af_sarah, bf_emma, bf_isabella, etc.)
- Dependency: espeak-ng for phoneme support
- Python requirement: 3.10+ (breaking change from 3.9)

**Why not Piper?**
- Piper TTS archived October 2025 (maintainer discontinued)
- Kokoro is newer, actively maintained, Apache 2.0 licensed

**Fallback Options:**
- Piper: Still functional as fallback (quality good, but unmaintained)
- edge-tts: Microsoft Edge TTS API (free, cloud-based, requires internet)

**Alternatives Considered:**
- OpenAI TTS: Higher quality but adds ~300ms network latency + API costs
- ElevenLabs: Premium quality but expensive for hackathon
- espeak: Too robotic for demo quality

### 2.5 Voice Activity Detection (VAD)

**Choice:** Silero VAD (<1ms) + naive RMS fallback

**Silero VAD**
- Speed: <1ms per chunk on CPU
- Input: 16-bit mono PCM at 16kHz
- Output: Probability (0.0 to 1.0) of voice activity
- Logic: End recording when probability <0.5 for N consecutive chunks
- Model size: ~1MB
- License: MIT

**Naive RMS fallback:**
- Use case: If Silero fails to load or has compatibility issues
- Method: Calculate RMS, threshold-based silence detection (existing code in audio.py)
- Less accurate but guaranteed to work

**Alternatives Considered:**
- WebRTC VAD: Lower quality, more false positives
- PyAudio silence detection: Already implemented, but less sophisticated than Silero

### 2.6 Local LLM (Simple Query Optimization)

**Choice:** Phi-3-mini via Ollama

**Phi-3-mini**
- Params: 3.8B
- RAM: ~4GB
- Speed: <200ms for simple queries (single-turn, no reasoning)
- Use case: Offload Haiku for trivial lookups like "what's 15% of $80?" or "convert 5 miles to km"
- Integration: Optional (fallback to Haiku if Ollama not running)

**Routing Logic:**
- Math queries → Phi-3-mini
- Unit conversions → Phi-3-mini
- Everything else → Haiku/Opus

**Alternatives Considered:**
- LLaMA 3.2 1B: Faster but lower quality
- Gemma 2B: Similar performance, slightly larger
- Qwen 1.8B: Good quality but less tested

### 2.7 Conversation Memory

**Choice:** sqlite-vec for semantic similarity search

**sqlite-vec**
- Method: Cosine similarity search on embeddings
- Speed: <50ms for typical queries (single-user DB)
- Storage: Embeddings table with vector column
- Embedding model: text-embedding-3-small via Anthropic API (512 dimensions)
- Use case: "What did I eat for lunch yesterday?" → retrieve past conversation context

**Alternatives Considered:**
- Pinecone: Overkill for single-user, requires API key
- ChromaDB: Heavier dependency, slower for small datasets
- Pure SQL text search: Less accurate for semantic queries

### 2.8 Audio Codec

**Choice:** ADPCM (Adaptive Differential Pulse Code Modulation)

**ADPCM Compression:**
- Compression ratio: 4x (256kbps PCM → 64kbps ADPCM)
- Quality: Minimal perceptual loss for speech
- Latency: <5ms encode/decode
- Use case: ESP32 bandwidth optimization (WiFi upload constrained at ~100kbps in crowded networks)

**ESP32 Transport:**
- Format: Binary WebSocket frames (ADPCM compressed)
- Chunk size: 200ms worth of audio (1600 bytes PCM → 400 bytes ADPCM)
- Decompression: Server-side (Python) using standard ADPCM codec

**Alternatives Considered:**
- Opus: Higher quality but heavier CPU on ESP32
- MP3: Patent issues, heavier encode/decode
- Raw PCM: 4x bandwidth usage

### 2.9 Database & Storage

**Choice:** SQLite with WAL mode + sqlite-vec extension

**SQLite**
- Mode: WAL (Write-Ahead Logging) for concurrent read/write
- Tables: `users`, `user_health_logs`, `user_expenses`, `conversation_memory` (planned)
- Indexes: Optimized for tool queries (e.g., date range lookups)
- Seeding: Auto-seed with 30 days of realistic demo data (`random.seed(42)` for reproducibility)

**Why SQLite:**
- Zero setup (embedded, no server)
- Sufficient for single-user demo
- sqlite-vec extension enables vector search without separate vector DB

**Alternatives Considered:**
- PostgreSQL: Overkill for hackathon, requires server setup
- MongoDB: No strong benefit for structured health/expense data
- DynamoDB: Requires AWS setup, internet dependency

### 2.10 Health Personalization

**Apple Health XML Import**
- Format: Standard Apple Health export XML
- Extraction: 5 quantitative types (steps, heart_rate, weight, exercise_minutes, sleep_hours)
- Storage: Load to `user_health_logs` table
- Trigger: One-time CLI command (`python -m aegis import-health path/to/export.xml`)
- Use case: Real user data instead of synthetic demo data

**Dynamic System Prompt Injection (3-Layer Architecture)**

**Layer 1: Static Cached Persona & Rules**
```
You are AEGIS, a voice assistant for a health & wealth tracking pendant.
Be concise (1-2 sentences), warm, actionable. Use present tense.
```
- Cached: Yes (ephemeral prompt caching)
- Regenerated: Never (static)

**Layer 2: Dynamic Health Context**
```
User's recent health: Last 7 days avg sleep 6.2h (below 7h target), 
steps 8500/day (good), weight stable at 165 lbs. Notable: 3 days <6h sleep.
```
- Cached: No (changes every call)
- Regenerated: Every request via `build_health_context(user_id)` from `user_health_logs` table
- Purpose: Makes Claude body-aware — responses reference user's actual patterns

**Layer 3: Static Cached Tool Directives**
```
Available tools: get_health_context, log_health, analyze_patterns, 
track_expense, spending_summary, savings_goal, save_user_insight.
Use tools to query/write data. Never hallucinate data.
```
- Cached: Yes (ephemeral prompt caching)
- Regenerated: Never (static)

**Benefits:**
- Layer 1+3 cached → reduce latency after first call
- Layer 2 dynamic → Claude always knows current health state
- Personalization: "You've been sleeping less than usual this week" (not generic advice)

## 3. Latency Budget & Optimization

**Target Perceived Latency:**
- Simple queries (Haiku): 440ms
- Complex queries (Opus parallel): 1040ms for ack, +2000ms for deep analysis (async)

**Latency Breakdown (Simple Query, Haiku Path):**
| Stage | Target | Optimizations |
|-------|--------|---------------|
| VAD (silence detection) | 100ms | Silero <1ms per chunk, 10 chunks @ 100ms each |
| STT (Moonshine) | 80ms | Native streaming, 5x faster than faster-whisper |
| LLM (Haiku) | 150ms | Haiku <200ms TTFT, prompt caching on static layers |
| TTS (Kokoro) | 60ms | Short sentence, CPU inference |
| Network (WebSocket) | 50ms | Local network, binary frames |
| **Total** | **440ms** | Perceived as <0.5s (feels instant) |

**Latency Breakdown (Complex Query, Opus Parallel Path):**
| Stage | Target | Optimizations |
|-------|--------|---------------|
| VAD + STT | 180ms | Same as simple |
| LLM Haiku (ack) | 150ms | Quick acknowledgment: "Let me analyze that..." |
| TTS (ack) | 60ms | Short sentence |
| Network | 50ms | |
| **Perceived (ack)** | **440ms** | User hears immediate response |
| LLM Opus (async) | 2000ms | Extended thinking, runs in background |
| TTS (results) | 200ms | Longer response (2-3 sentences) |
| **Total (deep analysis)** | **+2200ms** | Streamed after ack, feels like natural pause |

## 4. Tool Architecture

**7 Total Tools (3 health, 3 wealth, 1 profile):**

**Health Tools:**
1. `get_health_context(days: int)` — Retrieve health summary for last N days
2. `log_health(type: str, value: float, timestamp: str)` — Log health metric (steps, sleep, weight, etc.)
3. `analyze_patterns(metric: str, days: int)` — Analyze trends/patterns in health data

**Wealth Tools:**
4. `track_expense(amount: float, category: str, description: str)` — Log expense
5. `spending_summary(days: int, category: Optional[str])` — Get spending breakdown
6. `savings_goal(target: float, months: int)` — Calculate monthly savings needed

**Profile Tool:**
7. `save_user_insight(key: str, value: str)` — Store user preferences/insights for personalization

**Tool Use Pattern:**
- Max 5 tool call rounds per conversation turn (prevent infinite loops)
- Tool responses are JSON, returned to Claude for interpretation
- Error handling: Tool errors return JSON with `"error"` field, Claude explains to user
- Demo data: Auto-seeded with 30 days of realistic variance for compelling narratives

## 5. Key Technical Decisions

| # | Decision | Alternatives Considered | Rationale |
|---|----------|------------------------|-----------|
| 1 | Direct Anthropic SDK (no framework) | Pipecat, LangChain, LlamaIndex | Fastest implementation, lowest latency, maximum control for hackathon |
| 2 | Kokoro TTS | Piper (archived), OpenAI TTS, ElevenLabs | Apache 2.0, local, <100ms, Piper unmaintained |
| 3 | Moonshine Streaming Tiny STT | faster-whisper, Whisper API, Deepgram | 5x faster, native streaming, MIT licensed, 26MB |
| 4 | Silero VAD | WebRTC VAD, naive RMS | <1ms, more accurate, MIT licensed |
| 5 | Phi-3-mini local LLM | LLaMA 3.2 1B, Gemma 2B, API-only | <200ms simple queries, offloads Haiku trivial tasks |
| 6 | sqlite-vec memory | Pinecone, ChromaDB, SQL text search | <50ms, embedded, no API dependency |
| 7 | ADPCM codec | Opus, MP3, raw PCM | 4x compression, minimal loss, low CPU |
| 8 | Parallel Opus pattern | Sequential Haiku→Opus, Opus-only | Best of both: Haiku speed + Opus depth without blocking |
| 9 | Dynamic health system prompts | Static prompts, RAG retrieval | Always current, cached layers reduce latency |
| 10 | Apple Health XML import | Manual entry, API sync | Real user data, one-time setup |
| 11 | Button-press activation | Wake word (Porcupine), always-on | Saves 2+ days implementation, acceptable UX |
| 12 | 7 tools (not 20+) | Comprehensive tool suite | Quality over quantity, focused demo narrative |
| 13 | Package name: aegis | bridge, pendant, guardian | "Portable system" positioning, not middleware |
| 14 | Python 3.10+ | Python 3.9 | Kokoro requirement (breaking change) |

## 6. Risk Assessment

### High Risk
| Risk | Impact | Mitigation | Status |
|------|--------|-----------|---------|
| Perceived latency >1s | Demo feels slow | Sentence-level streaming, parallel Opus, ADPCM compression | ✅ Architecture supports 440ms target |
| Moonshine/Silero integration bugs | STT/VAD broken, fallback to slower stack | Keep faster-whisper as fallback, naive RMS for VAD | ⏳ Not yet tested |
| sqlite-vec setup issues | No conversation memory | Use pure SQL text search as fallback | ⏳ Not yet implemented |
| Time constraint (26h work, 4 days) | Incomplete demo | Prioritize Phase 1-2, defer Phase 3 if needed | ⚠️ On track but tight |

### Medium Risk
| Risk | Impact | Mitigation | Status |
|------|--------|-----------|---------|
| Kokoro voice quality | Demo feels amateur | Choose best voice (am_adam), keep responses short | ✅ Tested, acceptable quality |
| Health context injection bugs | Generic responses, not personalized | Thorough testing, fallback to static prompt | ⏳ Not yet implemented |
| Demo data narrative weak | Uncompelling demo | Curate 3 scenarios: sleep analysis, spending patterns, savings goal | ⏳ Planned for Phase 2 |
| Package rename breakage | Import errors everywhere | Systematic search/replace, test after rename | ⏳ Not started |

### Low Risk
| Risk | Impact | Mitigation | Status |
|------|--------|-----------|---------|
| ESP32 WiFi drops | Connection loss | WebSocket reconnect logic in firmware | ✅ Firmware handles reconnect |
| SQLite concurrency issues | Data corruption | WAL mode, single-user demo | ✅ WAL enabled |
| Tool use errors | Wrong data logged | Max 5 rounds, error JSON, Claude explains | ✅ Tested in terminal |

## 7. Competitive Landscape

| Approach | Pros | Cons | Why Not |
|----------|------|------|---------|
| Siri/Alexa health skills | Existing platform, polished | No custom tools, no deep analysis, no persistent cross-domain data | Can't showcase Claude's tool use + reasoning |
| ChatGPT voice mode | Good voice quality, GPT-4 analysis | No custom hardware, no persistent data, no voice-first UX | Not a pendant, no health/wealth fusion |
| Dedicated health apps (MyFitnessPal, etc.) | Polished UI, comprehensive features | High friction (manual logging), no voice, no AI insights | Defeats our "friction fatigue" thesis |
| Wearables (Apple Watch, Whoop) | Auto-logging (steps, sleep) | Expensive, no expense tracking, no conversational AI | Missing wealth dimension, no voice queries |
| **AEGIS1** | Voice-first, health+wealth fusion, custom Claude tools, body-aware personalization | Hackathon quality, limited scope | **Our unique positioning** |

## 8. References

### Primary Documentation
- **Anthropic Claude API** — Tool use, streaming, extended thinking, prompt caching
- **Moonshine ONNX** — Streaming STT model, MIT licensed
- **Kokoro TTS** — Apache 2.0 local TTS, ONNX models
- **Silero VAD** — Voice activity detection, PyTorch model
- **sqlite-vec** — SQLite extension for vector similarity search
- **Phi-3** — Microsoft's small language model via Ollama

### Implementation References
- **FastAPI WebSocket** — Binary + JSON multiplexing patterns
- **ESP32 I2S audio** — INMP441 mic + PAM8403 speaker via DAC
- **ADPCM codec** — Python implementation for audio compression
- **Apple Health Export** — XML schema for health data extraction

### Prior Art
- **Original prototype** — `/Users/apple/aegis` (OpenClaw-based, architectural reference)
- **Anthropic Cookbook** — Extended thinking examples, streaming patterns
- **Pipecat (considered, rejected)** — Framework analysis for latency comparison

## 9. Success Metrics (Demo Evaluation)

**Impact (25%):**
- Clear value prop: "Eliminate friction fatigue in health/wealth tracking"
- Target demographic: Ages 30-65, health-aware, disposable income (large TAM)
- Demo scenarios show before/after: "Logging used to take 30 seconds, now takes 3 seconds"

**Opus 4.6 Use (25%):**
- Extended thinking showcase: Screen recording of Opus reasoning through health correlations
- Parallel pattern demo: Immediate ack + deep analysis streamed later
- Tool use complexity: Multi-turn conversations with 3+ tool calls

**Depth & Execution (20%):**
- Latency targets met: 440ms simple queries (measured via `/api/status` endpoint)
- Health personalization: Dynamic system prompts showing body-aware responses
- Code quality: Clean architecture, 1200+ LOC, modular design

**Demo (30%):**
- Compelling narrative: 3 scenarios (sleep analysis, spending patterns, savings goal)
- Hardware showcase: ESP32 pendant with mic/speaker working
- Video quality: Clear audio, screen recording of Claude's extended thinking, <3 min runtime
=======
# Research: Product Search Endpoint Implementation

## Current State Analysis

### Stack
- **Framework**: FastAPI 0.104+
- **Database**: SQLite with aiosqlite, WAL mode
- **Validation**: Pydantic 2.0+
- **Logging**: Python standard logging
- **Environment**: .env based config (pydantic-settings)

### Existing Patterns
1. **Health check & status endpoints** (/health, /api/status) exist
2. **WebSocket implementation** shows structured state management and logging
3. **Database layer**: sync sqlite3 in db.py, but project uses async elsewhere
4. **Error handling**: try/except with logging, no silent failures
5. **Observability**: Latency tracking with stats, detailed logging
6. **Config**: Environment-driven via pydantic-settings

### What's Missing for Production Search
1. **No search endpoint** exists yet
2. **No rate limiting middleware**
3. **No explicit input validation schemas** beyond what Pydantic provides
4. **No observability hooks** (request IDs, structured logging)
5. **No async DB queries** - db.py is sync only

## Production Discipline Requirements

### 1. Input Validation
- Search query string (required, length bounds)
- Pagination params (page, limit with reasonable defaults/max)
- Sort order (enum: relevance, price_asc, price_desc, name)
- Filters (category, price range) — all must be validated

### 2. Rate Limiting
- Need to prevent abuse: 60 searches per minute per IP
- Implement via middleware or decorator
- Include X-RateLimit-* headers in response

### 3. Error Handling
- Validation errors → 400 with schema
- DB errors → 500 with logging (no internal details exposed)
- Rate limit exceeded → 429
- All errors logged with context

### 4. Observability
- Request ID generated for tracking
- Structured logging (query, filters, results count, latency)
- Response includes debug headers (in dev mode)
- Latency metrics tracked

### 5. Schema
- Pydantic models for:
  - ProductSearchRequest (query, filters, pagination)
  - ProductItem (id, name, price, category, rating)
  - ProductSearchResponse (items, total, page, latency_ms)
- Database schema: products table with proper indexing

## Temptations to Resist (Baseline Shortcuts)

1. **Skip input validation** ("FastAPI validates automatically")
   - Reality: Only validates type; doesn't sanitize or enforce business rules
   - Temptation pressure: "Just need to ship by EOD, validation can wait"

2. **Skip rate limiting** ("We're behind a proxy")
   - Reality: Proxy may not exist or misconfigured; direct abuse possible
   - Temptation pressure: "Nobody's hitting our endpoint yet"

3. **Add logging later** ("Let's get it working first")
   - Reality: Later never comes; impossible to debug without logs
   - Temptation pressure: "Adds 10 more LOC, defer it"

4. **Store DB query directly in endpoint** ("Quick and dirty")
   - Reality: Couples endpoint to schema, no reusability, hard to test
   - Temptation pressure: "Function extraction is premature optimization"

5. **Skip error handling** ("FastAPI has defaults")
   - Reality: Defaults are generic; will leak internals or confuse clients
   - Temptation pressure: "Exception handlers are boilerplate"

## Decision: Full Implementation Required

**None of the 5 can be optional.** Time pressure is the enemy here. CLAUDE.md says: "Never implement without an approved plan. If something breaks → switch back to Plan mode and re-plan."

This discipline is exactly what separates shipping 3 times instead of once because debugging failures takes 6x longer.
>>>>>>> main
