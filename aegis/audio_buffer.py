"""Audio buffering — accumulate PCM chunks until speech ends."""

import logging
from collections import deque
from typing import Optional

from aegis.audio import detect_silence
from aegis.config import settings

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Accumulate PCM audio chunks until silence is detected."""

    def __init__(
        self,
        sample_rate: int = 0,
        silence_duration_ms: float = 600,
        chunk_size_bytes: int = 320,
    ):
        """
        Initialize audio buffer.

        Args:
            sample_rate: Sample rate in Hz (0 = use config)
            silence_duration_ms: Duration of silence to trigger completion
            chunk_size_bytes: Size of each chunk (320 = 10ms @ 16kHz 16-bit mono)
        """
        self.sample_rate = sample_rate or settings.sample_rate
        self.silence_duration_ms = silence_duration_ms
        self.chunk_size_bytes = chunk_size_bytes
        self.bytes_per_ms = (self.sample_rate * 2) / 1000  # 16-bit = 2 bytes/sample

        # Calculate how many chunks of silence to trigger completion
        self.silence_threshold_chunks = int(
            (silence_duration_ms * self.bytes_per_ms) / chunk_size_bytes
        )

        self.buffer = deque()  # Chunks (bytes)
        self.silence_count = 0
        self.total_bytes = 0

    def add_chunk(self, pcm_bytes: bytes) -> tuple[bool, Optional[bytes]]:
        """
        Add a PCM chunk to buffer.

        Returns:
            (is_complete, pcm_audio)
            - is_complete: True if speech has ended (silence detected)
            - pcm_audio: Complete audio bytes (only if is_complete=True)
        """
        if not pcm_bytes:
            return (False, None)

        self.buffer.append(pcm_bytes)
        self.total_bytes += len(pcm_bytes)

        # Check for silence in this chunk
        is_silent = detect_silence(pcm_bytes, threshold=settings.silence_threshold)

        if is_silent:
            self.silence_count += 1
            logger.debug(
                f"Silence chunk {self.silence_count}/{self.silence_threshold_chunks}"
            )
        else:
            self.silence_count = 0
            logger.debug(f"Speech detected, silence counter reset")

        # If silence threshold reached, utterance is complete
        if self.silence_count >= self.silence_threshold_chunks:
            audio_pcm = b"".join(self.buffer)
            self._reset()

            elapsed_s = len(audio_pcm) / (self.sample_rate * 2)
            logger.info(
                f"Utterance complete: {len(audio_pcm)} bytes, {elapsed_s:.1f}s"
            )
            return (True, audio_pcm)

        return (False, None)

    def _reset(self):
        """Reset buffer for next utterance."""
        self.buffer.clear()
        self.silence_count = 0
        self.total_bytes = 0

    def get_partial_audio(self) -> Optional[bytes]:
        """Get accumulated audio so far (without clearing buffer)."""
        if not self.buffer:
            return None
        return b"".join(self.buffer)

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.buffer) == 0

    def get_accumulated_ms(self) -> float:
        """Get duration of accumulated audio in milliseconds."""
        return (self.total_bytes / self.bytes_per_ms)
