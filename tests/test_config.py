"""Unit tests for configuration management (bridge/config.py)."""

import pytest
import os
from unittest.mock import patch

from bridge.config import Settings


class TestSettings:
    """Test the Settings configuration class."""

    def test_settings_default_values(self):
        """Verify default configuration values are set correctly."""
        settings = Settings()

        # Claude API defaults
        assert settings.claude_haiku_model == "claude-haiku-4-5-20251001"
        assert settings.claude_opus_model == "claude-opus-4-6"
        assert settings.claude_max_tokens == 300

        # Bridge server defaults
        assert settings.bridge_host == "0.0.0.0"
        assert settings.bridge_port == 8000

        # Audio defaults
        assert settings.sample_rate == 16000
        assert settings.channels == 1
        assert settings.chunk_size_ms == 200

        # TTS (Kokoro) defaults
        assert settings.kokoro_voice == "af_heart"
        assert settings.kokoro_speed == 1.0
        assert settings.kokoro_lang == "a"

        # STT defaults
        assert settings.stt_model == "base"
        assert settings.stt_device == "cpu"
        assert settings.stt_language == "en"
        assert settings.stt_beam_size == 1

        # Voice activity defaults
        assert settings.silence_chunks_to_stop == 8
        assert settings.max_recording_time_ms == 10000

        # Database defaults
        assert settings.db_path == "aegis1.db"

        # Logging defaults
        assert settings.log_level == "INFO"


    def test_settings_from_environment_variables(self):
        """Test that settings can be loaded from environment variables."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test-key-123",
            "BRIDGE_PORT": "9000",
            "SAMPLE_RATE": "48000",
            "LOG_LEVEL": "DEBUG"
        }):
            settings = Settings()

            assert settings.anthropic_api_key == "test-key-123"
            assert settings.bridge_port == 9000
            assert settings.sample_rate == 48000
            assert settings.log_level == "DEBUG"


    def test_settings_api_key_alias(self):
        """Test that ANTHROPIC_API_KEY environment variable works via alias."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "aliased-key"}):
            settings = Settings()
            assert settings.anthropic_api_key == "aliased-key"


    def test_settings_integer_validation(self):
        """Test that integer fields validate types correctly."""
        settings = Settings()

        # Valid integers
        assert isinstance(settings.bridge_port, int)
        assert isinstance(settings.sample_rate, int)
        assert isinstance(settings.channels, int)
        assert isinstance(settings.chunk_size_ms, int)
        assert isinstance(settings.claude_max_tokens, int)


    def test_settings_float_validation(self):
        """Test that float fields validate types correctly."""
        settings = Settings()

        assert isinstance(settings.kokoro_speed, float)
        assert settings.kokoro_speed == 1.0


    def test_settings_string_validation(self):
        """Test that string fields are properly typed."""
        settings = Settings()

        assert isinstance(settings.claude_haiku_model, str)
        assert isinstance(settings.bridge_host, str)
        assert isinstance(settings.kokoro_voice, str)
        assert isinstance(settings.stt_model, str)
        assert isinstance(settings.db_path, str)


    def test_settings_reasonable_value_ranges(self):
        """Test that default values are within reasonable ranges."""
        settings = Settings()

        # Audio settings should be reasonable
        assert 8000 <= settings.sample_rate <= 48000
        assert 1 <= settings.channels <= 2
        assert 50 <= settings.chunk_size_ms <= 1000

        # Server port should be valid
        assert 1024 <= settings.bridge_port <= 65535

        # STT beam size should be positive
        assert settings.stt_beam_size > 0

        # Recording time should be reasonable (max 10 seconds default)
        assert 1000 <= settings.max_recording_time_ms <= 60000


    def test_settings_immutability(self):
        """Test that settings values can be modified (not frozen by default)."""
        settings = Settings()

        # Pydantic Settings allows modification by default
        settings.bridge_port = 9999
        assert settings.bridge_port == 9999


    def test_settings_env_file_config(self):
        """Test that model_config is set for .env file loading."""
        settings = Settings()

        # Check model_config exists
        assert hasattr(settings, "model_config")
        assert settings.model_config["env_file"] == ".env"
        assert settings.model_config["env_file_encoding"] == "utf-8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
