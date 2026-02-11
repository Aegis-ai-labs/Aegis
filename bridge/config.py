"""
AEGIS1 Configuration — pydantic-settings based env config.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Claude API
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    claude_opus_model: str = "claude-opus-4-6"
    claude_max_tokens: int = 300

    # Bridge server
    bridge_host: str = "0.0.0.0"
    bridge_port: int = 8000

    # Audio
    sample_rate: int = 16000
    chunk_size_ms: int = 200
    max_recording_time_ms: int = 10000
    silence_threshold: int = 500
    silence_chunks_to_stop: int = 8  # 1.6s of silence

    # STT (faster-whisper)
    stt_model: str = "base"
    stt_device: str = "cpu"
    stt_language: str = "en"
    stt_beam_size: int = 1

    # TTS (Piper)
    tts_model: str = "en_US-lessac-medium"
    tts_speaker_id: int = 0

    # Database
    db_path: str = "aegis1.db"

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
