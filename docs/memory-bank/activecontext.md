# AEGIS1 — Active Context

*Last updated: Feb 12, 2026 (Day 3 of hackathon)*

## Current Phase

**Phase 1: Foundation** — Bridge server with Claude streaming + tools working in terminal.

## What's Happening Now

- Bridge server code is substantially implemented in `feature/bridge-dev` worktree
- All core modules exist: config, db, claude_client, audio, stt, tts, main, tools
- The code has not yet been tested end-to-end (dependencies not installed/verified)
- Firmware is tested and working independently (mic, speaker, WiFi, WebSocket on ESP32)
- Main branch has only `.gitignore` and initial commit — bridge code not yet merged

## Recent Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 12 | Claude-native (no Pipecat framework) | Fastest to implement, lowest latency, best Opus showcase |
| Feb 12 | Piper TTS over OpenAI TTS | Free, local, no API dependency, low latency |
| Feb 12 | Button-press only (no wake word) | Saves implementation time, still compelling demo |
| Feb 12 | SQLite over cloud DB | Zero setup, embedded, hackathon-appropriate |
| Feb 12 | Firmware already tested | Skip firmware rework, focus on bridge software |
| Feb 12 | Sentence-level streaming | TTS on first sentence boundary for <2s perceived latency |

## Known Issues / Risks

1. **STT `stt_beam_size` config missing** — `stt.py:62` references `settings.stt_beam_size` but `config.py` doesn't define it. Will error on first STT call.
2. **Piper model not bundled** — `PIPER_MODEL_PATH` defaults to empty string. Need to download a voice model.
3. **No tests yet** — Zero test files exist. Phase 4 deliverable.
4. **Claude client uses sync API** — `self.client.messages.create()` is blocking. Works for single-connection hackathon but won't scale. Not a concern for demo.
5. **`silence_chunks_to_stop` / `max_recording_time_ms` missing from Settings** — `main.py` uses `hasattr()` fallback, but should be in `config.py`.

## What's Next

1. Fix config gaps (beam_size, silence settings)
2. Install dependencies and verify each module loads
3. Test Claude client with terminal input (Phase 1 verification)
4. Test all 6 tools return correct data
5. Move to Phase 2: full audio pipeline testing
