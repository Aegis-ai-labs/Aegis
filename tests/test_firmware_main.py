"""
Tests for AEGIS1 firmware main file (firmware/src/main.cpp).

Verifies that the firmware source matches the bridge contract so that
flashed hardware can connect to the AEGIS1 bridge. Firmware is taken
from the AEGIS prototype (test_5_openclaw_voice) and maintained here.

TDD: Most tests here are contract/characterization tests (written against
existing firmware; they passed on first run). For new firmware behavior,
write a failing test first (RED), then implement (GREEN), then refactor.
One test (test_documents_bridge_contract_version) drives an explicit
contract version so we can detect protocol drift.

Run:
  pip install -e ".[dev]"
  pytest tests/test_firmware_main.py -v
"""

import os
import pytest

# Paths relative to project root
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
FIRMWARE_MAIN = os.path.join(PROJECT_ROOT, "firmware", "src", "main.cpp")
FIRMWARE_CONFIG = os.path.join(PROJECT_ROOT, "firmware", "config.h")
FIRMWARE_CONFIG_TEMPLATE = os.path.join(PROJECT_ROOT, "firmware", "config.h.template")


def read_firmware_main() -> str:
    """Read firmware main.cpp content."""
    with open(FIRMWARE_MAIN, "r") as f:
        return f.read()


def read_config() -> str:
    """Read firmware config.h content."""
    with open(FIRMWARE_CONFIG, "r") as f:
        return f.read()


class TestFirmwareMainExists:
    """Firmware main file and config must exist."""

    def test_main_cpp_exists(self):
        """firmware/src/main.cpp exists."""
        assert os.path.isfile(FIRMWARE_MAIN), f"Missing {FIRMWARE_MAIN}"

    def test_config_h_exists(self):
        """firmware/config.h exists."""
        assert os.path.isfile(FIRMWARE_CONFIG), f"Missing {FIRMWARE_CONFIG}"

    def test_config_template_exists(self):
        """firmware/config.h.template exists."""
        assert os.path.isfile(FIRMWARE_CONFIG_TEMPLATE), f"Missing {FIRMWARE_CONFIG_TEMPLATE}"


class TestFirmwareMainContract:
    """Firmware main must match bridge WebSocket and audio contract."""

    @pytest.fixture
    def main_content(self):
        return read_firmware_main()

    def test_contains_ws_audio_path(self, main_content):
        """Main uses WebSocket path /ws/audio (bridge endpoint)."""
        assert "/ws/audio" in main_content

    def test_uses_bridge_host_and_port(self, main_content):
        """Main uses BRIDGE_HOST and BRIDGE_PORT from config."""
        assert "BRIDGE_HOST" in main_content
        assert "BRIDGE_PORT" in main_content

    def test_sends_binary_audio(self, main_content):
        """Main sends binary PCM via sendBIN (bridge expects binary chunks)."""
        assert "sendBIN" in main_content

    def test_handles_binary_response(self, main_content):
        """Main handles WStype_BIN (TTS PCM from bridge)."""
        assert "WStype_BIN" in main_content

    def test_handles_connected_event(self, main_content):
        """Main handles WStype_CONNECTED (bridge sends connected message first)."""
        assert "WStype_CONNECTED" in main_content

    def test_chunk_size_320_or_defined(self, main_content):
        """Main uses 320-byte chunk (10ms @ 16kHz 16-bit) or SEND_CHUNK_BYTES."""
        assert "320" in main_content or "SEND_CHUNK_BYTES" in main_content

    def test_websocket_client_used(self, main_content):
        """Main uses WebSocketsClient (links2004/WebSockets)."""
        assert "WebSocketsClient" in main_content
        assert "webSocket" in main_content

    def test_i2s_mic_and_dac_speaker(self, main_content):
        """Main uses I2S for mic and DAC for speaker (hardware contract)."""
        assert "i2s" in main_content or "I2S" in main_content
        assert "dacWrite" in main_content or "AMP_DAC_PIN" in main_content

    def test_documents_bridge_contract_version(self, main_content):
        """Main documents bridge contract version for protocol drift detection (TDD: RED then GREEN)."""
        # Require explicit contract marker: CONTRACT_VERSION or "bridge contract v1" (case-insensitive)
        lower = main_content.lower()
        has_version = "CONTRACT_VERSION" in main_content or "bridge contract v1" in lower
        assert has_version, "Firmware must document bridge contract version (e.g. CONTRACT_VERSION 1 or comment 'bridge contract v1')"


class TestFirmwareConfigContract:
    """Firmware config must define bridge connection and pins."""

    @pytest.fixture
    def config_content(self):
        return read_config()

    def test_config_defines_bridge_host_port(self, config_content):
        """config.h defines BRIDGE_HOST and BRIDGE_PORT."""
        assert "BRIDGE_HOST" in config_content
        assert "BRIDGE_PORT" in config_content

    def test_config_defines_wifi(self, config_content):
        """config.h defines WIFI_SSID and WIFI_PASSWORD."""
        assert "WIFI_SSID" in config_content
        assert "WIFI_PASSWORD" in config_content

    def test_config_defines_mic_pins(self, config_content):
        """config.h defines I2S mic pins (BCLK, LRCLK, DIN)."""
        assert "I2S_MIC_BCLK" in config_content
        assert "I2S_MIC_LRCLK" in config_content
        assert "I2S_MIC_DIN" in config_content

    def test_config_defines_dac_pin(self, config_content):
        """config.h defines AMP_DAC_PIN for speaker (GPIO 25)."""
        assert "AMP_DAC_PIN" in config_content
