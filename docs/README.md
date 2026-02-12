# AEGIS1 Documentation

Complete technical documentation for the AEGIS1 voice health & wealth assistant project.

## 📋 Quick Navigation

### Getting Started
- **[Project Brief](memory-bank/projectbrief.md)** — What AEGIS1 is, positioning, and value proposition
- **[Tech Context](memory-bank/techcontext.md)** — Tech stack overview, setup instructions, environment variables

### Architecture & Design
- **[Architecture](architecture.md)** — System design, data models, streaming pipeline, latency targets
- **[Research](research.md)** — Tech decisions, competitive analysis, risk assessment

### Implementation
- **[Plan](plan.md)** — 4-phase implementation roadmap with detailed checklists
- **[Phase 1: Foundation](specs/phase-1-foundation.md)** — Fix & verify (package rename, CLI, dependencies)
- **[Phase 2: Smart](specs/phase-2-smart.md)** — Health personalization (dynamic prompts, Apple Health import)

### Reference & Tracking
- **[Active Context](memory-bank/activecontext.md)** — Current project status and immediate next actions
- **[Progress](memory-bank/progress.md)** — Component completion matrix and risk assessment
- **[System Patterns](memory-bank/systempatterns.md)** — Architectural patterns and design conventions

---

## 📁 Directory Structure

```
docs/
├── README.md (this file)
├── architecture.md          # System design, diagrams, latency targets
├── plan.md                  # 4-phase roadmap with checklists
├── research.md              # Tech decisions & competitive analysis
├── memory-bank/             # Active project tracking
│   ├── projectbrief.md      # Project positioning
│   ├── techcontext.md       # Tech stack & setup
│   ├── activecontext.md     # Current status & next actions
│   ├── progress.md          # Component matrix & milestones
│   └── systempatterns.md    # Design patterns & conventions
└── specs/                   # Phase specifications
    ├── phase-1-foundation.md    # Fix & verify phase (6h)
    └── phase-2-smart.md         # Health personalization phase (4h)
```

---

## 🎯 Key Sections

### For Developers
Start with **[Tech Context](memory-bank/techcontext.md)** for setup, then read **[Architecture](architecture.md)** for system design.

### For Implementation
Follow **[Plan](plan.md)** checklist for the current phase, then refer to phase-specific **[Specs](specs/)**.

### For Project Status
Check **[Active Context](memory-bank/activecontext.md)** for Day X status, and **[Progress](memory-bank/progress.md)** for completion tracking.

### For Design Decisions
See **[Research](research.md)** for why specific technologies were chosen, and **[System Patterns](memory-bank/systempatterns.md)** for architectural conventions.

---

## 📊 Current Phase

**Phase 1: Foundation (Fix & Verify)** — Days 3-4
- Package rename: bridge → aegis
- CLI entry point: `python -m aegis`
- Dependencies: Moonshine, Kokoro, Silero, sqlite-vec
- Verification: Terminal test with streaming + tools

See **[Plan](plan.md)** for detailed checklist and **[Phase 1 Spec](specs/phase-1-foundation.md)** for implementation details.

---

## 🚀 Architecture Highlights

### Core Innovation
**Body-Aware AI:** Dynamic 3-layer system prompts inject user's actual health context, making responses personalized ("You've been sleeping 6.2h..." not "People need 7-9 hours...")

### Performance
- **Simple queries (Haiku):** 440ms perceived latency
- **Complex queries (Opus):** Parallel pattern (immediate ack + async deep analysis)
- **Streaming:** Sentence-level buffering for instant TTS start

### Tech Stack
- **STT:** Moonshine Streaming Tiny (5x faster than faster-whisper)
- **TTS:** Kokoro-82M (Apache 2.0, local execution)
- **VAD:** Silero VAD (<1ms detection)
- **Memory:** sqlite-vec (<50ms semantic search)
- **Local LLM:** Phi-3-mini via Ollama (<200ms simple queries)
- **Audio:** ADPCM codec (4x compression)

### Health Personalization
- Apple Health XML import (one-time CLI setup)
- 5 tracked metrics: steps, heart_rate, weight, exercise_minutes, sleep_hours
- Dynamic health context regenerated per request
- 3-layer system prompt with ephemeral caching

---

## 📅 Project Timeline

- **Day 1-2:** Architecture finalization, core bridge code
- **Day 3-4:** Phase 1 (Foundation) — Fix imports, verify streaming
- **Day 4-5:** Phase 2 (Smart) — Health personalization
- **Day 5-6:** Phase 3-4 (Shine + Perfect) — Optimization, testing, demo

Target submission: **Feb 16, 2026** (Anthropic Claude Code Hackathon)

---

## 🔗 External References

- **GitHub:** https://github.com/Aegis-ai-labs/Aegis
- **Anthropic Claude API:** https://docs.anthropic.com
- **Moonshine STT:** https://github.com/1f3f0/moonshine
- **Kokoro TTS:** https://github.com/rsxdalv/tts-generation-webui (Kokoro models)
- **Silero VAD:** https://github.com/snakers4/silero-vad
- **sqlite-vec:** https://github.com/asg017/sqlite-vec

---

## 📝 Document Maintenance

Documentation is updated to reflect:
- ✅ Two finalized implementation plans (restructure + edge-optimization)
- ✅ Current architecture decisions (direct SDK, Moonshine, Kokoro, etc.)
- ✅ 4-phase implementation roadmap
- ✅ Latency targets and performance budgets
- ✅ Health personalization system
- ✅ Verified component status (Day 3)

Last updated: **Feb 12, 2026 (Day 3)** — See MEMORY.md for detailed status.
