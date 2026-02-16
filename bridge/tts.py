"""Text-to-Speech — Piper TTS wrapper with streaming support."""

import io
import logging
import subprocess
import time
import wave
from typing import Optional

from bridge.config import settings

logger = logging.getLogger(__name__)

# Try piper-tts Python package first
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PiperVoice = None
    PIPER_AVAILABLE = False

# Try scipy for audio resampling (if Piper outputs non-16kHz)
try:
    from scipy import signal
    import numpy as np
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    signal = None
    np = None


class TTSEngine:
    """Piper TTS engine with fallback to CLI."""

    def __init__(self):
        self._voice = None
        if PIPER_AVAILABLE and settings.piper_model_path:
            try:
                self._voice = PiperVoice.load(
                    settings.piper_model_path,
                    config_path=settings.piper_config_path or None,
                )
                logger.info("Piper TTS loaded: %s", settings.piper_model_path)
            except Exception as e:
                logger.warning("Failed to load Piper model: %s", e)

    def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize text to 16-bit PCM audio bytes."""
        if not text.strip():
            return None

        start = time.monotonic()

        # Method 1: Piper Python API (preferred)
        if self._voice:
            result = self._synthesize_python(text, start)
            if result:
                return result
            # Fall through to CLI if Python API fails

        # Method 2: Piper CLI (fallback)
        result = self._synthesize_cli(text, start)
        if result:
            return result
        
        # Both methods failed
        logger.error("TTS synthesis failed: both Python API and CLI methods failed")
        logger.error("Check PIPER_MODEL_PATH configuration and ensure piper-tts is installed")
        return None

    def _synthesize_python(self, text: str, start: float) -> Optional[bytes]:
        """Synthesize using Piper Python API."""
        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                self._voice.synthesize(text, wav_file)
            wav_buffer.seek(0)

            # Extract raw PCM from WAV and verify/resample to 16kHz
            with wave.open(wav_buffer, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                pcm_data = wav_file.readframes(wav_file.getnframes())

                # Resample to 16kHz if needed (Piper models may output 22.05kHz or 48kHz)
                if sample_rate != settings.sample_rate:
                    logger.info("TTS resampling: %d Hz → %d Hz", sample_rate, settings.sample_rate)
                    pcm_data = self._resample_pcm(pcm_data, sample_rate, settings.sample_rate, channels)
                elif channels != settings.channels:
                    logger.warning("TTS channel mismatch: %d → %d (expected mono)", channels, settings.channels)
                    # If stereo, convert to mono (take left channel)
                    if channels == 2:
                        pcm_data = self._stereo_to_mono(pcm_data)

            # Normalize and compress audio for poor quality speakers (reduces harsh peaks)
            from bridge.audio import normalize_and_compress_pcm
            pcm_data = normalize_and_compress_pcm(pcm_data, target_rms=3000.0, compression_ratio=0.7)
            
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("TTS [%.0fms, python]: %d bytes for '%s'", elapsed_ms, len(pcm_data), text[:40])
            return pcm_data
        except Exception as e:
            logger.error("Piper Python TTS error: %s", e, exc_info=True)
            return None

    def _synthesize_cli(self, text: str, start: float) -> Optional[bytes]:
        """Synthesize using piper CLI (fallback)."""
        try:
            # Note: CLI outputs raw PCM without WAV headers, so we can't detect sample rate
            # Most Piper models output at 22.05kHz or 16kHz. We'll assume 22.05kHz if resampling is needed.
            # To be safe, use --output-raw with explicit sample rate if your Piper CLI supports it.
            cmd = ["piper", "--output-raw"]
            if settings.piper_model_path:
                cmd.extend(["--model", settings.piper_model_path])

            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                stderr_msg = result.stderr.decode("utf-8", errors="replace")[:500]
                logger.error("Piper CLI error (exit code %d): %s", result.returncode, stderr_msg)
                # If CLI fails due to import error, suggest Python API instead
                if "ImportError" in stderr_msg or "ModuleNotFoundError" in stderr_msg:
                    logger.error("Piper CLI has import errors. Try: pip install --upgrade piper-tts")
                    logger.error("Or ensure PIPER_MODEL_PATH is set and use Python API instead")
                return None

            pcm_data = result.stdout
            
            if not pcm_data:
                logger.warning("Piper CLI returned empty output")
                return None
            
            # CLI output is raw PCM - we can't detect sample rate from headers
            # Most Piper models output at 22.05kHz. If you know your model's rate, add resampling here.
            # For now, we'll log a warning and assume it's correct (user should verify)
            logger.debug("TTS CLI: %d bytes PCM (sample rate unknown, assuming %d Hz)", len(pcm_data), settings.sample_rate)
            
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("TTS [%.0fms, cli]: %d bytes for '%s'", elapsed_ms, len(pcm_data), text[:40])
            return pcm_data
        except FileNotFoundError:
            logger.error("piper CLI not found. Install: pip install piper-tts")
            logger.error("Or set PIPER_MODEL_PATH to use Python API instead")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Piper CLI timed out after 10 seconds")
            return None
        except Exception as e:
            logger.error("Piper CLI error: %s", e, exc_info=True)
            return None

    def _resample_pcm(self, pcm_data: bytes, from_rate: int, to_rate: int, channels: int = 1) -> bytes:
        """Resample PCM audio from one sample rate to another."""
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available; cannot resample. Install: pip install scipy")
            return pcm_data

        if from_rate == to_rate:
            return pcm_data

        # Convert bytes to numpy array (16-bit signed integers)
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        if channels == 2:
            # Reshape stereo: [L, R, L, R, ...] -> [[L, R], [L, R], ...]
            samples = samples.reshape(-1, 2)

        # Resample
        num_samples = int(len(samples) * to_rate / from_rate)
        resampled = signal.resample(samples, num_samples)

        # Convert back to 16-bit PCM bytes
        if channels == 2:
            resampled = resampled.flatten()
        return resampled.astype(np.int16).tobytes()

    def _stereo_to_mono(self, pcm_data: bytes) -> bytes:
        """Convert stereo PCM to mono (take left channel)."""
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available; cannot convert stereo to mono")
            return pcm_data

        samples = np.frombuffer(pcm_data, dtype=np.int16)
        # Reshape to [L, R, L, R, ...] and take left channel
        stereo = samples.reshape(-1, 2)
        mono = stereo[:, 0]  # Left channel only
        return mono.astype(np.int16).tobytes()

    def synthesize_sentences(self, text: str) -> list[bytes]:
        """Synthesize each sentence separately for streaming."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        results = []
        for sentence in sentences:
            if sentence.strip():
                pcm = self.synthesize(sentence.strip())
                if pcm:
                    results.append(pcm)
        return results
