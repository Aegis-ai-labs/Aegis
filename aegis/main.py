"""AEGIS1 Bridge Server — FastAPI WebSocket entry point.

Handles:
- WebSocket connections from ESP32 pendant (binary audio + text)
- Text-only mode for testing without hardware
- Health check endpoint
"""

import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .claude_client import ClaudeClient
from .config import settings
from .db import ensure_db, close_db

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown: initialize DB, seed demo data if needed."""
    log.info(f"AEGIS1 Bridge starting on {settings.bridge_host}:{settings.bridge_port}")
    ensure_db()  # Initialize DB tables + seed demo data
    log.info("Database initialized")
    yield
    await close_db()
    log.info("AEGIS1 Bridge shut down")


app = FastAPI(title="AEGIS1 Bridge", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "aegis1-bridge"})


@app.websocket("/ws/text")
async def text_ws(websocket: WebSocket):
    """Text-only WebSocket for testing Claude integration without audio.

    Protocol:
    - Client sends JSON: {"text": "user message"}
    - Server streams JSON: {"text": "sentence chunk", "done": false}
    - Final message: {"text": "", "done": true}
    """
    await websocket.accept()
    client = ClaudeClient()
    log.info("Text WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            user_text = msg.get("text", "").strip()
            if not user_text:
                await websocket.send_json({"error": "Empty text"})
                continue

            if user_text.lower() == "/reset":
                await client.reset()
                await websocket.send_json({"text": "Conversation reset.", "done": True})
                continue

            log.info(f"User: {user_text}")
            t0 = time.monotonic()

            async for sentence in client.chat(user_text):
                await websocket.send_json({"text": sentence, "done": False})
                log.debug(f"Sent: {sentence}")

            await websocket.send_json({"text": "", "done": True})
            elapsed = time.monotonic() - t0
            log.info(f"Full response in {elapsed:.2f}s")

    except WebSocketDisconnect:
        log.info("Text WebSocket disconnected")


@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    """Audio WebSocket for ESP32 pendant.

    Protocol (Phase 2 — currently returns text-only):
    - Client sends binary: raw PCM or ADPCM audio chunks
    - Server sends binary: PCM/ADPCM audio response chunks
    - Control messages via JSON text frames
    """
    await websocket.accept()
    client = ClaudeClient()
    log.info("Audio WebSocket connected")

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                # Control message (JSON)
                try:
                    msg = json.loads(data["text"])
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "reset":
                    await client.reset()
                    await websocket.send_json({"type": "reset_ack"})
                elif msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            elif "bytes" in data:
                # Audio data — Phase 2 will add STT/TTS pipeline here.
                # For now, just acknowledge receipt.
                log.debug(f"Received {len(data['bytes'])} bytes of audio")
                await websocket.send_json({
                    "type": "error",
                    "message": "Audio pipeline not yet implemented. Use /ws/text for testing.",
                })

    except WebSocketDisconnect:
        log.info("Audio WebSocket disconnected")


def main():
    """Run the bridge server."""
    import uvicorn

    uvicorn.run(
        "aegis.main:app",
        host=settings.bridge_host,
        port=settings.bridge_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
