"""
AEGIS1 Bridge Server — FastAPI WebSocket orchestrator.

Pipeline: ESP32 audio → STT → Claude (streaming + tools) → TTS → ESP32 audio

Key design: Sentence-level streaming — TTS starts on first sentence boundary,
not after full Claude response. This is critical for <2s perceived latency.
"""

import asyncio
import json
import logging
import re
import time
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from bridge.config import settings
from bridge.db import ensure_db
from bridge.audio import pcm_to_wav, detect_silence
from bridge.audio_feedback import generate_listening_chime, generate_thinking_tone, generate_success_chime
from bridge.stt import transcribe_wav
from bridge.tts import TTSEngine
from bridge.claude_client import ClaudeClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aegis1")

# Initialize components
ensure_db()
tts_engine = TTSEngine()

# Per-connection state
connections: dict[str, dict] = {}
dashboard_clients: set[WebSocket] = set()

app = FastAPI(title="AEGIS1 Bridge", version="0.1.0")

# Latency tracking
latency_stats: dict[str, list[float]] = defaultdict(list)


def log_latency(stage: str, ms: float):
    latency_stats[stage].append(ms)
    # Keep last 100 measurements
    if len(latency_stats[stage]) > 100:
        latency_stats[stage] = latency_stats[stage][-100:]


async def broadcast_to_dashboard(event: dict):
    """Send event to all connected dashboard clients."""
    if not dashboard_clients:
        return
    disconnected = set()
    for client in dashboard_clients:
        try:
            await client.send_json(event)
        except Exception:
            disconnected.add(client)
    # Clean up disconnected clients
    dashboard_clients.difference_update(disconnected)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    with open("static/index.html") as f:
        return f.read()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/api/status")
async def api_status():
    stats = {}
    for stage, measurements in latency_stats.items():
        if measurements:
            stats[stage] = {
                "avg_ms": round(sum(measurements) / len(measurements), 1),
                "min_ms": round(min(measurements), 1),
                "max_ms": round(max(measurements), 1),
                "count": len(measurements),
            }
    return {
        "connections": len(connections),
        "latency": stats,
    }


@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket for dashboard real-time updates."""
    await websocket.accept()
    dashboard_clients.add(websocket)
    logger.info("Dashboard client connected")

    try:
        # Send initial health summary
        from bridge.context import build_health_context
        from bridge.db import get_db
        from datetime import datetime, timedelta

        health_context = build_health_context(days=7)

        # Get last 7 days of sleep for chart
        db = get_db()
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        sleep_rows = db.execute(
            "SELECT value, DATE(timestamp) as date FROM health_logs "
            "WHERE metric = 'sleep_hours' AND timestamp >= ? "
            "GROUP BY DATE(timestamp) ORDER BY date",
            (seven_days_ago,)
        ).fetchall()
        daily_sleep = [row["value"] for row in sleep_rows]
        db.close()

        await websocket.send_json({
            "type": "health_summary",
            "stats": {"Health Context": health_context},
            "daily_sleep": daily_sleep,
        })

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Dashboard client disconnected")
    finally:
        dashboard_clients.discard(websocket)


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for ESP32 audio streaming.

    Protocol:
    - ESP32 sends binary PCM chunks (16kHz, 16-bit mono, ~200ms chunks)
    - Bridge detects silence → processes pipeline
    - Bridge sends back binary PCM audio (TTS response)
    - Bridge sends JSON status messages {"type": "status", "state": "..."}
    """
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info("ESP32 connected: %s", client_id)

    claude_client = ClaudeClient()
    audio_buffer = bytearray()
    silence_counter = 0
    is_recording = False
    recording_start = 0.0

    SILENCE_CHUNKS_TO_STOP = settings.silence_chunks_to_stop
    MAX_RECORDING_MS = settings.max_recording_time_ms

    connections[client_id] = {"connected_at": time.time()}

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "AEGIS1 ready",
            "config": {"sample_rate": settings.sample_rate, "chunk_size_ms": settings.chunk_size_ms},
        })

        while True:
            data = await websocket.receive()

            # Handle binary audio data
            if "bytes" in data:
                pcm_chunk = data["bytes"]
                audio_buffer.extend(pcm_chunk)

                if not is_recording:
                    is_recording = True
                    recording_start = time.monotonic()
                    logger.debug("Recording started")
                    # Send "listening" chime
                    await websocket.send_bytes(generate_listening_chime())

                # Silence detection
                is_silent = detect_silence(pcm_chunk, threshold=500)
                if is_silent:
                    silence_counter += 1
                else:
                    silence_counter = 0

                # Recording timeout
                elapsed_ms = (time.monotonic() - recording_start) * 1000
                if elapsed_ms > MAX_RECORDING_MS:
                    silence_counter = SILENCE_CHUNKS_TO_STOP

                # End of speech detected
                if silence_counter >= SILENCE_CHUNKS_TO_STOP and len(audio_buffer) > 3200:
                    logger.info("End of speech: %d bytes, %d ms", len(audio_buffer), int(elapsed_ms))
                    await websocket.send_json({"type": "status", "state": "processing"})

                    # Send "thinking" tone
                    await websocket.send_bytes(generate_thinking_tone())

                    # Run the full pipeline
                    await process_pipeline(
                        websocket, claude_client, bytes(audio_buffer)
                    )

                    # Reset
                    audio_buffer.clear()
                    silence_counter = 0
                    is_recording = False

                    await websocket.send_json({"type": "status", "state": "idle"})

            # Handle JSON control messages
            elif "text" in data:
                try:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "end_of_speech":
                        # Explicit end-of-speech from ESP32 (button release)
                        if len(audio_buffer) > 3200:
                            await websocket.send_json({"type": "status", "state": "processing"})
                            await process_pipeline(
                                websocket, claude_client, bytes(audio_buffer)
                            )
                            audio_buffer.clear()
                            silence_counter = 0
                            is_recording = False
                            await websocket.send_json({"type": "status", "state": "idle"})
                    elif msg.get("type") == "reset":
                        claude_client.reset_conversation()
                        audio_buffer.clear()
                        silence_counter = 0
                        is_recording = False
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("ESP32 disconnected: %s", client_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
    finally:
        connections.pop(client_id, None)


async def process_pipeline(websocket: WebSocket, claude_client: ClaudeClient, audio_data: bytes):
    """Full speech-to-speech pipeline with sentence-level streaming."""
    pipeline_start = time.monotonic()

    # Stage 1: STT
    stt_start = time.monotonic()
    wav_data = pcm_to_wav(audio_data)
    text = transcribe_wav(wav_data)
    stt_ms = (time.monotonic() - stt_start) * 1000
    log_latency("stt", stt_ms)

    if not text:
        logger.warning("STT returned empty — skipping")
        return

    logger.info("STT [%.0fms]: %s", stt_ms, text)

    # Broadcast user message to dashboard
    await broadcast_to_dashboard({"type": "user_message", "text": text})

    # Stage 2: Claude (streaming with tools)
    llm_start = time.monotonic()
    full_response = ""
    sentence_buffer = ""
    first_audio_sent = False

    async for chunk in claude_client.get_response(text):
        full_response += chunk
        sentence_buffer += chunk

        # Check for sentence boundary — stream TTS immediately
        sentences = re.split(r'(?<=[.!?])\s+', sentence_buffer)
        if len(sentences) > 1:
            # We have at least one complete sentence
            for complete_sentence in sentences[:-1]:
                if complete_sentence.strip():
                    tts_start = time.monotonic()
                    pcm_audio = tts_engine.synthesize(complete_sentence.strip())
                    tts_ms = (time.monotonic() - tts_start) * 1000

                    if pcm_audio:
                        if not first_audio_sent:
                            perceived_ms = (time.monotonic() - pipeline_start) * 1000
                            log_latency("perceived", perceived_ms)
                            logger.info("First audio at %.0fms (perceived latency)", perceived_ms)
                            first_audio_sent = True

                        log_latency("tts", tts_ms)
                        await websocket.send_json({"type": "status", "state": "speaking"})
                        # Send PCM in chunks to avoid overwhelming ESP32
                        chunk_size = 6400  # 200ms at 16kHz
                        for i in range(0, len(pcm_audio), chunk_size):
                            await websocket.send_bytes(pcm_audio[i:i + chunk_size])
                            await asyncio.sleep(0.01)  # Small delay for ESP32 to buffer

            sentence_buffer = sentences[-1]  # Keep incomplete sentence

    # Send any remaining text
    if sentence_buffer.strip():
        pcm_audio = tts_engine.synthesize(sentence_buffer.strip())
        if pcm_audio:
            if not first_audio_sent:
                perceived_ms = (time.monotonic() - pipeline_start) * 1000
                log_latency("perceived", perceived_ms)
                first_audio_sent = True
            chunk_size = 6400
            for i in range(0, len(pcm_audio), chunk_size):
                await websocket.send_bytes(pcm_audio[i:i + chunk_size])
                await asyncio.sleep(0.01)

    llm_ms = (time.monotonic() - llm_start) * 1000
    log_latency("llm", llm_ms)

    total_ms = (time.monotonic() - pipeline_start) * 1000
    log_latency("total", total_ms)

    # Broadcast assistant response to dashboard
    await broadcast_to_dashboard({
        "type": "assistant_message",
        "text": full_response,
        "model": "haiku" if "haiku" in str(claude_client) else "opus",
        "latency_ms": llm_ms,
    })

    # Send "success" chime
    await websocket.send_bytes(generate_success_chime())

    await websocket.send_json({
        "type": "done",
        "latency": {
            "stt_ms": round(stt_ms, 1),
            "llm_ms": round(llm_ms, 1),
            "total_ms": round(total_ms, 1),
        },
    })

    logger.info(
        "Pipeline complete: stt=%.0fms, llm=%.0fms, total=%.0fms | %s → %s",
        stt_ms, llm_ms, total_ms,
        text[:50], full_response[:80],
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("  AEGIS1 Bridge Server Starting")
    logger.info("=" * 60)
    logger.info("  Port: %d", settings.bridge_port)
    logger.info("  Claude: Haiku=%s, Opus=%s", settings.claude_haiku_model, settings.claude_opus_model)
    logger.info("  STT: faster-whisper (%s)", settings.stt_model)
    logger.info("  TTS: Piper")
    logger.info("  WebSocket: ws://%s:%d/ws/audio", settings.bridge_host, settings.bridge_port)
    logger.info("=" * 60)

    uvicorn.run(
        "bridge.main:app",
        host=settings.bridge_host,
        port=settings.bridge_port,
        log_level="info",
    )
