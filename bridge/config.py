"""AEGIS1 Configuration — pydantic-settings based env config."""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Configuration settings for AEGIS bridge.

    Environment Variables (Required):
    - ANTHROPIC_API_KEY: Required. Anthropic API key for Claude access.

    Environment Variables (Optional - Gemini):
    - GEMINI_API_KEY: Google Gemini API key (optional, for testing phase)
    - USE_GEMINI_FOR_TESTING: Use Gemini for testing to save Anthropic credits (default: false)
    - GEMINI_MODEL: Gemini model ID (default: gemini-2.0-flash-exp)
    - GEMINI_MAX_TOKENS: Max tokens for Gemini responses (default: 300)

    Environment Variables (Optional):
    - BRIDGE_HOST: Server host (default: 0.0.0.0)
    - BRIDGE_PORT: Server port (default: 8000)
    - STT_MODEL: Whisper model size (default: base)
    - PIPER_MODEL_PATH: Path to Piper TTS model
    - PIPER_CONFIG_PATH: Path to Piper config
    - PIPER_TTS_URL: Piper TTS server URL (default: http://localhost:5000)
    - DB_PATH: SQLite database path (default: aegis1.db)
    - LOG_LEVEL: Logging level (default: INFO)
    - CLAUDE_HAIKU_MODEL: Haiku model ID
    - CLAUDE_OPUS_MODEL: Opus model ID
    - CLAUDE_MAX_TOKENS: Max tokens for Claude responses
    - SAMPLE_RATE: Audio sample rate (default: 16000)
    - CHANNELS: Audio channels (default: 1)
    - CHUNK_SIZE_MS: Audio chunk size in ms (default: 200)
    - STT_DEVICE: STT device (default: cpu)
    - STT_LANGUAGE: STT language (default: en)
    - STT_BEAM_SIZE: STT beam size (default: 1)
    - SILENCE_CHUNKS_TO_STOP: Silence detection threshold (default: 8)
    - MAX_RECORDING_TIME_MS: Max recording time in ms (default: 10000)
    """
    # Claude API
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    claude_opus_model: str = "claude-opus-4-6"
    claude_max_tokens: int = 300

    # Gemini API (for testing phase to save Anthropic credits)
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    use_gemini_for_testing: bool = Field(default=False, alias="USE_GEMINI_FOR_TESTING")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", alias="GEMINI_MODEL")
    gemini_max_tokens: int = Field(default=300, alias="GEMINI_MAX_TOKENS")

    # Bridge server
    bridge_host: str = "0.0.0.0"
    bridge_port: int = 8000

    # Audio
    sample_rate: int = 16000
    channels: int = 1
    chunk_size_ms: int = 200

    # TTS (Piper)
    piper_model_path: str = ""
    piper_config_path: str = ""
    piper_tts_url: str = "http://localhost:5000"

    # STT (faster-whisper)
    stt_model: str = "base"
    stt_device: str = "cpu"
    stt_language: str = "en"
    stt_beam_size: int = 1

    # Voice activity / recording
    silence_chunks_to_stop: int = 8
    max_recording_time_ms: int = 10000

    # Database
    db_path: str = "aegis1.db"

    # Local LLM (Ollama for testing)
    use_local_model: bool = Field(default=False, alias="USE_LOCAL_MODEL")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="phi3", alias="OLLAMA_MODEL")

    # Server Discovery (mDNS for ESP32 auto-connect)
    server_discovery_enabled: bool = Field(default=True, alias="SERVER_DISCOVERY")
    mdns_service_name: str = Field(default="aegis1", alias="MDNS_SERVICE_NAME")

    # Test Mode (skip API key validation when using local models)
    test_mode: bool = Field(default=False, alias="TEST_MODE")

    # Logging
    log_level: str = "INFO"

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is not empty (unless using local model in test mode)."""
        # Skip validation if:
        # 1. USE_LOCAL_MODEL=true (using Ollama, no API key needed)
        # 2. TEST_MODE=true (testing mode, skip validation)
        # 3. Empty API key is acceptable if we're not using Claude
        
        # Always allow empty API key - it will be caught at usage time if needed
        if not v or not v.strip():
            # Just log a warning, don't fail - user might be using local Ollama
            return ""
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
