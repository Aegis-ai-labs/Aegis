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

    # STT — Moonshine Streaming Tiny primary, faster-whisper fallback
    stt_engine: str = "moonshine"  # "moonshine" | "faster-whisper"
    stt_model: str = "moonshine/tiny"  # moonshine: tiny|base; faster-whisper: tiny|base|small
    stt_language: str = "en"

    # TTS — Kokoro primary, Piper fallback
    tts_engine: str = "kokoro"  # "kokoro" | "piper"
    tts_kokoro_voice: str = "af_heart"  # Kokoro voice name
    tts_piper_model: str = "en_US-lessac-medium"  # Piper fallback model

    # VAD — Silero
    vad_threshold: float = 0.5  # Speech probability threshold
    vad_min_speech_ms: int = 250  # Min speech duration to trigger STT
    vad_silence_ms: int = 700  # Silence after speech to end utterance

    # Local LLM — Phi-3-mini via Ollama
    local_llm_enabled: bool = True
    local_llm_model: str = "phi3:mini"
    local_llm_url: str = "http://localhost:11434"  # Ollama API

    # Intent router
    router_complexity_threshold: float = 0.5  # Below = local LLM, above = Claude

    # Memory — sqlite-vec
    memory_enabled: bool = True
    memory_db_path: str = "aegis1_memory.db"
    memory_max_results: int = 5

    # Database
    db_path: str = "aegis1.db"

    # ADPCM audio compression
    use_adpcm: bool = True  # 4x compression for ESP32 transport

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
