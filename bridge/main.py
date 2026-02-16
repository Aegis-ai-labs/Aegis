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
from pathlib import Path

import anthropic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from bridge.config import settings
from bridge.db import ensure_db
from bridge.audio import pcm_to_wav, detect_silence
from bridge.audio_feedback import generate_thinking_tone, generate_success_chime
from bridge.stt import transcribe_wav
from bridge.tts import TTSEngine
from bridge.llm_router import get_llm_client
from bridge.claude_client import set_dashboard_broadcast as set_claude_dashboard_broadcast
from bridge.gemini_client import set_dashboard_broadcast as set_gemini_dashboard_broadcast

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

# Register dashboard broadcast callback for both LLM clients
set_claude_dashboard_broadcast(broadcast_to_dashboard)
set_gemini_dashboard_broadcast(broadcast_to_dashboard)


# Project root (parent of bridge package) for static files
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    index_path = _STATIC_DIR / "index.html"
    with open(index_path) as f:
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
        "esp32_connected": len(connections) > 0,
        "connections": len(connections),
        "esp32_clients": list(connections.keys()),
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

        health_context_str = build_health_context(days=7)

        # Parse health context string into structured stats for dashboard
        stats = {}
        if health_context_str and health_context_str != "No recent health data available." and health_context_str != "No recent health or spending data available.":
            # Parse "Sleep: avg 7.2h | Exercise: 30min | Mood: 8.5" format
            parts = health_context_str.split(" | ")
            for part in parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    stats[key.strip()] = value.strip()
        else:
            stats = {"Status": "No recent data"}

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
            "stats": stats,  # Now properly structured object
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

    llm_client = get_llm_client()
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
            try:
                data = await websocket.receive()
            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    logger.info("ESP32 disconnected: %s", client_id)
                    break
                raise

            # Handle binary audio data
            if "bytes" in data:
                pcm_chunk = data["bytes"]
                audio_buffer.extend(pcm_chunk)

                if not is_recording:
                    is_recording = True
                    recording_start = time.monotonic()
                    logger.debug("Recording started")
                    # No listening chime on first chunk: speaker only outputs after user speaks and pipeline runs

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
                # Require: silence detected + minimum recording length + actual speech content (not just ambient noise)
                if silence_counter >= SILENCE_CHUNKS_TO_STOP and len(audio_buffer) > 3200:
                    # Check if there was actual speech (not just silence/ambient noise)
                    from bridge.audio import calculate_rms
                    rms = calculate_rms(audio_buffer)
                    MIN_SPEECH_RMS = 800  # Minimum RMS to consider it actual speech (not ambient noise)
                    MIN_RECORDING_MS = 500  # Minimum recording duration to avoid false triggers
                    
                    # Reject if audio is too quiet OR recording too short
                    if rms < MIN_SPEECH_RMS:
                        logger.info("End of speech ignored: audio too quiet (RMS=%.0f < %d), likely ambient noise", rms, MIN_SPEECH_RMS)
                        # Reset and continue recording
                        audio_buffer.clear()
                        is_recording = False
                        silence_counter = 0
                        continue
                    
                    if elapsed_ms < MIN_RECORDING_MS:
                        logger.info("End of speech ignored: recording too short (%d ms < %d ms), likely false trigger", int(elapsed_ms), MIN_RECORDING_MS)
                        # Reset and continue recording
                        audio_buffer.clear()
                        is_recording = False
                        silence_counter = 0
                        continue
                    
                    logger.info("End of speech: %d bytes, %d ms, RMS=%.0f", len(audio_buffer), int(elapsed_ms), rms)
                    await websocket.send_json({"type": "status", "state": "processing"})
                    await broadcast_to_dashboard({"type": "pipeline_state", "state": "processing"})

                    # Run the full pipeline - thinking tone will be sent INSIDE process_pipeline only if STT succeeds
                    # This prevents sending audio feedback for false triggers
                    await process_pipeline(
                        websocket, llm_client, bytes(audio_buffer)
                    )

                    # Reset
                    audio_buffer.clear()
                    silence_counter = 0
                    is_recording = False

                    await websocket.send_json({"type": "status", "state": "idle"})
                    await broadcast_to_dashboard({"type": "pipeline_state", "state": "idle"})

            # Handle JSON control messages
            elif "text" in data:
                try:
                    msg = json.loads(data["text"])
                        if msg.get("type") == "end_of_speech":
                        # Explicit end-of-speech from ESP32 (button release)
                        if len(audio_buffer) > 3200:
                            await websocket.send_json({"type": "status", "state": "processing"})
                            await broadcast_to_dashboard({"type": "pipeline_state", "state": "processing"})
                            # Thinking tone will be sent inside process_pipeline only if STT succeeds
                            await process_pipeline(
                                websocket, llm_client, bytes(audio_buffer)
                            )
                            audio_buffer.clear()
                            silence_counter = 0
                            is_recording = False
                            await websocket.send_json({"type": "status", "state": "idle"})
                            await broadcast_to_dashboard({"type": "pipeline_state", "state": "idle"})
                    elif msg.get("type") == "reset":
                        llm_client.reset_conversation()
                        audio_buffer.clear()
                        silence_counter = 0
                        is_recording = False
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("ESP32 disconnected: %s", client_id)
    except RuntimeError as e:
        if "disconnect" in str(e).lower():
            logger.info("ESP32 disconnected: %s", client_id)
        else:
            logger.error("WebSocket error: %s", e, exc_info=True)
    except Exception as e:
        logger.error("WebSocket error: %s", e, exc_info=True)
    finally:
        connections.pop(client_id, None)


@app.on_event("startup")
async def startup_event():
    """Initialize mDNS service discovery for ESP32 auto-connect."""
    if not settings.server_discovery_enabled:
        return
    
    try:
        from zeroconf import ServiceInfo, Zeroconf
        import socket
        
        # Get the local IP address
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Register mDNS service (type must start with '_' per RFC 6763)
        service_type = f"_{settings.mdns_service_name}._tcp.local."
        service_info = ServiceInfo(
            service_type,
            f"{settings.mdns_service_name}.{service_type}",
            addresses=[socket.inet_aton(local_ip)],
            port=settings.bridge_port,
            properties={
                "path": "/ws/audio",
                "version": "0.1.0",
                "model": "AEGIS1",
            },
            server=f"{hostname}.local.",
        )
        
        zeroconf = Zeroconf()
        zeroconf.register_service(service_info)
        logger.info(
            "mDNS registered: %s.local:%d (ESP32 can auto-discover)",
            settings.mdns_service_name, settings.bridge_port
        )
        
        # Store for cleanup
        app.state.zeroconf = zeroconf
        app.state.service_info = service_info
        
    except ImportError:
        logger.warning("zeroconf not installed - mDNS discovery disabled. Install: pip install zeroconf")
    except Exception as e:
        logger.warning("Failed to register mDNS: %s", str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up mDNS registration."""
    if hasattr(app.state, "zeroconf"):
        try:
            app.state.zeroconf.unregister_service(app.state.service_info)
            app.state.zeroconf.close()
            logger.info("mDNS service unregistered")
        except Exception as e:
            logger.warning("Error unregistering mDNS: %s", str(e))


async def process_pipeline(websocket: WebSocket, llm_client, audio_data: bytes):
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
    
    # Send "thinking" tone ONLY after STT succeeds (prevents false triggers from causing audio feedback)
    thinking_tone = generate_thinking_tone()
    logger.debug("Sending thinking tone: %d bytes", len(thinking_tone))
    await websocket.send_bytes(thinking_tone)

    # Broadcast user message to dashboard
    await broadcast_to_dashboard({"type": "user_message", "text": text})

    # Stage 2: Claude (streaming with tools)
    llm_start = time.monotonic()
    full_response = ""
    sentence_buffer = ""
    first_audio_sent = False

    try:
        async for chunk in llm_client.get_response(text):
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
                            try:
                                await websocket.send_json({"type": "status", "state": "speaking"})
                                await broadcast_to_dashboard({"type": "pipeline_state", "state": "speaking"})
                                # Send PCM in chunks to avoid overwhelming ESP32
                                chunk_size = 6400  # 200ms at 16kHz
                                logger.debug("Sending TTS audio: %d bytes total, %d chunks", len(pcm_audio), (len(pcm_audio) + chunk_size - 1) // chunk_size)
                                for i in range(0, len(pcm_audio), chunk_size):
                                    chunk = pcm_audio[i:i + chunk_size]
                                    await websocket.send_bytes(chunk)
                                    await asyncio.sleep(0.01)  # Small delay for ESP32 to buffer
                            except WebSocketDisconnect:
                                logger.warning("ESP32 disconnected during audio transmission")
                                return

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
                try:
                    for i in range(0, len(pcm_audio), chunk_size):
                        chunk = pcm_audio[i:i + chunk_size]
                        logger.debug("Sending TTS audio chunk: %d bytes", len(chunk))
                        await websocket.send_bytes(chunk)
                        await asyncio.sleep(0.01)
                except WebSocketDisconnect:
                    logger.warning("ESP32 disconnected during final audio transmission")
                    return

    except anthropic.APIError as e:
        logger.error("Claude API error: %s", str(e), exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Claude API error. Please check your API key and try again."
            })
        except WebSocketDisconnect:
            logger.warning("ESP32 disconnected before error message could be sent")
        return
    except Exception as e:
        logger.error("Unexpected error in LLM processing: %s", str(e), exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "An error occurred during processing. Please try again."
            })
        except WebSocketDisconnect:
            logger.warning("ESP32 disconnected before error message could be sent")
        return

    llm_ms = (time.monotonic() - llm_start) * 1000
    log_latency("llm", llm_ms)

    total_ms = (time.monotonic() - pipeline_start) * 1000
    log_latency("total", total_ms)

    # Broadcast assistant response to dashboard
    await broadcast_to_dashboard({
        "type": "assistant_message",
        "text": full_response,
        "model": llm_client.__class__.__name__.lower(),  # "claudeclient" or "geminiclient"
        "latency_ms": llm_ms,
    })

    # Send "success" chime and final status
    try:
        success_chime = generate_success_chime()
        logger.debug("Sending success chime: %d bytes", len(success_chime))
        await websocket.send_bytes(success_chime)

        await websocket.send_json({
            "type": "done",
            "latency": {
                "stt_ms": round(stt_ms, 1),
                "llm_ms": round(llm_ms, 1),
                "total_ms": round(total_ms, 1),
            },
        })
    except WebSocketDisconnect:
        logger.warning("ESP32 disconnected before success chime could be sent")
        # Don't return - let logger.info below execute

    logger.info(
        "Pipeline complete: stt=%.0fms, llm=%.0fms, total=%.0fms | %s → %s",
        stt_ms, llm_ms, total_ms,
        text[:50], full_response[:80],
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 70)
    logger.info("  AEGIS1 BRIDGE SERVER STARTING")
    logger.info("=" * 70)
    
    # LLM Configuration
    if settings.use_local_model:
        logger.info("  LLM: Ollama (local testing)")
        logger.info("       URL: %s", settings.ollama_url)
        logger.info("       Model: %s (FREE - perfect for development)", settings.ollama_model)
    elif settings.use_gemini_for_testing:
        logger.info("  LLM: Gemini (budget testing)")
    else:
        logger.info("  LLM: Claude (production)")
        logger.info("       Haiku: %s", settings.claude_haiku_model)
        logger.info("       Opus: %s", settings.claude_opus_model)
    
    # Server Configuration
    logger.info("  Server:")
    logger.info("       Host: %s:%d", settings.bridge_host, settings.bridge_port)
    logger.info("       WebSocket: ws://localhost:%d/ws/audio", settings.bridge_port)
    logger.info("       Dashboard: http://localhost:%d/", settings.bridge_port)
    
    # Audio Configuration
    logger.info("  Audio:")
    logger.info("       STT: faster-whisper (%s)", settings.stt_model)
    logger.info("       TTS: Piper")
    logger.info("       Sample Rate: %d Hz", settings.sample_rate)
    
    # Service Discovery
    if settings.server_discovery_enabled:
        logger.info("  mDNS Discovery:")
        logger.info("       Service: %s.local:%d", settings.mdns_service_name, settings.bridge_port)
        logger.info("       ESP32 can auto-discover and connect")
    
    # Test Mode
    if settings.test_mode:
        logger.info("  TEST MODE: API key validation disabled")
    
    logger.info("=" * 70)

    uvicorn.run(
        "bridge.main:app",
        host=settings.bridge_host,
        port=settings.bridge_port,
        log_level="info",
    )
