"""Speech-to-Text — faster-whisper wrapper (adapted from reference)."""

import io
import logging
import tempfile
import time
from typing import Optional

from bridge.config import settings

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    FASTER_WHISPER_AVAILABLE = False

_model: Optional[object] = None


def _get_model():
    """Load WhisperModel once on first use."""
    global _model
    if _model is not None:
        return _model
    if not FASTER_WHISPER_AVAILABLE:
        logger.warning("faster-whisper not installed; pip install faster-whisper")
        return None
    compute_type = "int8" if settings.stt_device == "cpu" else "float16"
    try:
        _model = WhisperModel(
            settings.stt_model,
            device=settings.stt_device,
            compute_type=compute_type,
        )
        logger.info("STT model loaded: %s (device=%s)", settings.stt_model, settings.stt_device)
        return _model
    except Exception as e:
        logger.error("Failed to load STT model: %s", e, exc_info=True)
        return None


def transcribe_wav(audio_wav_bytes: bytes) -> Optional[str]:
    """Transcribe WAV audio bytes to text."""
    if not audio_wav_bytes or len(audio_wav_bytes) < 100:
        return None

    model = _get_model()
    if model is None:
        return None

    start = time.monotonic()
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_wav_bytes)
            f.flush()
            segments, info = model.transcribe(
                f.name,
                beam_size=settings.stt_beam_size,
                language=settings.stt_language or None,
                vad_filter=True,
            )
            parts = [seg.text.strip() for seg in segments if seg.text]
            text = " ".join(parts).strip()

        elapsed_ms = (time.monotonic() - start) * 1000
        if text:
            logger.info("STT [%.0fms]: %s", elapsed_ms, text[:80])
        return text or None
    except Exception as e:
        logger.error("STT error: %s", e, exc_info=True)
        return None
