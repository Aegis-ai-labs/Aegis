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

        # Method 1: Piper Python API
        if self._voice:
            return self._synthesize_python(text, start)

        # Method 2: Piper CLI
        return self._synthesize_cli(text, start)

    def _synthesize_python(self, text: str, start: float) -> Optional[bytes]:
        """Synthesize using Piper Python API."""
        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                self._voice.synthesize(text, wav_file)
            wav_buffer.seek(0)

            # Extract raw PCM from WAV
            with wave.open(wav_buffer, "rb") as wav_file:
                pcm_data = wav_file.readframes(wav_file.getnframes())

            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("TTS [%.0fms, python]: %d bytes for '%s'", elapsed_ms, len(pcm_data), text[:40])
            return pcm_data
        except Exception as e:
            logger.error("Piper Python TTS error: %s", e, exc_info=True)
            return None

    def _synthesize_cli(self, text: str, start: float) -> Optional[bytes]:
        """Synthesize using piper CLI (fallback)."""
        try:
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
                logger.error("Piper CLI error: %s", result.stderr.decode()[:200])
                return None

            pcm_data = result.stdout
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("TTS [%.0fms, cli]: %d bytes for '%s'", elapsed_ms, len(pcm_data), text[:40])
            return pcm_data
        except FileNotFoundError:
            logger.error("piper CLI not found. Install: pip install piper-tts")
            return None
        except Exception as e:
            logger.error("Piper CLI error: %s", e, exc_info=True)
            return None

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
