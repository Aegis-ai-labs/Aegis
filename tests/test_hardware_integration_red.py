"""
RED Phase Tests: Hardware Integration (Bridge Server <-> ESP32 Contract)

TDD: These tests define the required behavior for connecting the AEGIS1 bridge
server to ESP32 hardware. They are written to FAIL initially (RED). Implement
or fix the bridge so they pass (GREEN), then refactor.

Contract under test:
1. Bridge exposes HTTP health and status endpoints.
2. Bridge exposes WebSocket /ws/audio for ESP32.
3. On connect, bridge sends a well-formed "connected" message with config.
4. Bridge accepts binary PCM chunks and responds with audio/status (e.g. listening chime).
5. Firmware snippet is obtainable and contains required symbols for WiFi and WebSocket.

Run (firmware-only, no bridge app): pytest tests/test_hardware_integration_red.py::TestFirmwareSnippetObtainable -v
Run (full suite; use bridge venv to avoid numpy/audio import issues): source bridge/.venv/bin/activate && pytest tests/test_hardware_integration_red.py -v
Expected (RED): some failures until server/firmware fully match contract.
"""

import os
import sys

# Disable mDNS/zeroconf during tests to avoid import or socket issues
os.environ.setdefault("SERVER_DISCOVERY", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-hardware-red")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# Prefer project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def bridge_client():
    """FastAPI TestClient for the bridge app (server that ESP32 connects to)."""
    from fastapi.testclient import TestClient
    from bridge.main import app
    return TestClient(app)


@pytest.fixture
def firmware_snippet():
    """Firmware code snippet from bridge (what gets loaded onto ESP32)."""
    from bridge.esp32_config import ESP32_FIRMWARE_SNIPPET
    return ESP32_FIRMWARE_SNIPPET


# =============================================================================
# 1. HTTP ENDPOINTS (Health & Status)
# =============================================================================


class TestHealthEndpoint:
    """Bridge must expose /health for monitoring and ESP32 pre-check."""

    def test_health_returns_200(self, bridge_client):
        """GET /health returns 200."""
        response = bridge_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json_with_status(self, bridge_client):
        """GET /health returns JSON with status and version."""
        response = bridge_client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data


class TestApiStatusEndpoint:
    """Bridge must expose /api/status for dashboard and debugging."""

    def test_api_status_returns_200(self, bridge_client):
        """GET /api/status returns 200."""
        response = bridge_client.get("/api/status")
        assert response.status_code == 200

    def test_api_status_returns_connections_and_latency(self, bridge_client):
        """GET /api/status returns connections count and latency stats."""
        response = bridge_client.get("/api/status")
        data = response.json()
        assert "connections" in data
        assert "latency" in data
        assert isinstance(data["connections"], int)
        assert isinstance(data["latency"], dict)


# =============================================================================
# 2. WEBSOCKET /ws/audio (ESP32 Contract)
# =============================================================================


class TestWebSocketAudioEndpoint:
    """WebSocket /ws/audio must accept ESP32 and send connected message with config."""

    def test_ws_audio_accepts_connection(self, bridge_client):
        """Client can connect to /ws/audio without error."""
        with bridge_client.websocket_connect("/ws/audio") as ws:
            pass

    def test_ws_audio_sends_connected_message_first(self, bridge_client):
        """First message after connect is JSON with type 'connected' and config."""
        with bridge_client.websocket_connect("/ws/audio") as ws:
            data = ws.receive_json()
        assert data.get("type") == "connected"
        assert "message" in data
        assert "config" in data
        assert data["config"].get("sample_rate") == 16000
        assert "chunk_size_ms" in data["config"]

    def test_ws_audio_accepts_binary_chunk(self, bridge_client):
        """Bridge accepts at least one binary PCM chunk (320 bytes) and does not disconnect."""
        with bridge_client.websocket_connect("/ws/audio") as ws:
            _ = ws.receive_json()
            ws.send_bytes(b"\x00\x00" * 160)
            ws.receive_bytes()

    def test_ws_audio_responds_with_audio_after_binary(self, bridge_client):
        """After sending PCM chunk, client receives bytes (e.g. listening chime)."""
        with bridge_client.websocket_connect("/ws/audio") as ws:
            _ = ws.receive_json()
            ws.send_bytes(b"\x00\x00" * 160)
            raw = ws.receive_bytes()
        assert isinstance(raw, bytes)
        assert len(raw) > 0


# =============================================================================
# 3. FIRMWARE SNIPPET (Load Firmware)
# =============================================================================


class TestFirmwareSnippetObtainable:
    """Firmware code must be obtainable from project and contain required symbols."""

    def test_firmware_snippet_exists(self, firmware_snippet):
        """ESP32_FIRMWARE_SNIPPET is non-empty string."""
        assert firmware_snippet
        assert isinstance(firmware_snippet, str)
        assert len(firmware_snippet) > 200

    def test_firmware_contains_ws_audio_path(self, firmware_snippet):
        """Firmware contains WebSocket path /ws/audio."""
        assert "/ws/audio" in firmware_snippet

    def test_firmware_contains_wifi_config(self, firmware_snippet):
        """Firmware contains WIFI_SSID and WIFI_PASSWORD placeholders."""
        assert "WIFI_SSID" in firmware_snippet
        assert "WIFI_PASSWORD" in firmware_snippet

    def test_firmware_contains_websocket_client(self, firmware_snippet):
        """Firmware uses WebSocketsClient and connects to bridge."""
        assert "WebSocketsClient" in firmware_snippet
        assert "webSocket" in firmware_snippet

    def test_firmware_contains_audio_send_receive(self, firmware_snippet):
        """Firmware sends binary audio and handles received audio/JSON."""
        assert "sendBIN" in firmware_snippet
        assert "WStype_BIN" in firmware_snippet or "playAudioToSpeaker" in firmware_snippet
