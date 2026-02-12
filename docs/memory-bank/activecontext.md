# AEGIS1 — Active Context

*Last updated: Feb 12, 2026 (Day 3 of hackathon)*

## Current Phase

**Phase 1: Foundation** — Bridge server with Claude streaming + tools + health personalization working in terminal.

## What's Happening Now

- Two finalized implementation plans ready for execution:
  - **Restructure Plan** (`shiny-wondering-kitten.md`): Package rename bridge→aegis, Python 3.10+, __main__.py CLI, Apple Health XML import, dynamic health-aware system prompts (~12h, 4 phases)
  - **Edge-Optimized Restack** (`sharded-baking-lark.md`): Moonshine STT, Kokoro TTS, Silero VAD, Phi-3-mini local LLM, sqlite-vec memory, ADPCM codec (~20-26h)
- Current branch: `feat/project-config` (was feature/bridge-dev)
- Bridge code substantially implemented with core architecture decisions finalized:
  - **Direct Anthropic SDK** (not Pipecat framework)
  - **Kokoro TTS** working (82M params, Apache 2.0, local execution)
  - **claude_client.py rewritten** with true streaming via `messages.stream()` + parallel Opus pattern
  - **Haiku 4.5** for fast queries + **Opus 4.6** for deep analysis with extended thinking
- Firmware tested and working independently (ESP32 mic, speaker, WiFi, WebSocket)
- Documentation updated: MEMORY.md, projectbrief.md, techcontext.md, systempatterns.md (partial)

## Recent Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 12 | Direct Anthropic SDK (no Pipecat) | Fastest to implement, lowest latency, best Opus 4.6 showcase |
| Feb 12 | Kokoro TTS (not Piper) | Piper archived Oct 2025; Kokoro 82M Apache 2.0, 350MB ONNX, local |
| Feb 12 | Moonshine Streaming Tiny STT | 27M params, 26MB, MIT licensed, 5x faster than faster-whisper, native streaming |
| Feb 12 | Silero VAD | <1ms voice activity detection, replaces naive silence counting |
| Feb 12 | Parallel Opus Pattern | Haiku quick ack → async Opus deep analysis via asyncio.create_task() |
| Feb 12 | Dynamic Health System Prompts | 3-layer injection: static cached persona + dynamic health context + static tool directives |
| Feb 12 | Apple Health XML Import | One-time CLI import of 5 quantitative types (steps, heart_rate, weight, exercise_minutes, sleep_hours) |
| Feb 12 | sqlite-vec for memory | <50ms cosine similarity search for conversation recall |
| Feb 12 | ADPCM audio codec | 4x compression (256kbps PCM → 64kbps) for ESP32 bandwidth optimization |
| Feb 12 | Button-press only (no wake word) | Saves implementation time, still compelling demo |
| Feb 12 | Sentence-level streaming | TTS starts on first complete sentence for <440ms perceived latency |

## Known Issues / Risks

1. **Package rename pending** — Code still uses `bridge/` imports; needs systematic update to `aegis/` per restructure plan
2. **Dependencies not fully installed** — Kokoro, Moonshine, Silero, sqlite-vec not yet in virtual environment
3. **No end-to-end testing yet** — Individual components tested in isolation, full pipeline needs verification
4. **Health import not implemented** — Apple Health XML parser (health_import.py) planned but not yet written
5. **VAD module missing** — Silero VAD wrapper (vad.py) planned but not yet implemented
6. **Context builder missing** — Dynamic health context generation (context.py) for system prompt injection not yet written
7. **Memory system not implemented** — sqlite-vec integration for conversation recall planned but not started
8. **ADPCM codec not implemented** — Audio compression for ESP32 transport not yet written
9. **Local LLM not integrated** — Phi-3-mini via Ollama planned for simple queries but not yet connected

## What's Next

**Immediate (Day 3-4):**
1. Execute restructure plan Phase 1: Fix imports (bridge→aegis), verify dependencies, test streaming, verify tools
2. Execute edge-optimization plan in parallel: Add Moonshine STT, Silero VAD, health_import.py, context.py
3. Update remaining documentation: progress.md, research.md, architecture.md, plan.md, phase specs

**Near-term (Day 4-5):**
1. Phase 2 (Smart): Dynamic health prompts, tool data enrichment, demo data tuning
2. Phase 3 (Shine): Polish UX, add conversational memory (sqlite-vec), optimize latency
3. Full end-to-end testing with ESP32 hardware

**Pre-demo (Day 5-6):**
1. Phase 4 (Perfect): Write comprehensive tests, fix edge cases, demo rehearsal
2. Record demo video showcasing Opus 4.6 extended thinking + health personalization
3. Final polish and submission
