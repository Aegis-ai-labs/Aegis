"""Audio processing — PCM/WAV conversion, silence detection."""

import io
import logging
import struct
import wave
from typing import Optional

from bridge.config import settings

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


def amplify_pcm(pcm_data: bytes, gain: float = 2.0) -> bytes:
    """Amplify PCM audio by applying gain factor."""
    if len(pcm_data) < 4:
        return pcm_data
    
    samples = list(struct.unpack(f"<{len(pcm_data) // 2}h", pcm_data))
    amplified = [int(s * gain) for s in samples]
    # Clip to prevent overflow
    amplified = [max(-32768, min(32767, s)) for s in amplified]
    return struct.pack(f"<{len(amplified)}h", *amplified)


def calculate_rms(pcm_chunk: bytes) -> float:
    """Calculate RMS amplitude of PCM chunk."""
    if len(pcm_chunk) < 4:
        return 0.0
    samples = struct.unpack(f"<{len(pcm_chunk) // 2}h", pcm_chunk)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return rms


def normalize_and_compress_pcm(pcm_data: bytes, target_rms: float = 3000.0, compression_ratio: float = 0.7) -> bytes:
    """Normalize and compress PCM audio to reduce harsh peaks for poor quality speakers.
    
    Args:
        pcm_data: Raw 16-bit PCM audio
        target_rms: Target RMS level (default 3000 = moderate volume)
        compression_ratio: Compression ratio (0.7 = gentle compression, lower = more aggressive)
    
    Returns:
        Normalized and compressed PCM audio
    """
    if len(pcm_data) < 4:
        return pcm_data
    
    samples = list(struct.unpack(f"<{len(pcm_data) // 2}h", pcm_data))
    
    # Calculate current RMS
    current_rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    if current_rms < 100:  # Too quiet, skip normalization
        return pcm_data
    
    # Normalize to target RMS
    if current_rms > 0:
        normalize_factor = target_rms / current_rms
    else:
        normalize_factor = 1.0
    
    # Apply normalization and compression
    processed = []
    for s in samples:
        # Normalize
        normalized = s * normalize_factor
        
        # Soft compression: reduce peaks more aggressively
        abs_val = abs(normalized)
        if abs_val > 8000:  # Compress peaks above 8000
            # Compression: reduce peaks gradually
            excess = abs_val - 8000
            compressed_excess = excess * compression_ratio
            compressed_val = 8000 + compressed_excess
            if normalized < 0:
                compressed_val = -compressed_val
            normalized = compressed_val
        
        # Clip to prevent overflow
        normalized = max(-32768, min(32767, int(normalized)))
        processed.append(normalized)
    
    return struct.pack(f"<{len(processed)}h", *processed)
