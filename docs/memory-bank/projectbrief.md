# AEGIS1 — Project Brief

## Mission

AEGIS1 is an AI-powered voice pendant that helps adults (ages 30-65) manage their **health and wealth** through natural conversation. Speak to your pendant to log meals, track sleep, record expenses, analyze spending patterns, and get actionable health insights — all without touching a screen.

## What AEGIS1 Is

- A wearable voice assistant (ESP32 pendant with mic, speaker, LED, button)
- A Python bridge server that orchestrates speech-to-speech AI conversations
- A showcase of Claude's tool-use capabilities (6 specialized tools for health & wealth)
- A dual-model system: Haiku 4.5 for speed, Opus 4.6 for deep analysis
- Built for the Anthropic Claude Code Hackathon (Feb 10-16, 2026)

## What AEGIS1 Is Not

- Not a medical device or financial advisor (informational only)
- Not a general-purpose assistant (scoped to health + wealth)
- Not cloud-dependent for STT/TTS (faster-whisper and Piper run locally)
- Not a wake-word device (button-press activation for the hackathon)

## Target Users

Adults 30-65 who want frictionless daily health and expense tracking without app fatigue. People who would benefit from pattern analysis ("your sleep drops on days you skip exercise") and spending awareness ("you've spent $140 on food this week, up 30% from last week").

## Hackathon Context

- **Event:** Anthropic Claude Code Hackathon (Feb 10-16, 2026)
- **Judging Criteria:**
  - Impact (25%) — Real-world usefulness of health + wealth tracking
  - Opus 4.6 Use (25%) — Intelligent model routing, extended thinking for analysis
  - Depth & Execution (20%) — Full stack: hardware + bridge + AI pipeline
  - Demo (30%) — Live voice interaction with real data

## Core Goals

1. **Sub-2-second perceived latency** — sentence-level streaming (TTS starts before Claude finishes)
2. **Intelligent model routing** — Haiku for "log my coffee" (fast), Opus for "analyze my sleep patterns" (deep)
3. **Real tool use** — Claude actually queries SQLite, not canned responses
4. **End-to-end demo** — ESP32 hardware talking to Claude through the full pipeline

## Team

- **Aegis.ai-labs** — Solo developer / hardware + software
