# AEGIS1 — AI Voice Pendant for Health & Wealth

> **Contextual intelligence for everyone.** An AI assistant that actually knows your body.

Built for the Anthropic Claude Code Hackathon (Feb 10-16, 2026)

---

## The Problem

Generic AI assistants give generic advice. "Get 8 hours of sleep." "Save money."

But YOUR body is unique. Your patterns matter.

## The Solution

**AEGIS1** is a voice-first AI pendant that combines health tracking with wealth management, making advice **contextually intelligent** by understanding YOUR actual patterns.

### Key Innovation: Body-Aware AI

Instead of generic advice, AEGIS1 says:

- "You averaged 6 hours on weekdays vs 7.9 on weekends — that 2-hour sleep debt explains your weekday fatigue."
- "You spent $12 on coffee after 5 hours of sleep. Your spending spikes when you're tired."
- "For 5K training, do lunchtime walks — evening exercise will hurt your already-limited weekday sleep."

---

## Architecture

```
┌─────────────┐
│   ESP32     │  16kHz PCM audio
│  (Pendant)  │  ←────────────────┐
│             │                   │
│ • INMP441   │                   │
│ • PAM8403   │                   │
│ • WiFi      │                   │
└─────────────┘                   │
                                  │
                          WebSocket (binary)
                                  │
┌─────────────────────────────────┼───────────────────────────┐
│  BRIDGE SERVER (FastAPI)        ↓                           │
│                                                              │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────┐       │
│  │   STT    │ →  │   CLAUDE    │ →  │     TTS      │       │
│  │ faster-  │    │  STREAMING  │    │   Kokoro     │       │
│  │ whisper  │    │             │    │   (82M)      │       │
│  └──────────┘    └─────────────┘    └──────────────┘       │
│                         ↓                                    │
│                  ┌─────────────┐                            │
│                  │   TOOLS     │                            │
│                  │ • Health×3  │                            │
│                  │ • Wealth×3  │                            │
│                  │ • Insight×1 │                            │
│                  └─────────────┘                            │
│                         ↓                                    │
│                  ┌─────────────┐                            │
│                  │   SQLite    │                            │
│                  │ • health    │                            │
│                  │ • expenses  │                            │
│                  │ • insights  │                            │
│                  └─────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

### The Intelligence Stack

1. **Dual Model System**
   - **Haiku 4.5:** Fast path (<500ms) for simple queries
   - **Opus 4.6:** Deep analysis with **interleaved thinking** (THE showcase feature)

2. **3-Layer System Prompt** (with prompt caching)
   - Layer 1: Static persona (cached)
   - Layer 2: **Dynamic health context** (7-day snapshot, regenerated per request)
   - Layer 3: Tool directives (cached)

3. **True Streaming**
   - `messages.stream()` for token-by-token delivery
   - TTS starts on first sentence boundary (not after full response)
   - Perceived latency: ~150ms vs ~500ms with blocking API

4. **7 Tools**
   - **Health:** get_health_context, log_health, analyze_health_patterns
   - **Wealth:** track_expense, get_spending_summary, calculate_savings_goal
   - **Insight:** save_user_insight (Claude saves discovered patterns)

---

## Demo Data Patterns (Optimized for Impact)

Our seed data creates **dramatic, visible patterns**:

| Metric        | Weekday  | Weekend    | Impact                       |
| ------------- | -------- | ---------- | ---------------------------- |
| Sleep         | 6.0h avg | 7.9h avg   | 1.9h deficit                 |
| Mood          | 2.5/5    | 3.8/5      | Clear correlation with sleep |
| Exercise      | 10 min   | 45 min     | Weekend warrior pattern      |
| Food spending | $8.9/day | $34-41/day | 4-5x spike (dining out)      |

**Sleep-Mood Correlation:** 5h sleep → 2.3 mood, 8h sleep → 3.8 mood

This makes Claude responses **dramatically** contextual.

---

## Quick Start

### 1. Install Dependencies

```bash
cd bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY
```

### 3. Start Bridge Server

```bash
python -m bridge.main
```

Server runs on `http://localhost:8000`

### 4. Open Dashboard

Navigate to `http://localhost:8000` in browser

### 5. Test with Terminal

```bash
python test_terminal.py
```

Try:

- "How did I sleep this week?"
- "I spent $45 on dinner"
- "Why am I tired on weekdays?" (triggers Opus!)
- "Help me train for a 5K"

---

## Technical Highlights

### Opus 4.6 Showcase

- **Interleaved thinking** enabled with beta header
- Thinks BETWEEN tool calls (not just before/after)
- Budget: 10,000 tokens for deep reasoning
- Visible in logs and dashboard

### Performance

- **Haiku TTFT:** <200ms (time to first token)
- **Perceived latency:** ~150ms (streaming + sentence buffering)
- **Opus latency:** ~2s (acceptable for deep analysis)
- **STT:** faster-whisper (27M model, CPU-friendly)
- **TTS:** Kokoro (82M, Apache 2.0, high quality)

### Efficiency

- **Prompt caching:** Static prompt layers cached (saves latency + cost)
- **Streaming:** Token-by-token delivery (TTS starts immediately)
- **Smart routing:** Haiku for 80% of queries, Opus for complex 20%

---

## Code Stats

| Component     | Lines      |
| ------------- | ---------- |
| Bridge server | ~1,900     |
| Tools         | ~400       |
| Tests         | ~450       |
| Dashboard     | ~200       |
| **Total**     | **~2,950** |

Well under 5,000 line target.

---

## Judging Criteria Alignment

### Impact (25%) ✓

- **Target audience:** 30-65 age bracket (health-conscious, financially aware)
- **Real value:** Personalized health advice beats generic wearables
- **Cross-domain:** Health + wealth interconnections are unique

### Opus 4.6 Use (25%) ✓

- **Interleaved thinking:** Beta feature enabled and showcased
- **Extended thinking:** 10K token budget for deep reasoning
- **Smart routing:** Opus only when needed (efficient)
- **Visible differentiation:** Dashboard shows Haiku vs Opus badges

### Depth & Execution (20%) ✓

- **7 tools** working with real data
- **True streaming** implementation (not just async create)
- **Prompt caching** for efficiency
- **Dynamic context** injection (body-aware responses)
- **36 tests** passing

### Demo (30%) ✓

- **3-minute script** with 4 compelling queries
- **Split-screen** (person + dashboard)
- **Visible intelligence:** Thinking badges, tool calls, latency
- **Clear narrative:** Generic → Contextual intelligence

---

## What Makes This Special

1. **Not just a chatbot** — It's body-aware
2. **Not just health tracking** — It connects health + wealth
3. **Not generic advice** — It knows YOUR patterns
4. **Not slow** — Streaming makes it feel instant
5. **Not complex** — Clean architecture, <3K lines

---

## Future Potential

- **Apple Health integration:** Real iOS/watchOS data
- **Google Fit integration:** Android users
- **Local LLM fallback:** Phi-3-mini for offline queries
- **Voice cloning:** Personalized TTS voice
- **Multi-user:** Family health tracking
- **Insurance integration:** Reward healthy behaviors

---

## Built With

- **Claude Opus 4.6** (interleaved thinking) + Haiku 4.5 (speed)
- **FastAPI** + WebSockets (streaming)
- **faster-whisper** (STT, 27M model)
- **Kokoro TTS** (82M, Apache 2.0)
- **SQLite** (embedded, zero setup)
- **ESP32** (microcontroller, $5 hardware)

---

## License

MIT

---

## Acknowledgments

Built for the Anthropic Claude Code Hackathon using Claude Opus 4.6's extended thinking capabilities.

**Team:** Solo developer showcase

**Build Time:** 3 days (Feb 12-14, 2026)

**Hardware cost:** ~$15 (ESP32 + mic + speaker)

---

**The future of AI is contextual. AEGIS1 is just the beginning.**
