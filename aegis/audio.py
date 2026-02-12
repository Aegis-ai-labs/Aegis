"""Audio processing — PCM/WAV conversion, silence detection."""

import io
import logging
import struct
import wave
from typing import Optional

from aegis.config import settings

logger = logging.getLogger(__name__)


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 0, channels: int = 0) -> bytes:
    """Convert raw 16-bit PCM to WAV bytes."""
    sr = sample_rate or settings.sample_rate
    ch = channels or settings.channels
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def wav_to_pcm(wav_data: bytes) -> Optional[bytes]:
    """Extract raw PCM from WAV bytes."""
    try:
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            return wf.readframes(wf.getnframes())
    except Exception as e:
        logger.error("WAV to PCM error: %s", e)
        return None


def detect_silence(pcm_chunk: bytes, threshold: int = 500) -> bool:
    """Check if a PCM chunk is mostly silent (amplitude-based)."""
    if len(pcm_chunk) < 4:
        return True

    samples = struct.unpack(f"<{len(pcm_chunk) // 2}h", pcm_chunk)
    avg_amplitude = sum(abs(s) for s in samples) / len(samples)
    return avg_amplitude < threshold


def calculate_rms(pcm_chunk: bytes) -> float:
    """Calculate RMS amplitude of PCM chunk."""
    if len(pcm_chunk) < 4:
        return 0.0
    samples = struct.unpack(f"<{len(pcm_chunk) // 2}h", pcm_chunk)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return rms
