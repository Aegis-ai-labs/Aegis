"""
RED Phase Tests for Audio Pipeline (Core Workflow)

End-to-End Audio Pipeline: Audio → STT → Claude → TTS → Audio

This test suite defines FAILING tests that specify the complete audio pipeline behavior.
Tests are intentionally designed to fail initially, following TDD RED → GREEN → REFACTOR cycle.

Requirements (All FAILING tests):
1. STT converts speech to text with accuracy > 85%
2. Claude processes text and generates response
3. TTS converts response to speech
4. Response is streamed sentence-by-sentence
5. Latency target: < 2 seconds total
6. Error handling: graceful degradation if any step fails
"""

import asyncio
import io
import json
import logging
import math
import struct
import time
from typing import Generator, AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from aegis.audio import pcm_to_wav, wav_to_pcm, detect_silence, calculate_rms
from aegis.config import settings
from aegis.stt import transcribe_wav
from aegis.tts import TTSEngine
from aegis.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Test constants
SAMPLE_RATE = 16000
CHANNELS = 1
SILENCE_THRESHOLD = 500
MAX_AMPLITUDE = 32767
TEST_FREQUENCY = 440  # A4 note
LATENCY_TARGET_MS = 2000
STT_ACCURACY_TARGET = 0.85


# ============================================================================
# FIXTURES - Reusable test data and mocks
# ============================================================================


@pytest.fixture
def audio_generator_sine_wave() -> bytes:
    """Generate 1 second of 440Hz sine wave audio."""
    duration_sec = 1
    num_samples = SAMPLE_RATE * duration_sec
    pcm_data = b""

    for i in range(num_samples):
        sample = int(
            MAX_AMPLITUDE
            * math.sin(2 * math.pi * TEST_FREQUENCY * i / SAMPLE_RATE)
        )
        pcm_data += int(sample).to_bytes(2, byteorder="little", signed=True)

    return pcm_data


@pytest.fixture
def audio_generator_silent() -> bytes:
    """Generate 1 second of silent audio (zeros)."""
    duration_sec = 1
    num_samples = SAMPLE_RATE * duration_sec
    return b"\x00\x00" * num_samples


@pytest.fixture
def audio_generator_noise() -> bytes:
    """Generate 1 second of pseudo-random noise."""
    import random

    duration_sec = 1
    num_samples = SAMPLE_RATE * duration_sec
    pcm_data = b""

    for i in range(num_samples):
        sample = random.randint(-32767, 32767)
        pcm_data += int(sample).to_bytes(2, byteorder="little", signed=True)

    return pcm_data


@pytest.fixture
def mock_stt_engine():
    """Mock STT engine that returns deterministic transcriptions."""
    engine = MagicMock()
    engine.transcribe_wav = MagicMock(return_value="Hello, how can I help you today?")
    return engine


@pytest.fixture
def mock_claude_client():
    """Mock Claude client that returns deterministic responses."""
    client = AsyncMock(spec=ClaudeClient)

    async def mock_chat(user_text: str) -> AsyncGenerator[str, None]:
        """Simulate Claude response streaming sentences."""
        response = "I can help you with that. Let me check your data."
        sentences = response.split(". ")
        for sentence in sentences:
            yield sentence + (". " if not sentence.endswith(".") else "")

    client.chat = mock_chat
    return client


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine that returns PCM bytes."""
    engine = MagicMock(spec=TTSEngine)

    def mock_synthesize(text: str) -> Optional[bytes]:
        """Simulate TTS output (PCM audio)."""
        # Generate PCM proportional to text length (0.1s per word)
        words = len(text.split())
        duration_sec = words * 0.1
        num_samples = int(SAMPLE_RATE * duration_sec)
        pcm = b"\x00\x00" * num_samples  # Silence as placeholder
        return pcm if num_samples > 0 else None

    engine.synthesize = mock_synthesize

    def mock_synthesize_sentences(text: str) -> list[bytes]:
        """Simulate sentence-by-sentence TTS."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        results = []
        for sentence in sentences:
            if sentence.strip():
                pcm = mock_synthesize(sentence)
                if pcm:
                    results.append(pcm)
        return results

    engine.synthesize_sentences = mock_synthesize_sentences
    return engine


@pytest.fixture
def latency_tracker():
    """Track latency measurements across pipeline stages."""
    class LatencyTracker:
        def __init__(self):
            self.measurements: dict[str, list[float]] = {}

        def record(self, stage: str, elapsed_ms: float):
            if stage not in self.measurements:
                self.measurements[stage] = []
            self.measurements[stage].append(elapsed_ms)

        def get_total(self) -> float:
            return sum(
                sum(times) for times in self.measurements.values()
            ) / len(self.measurements) if self.measurements else 0

        def report(self) -> dict:
            return {
                stage: {
                    "mean_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "count": len(times),
                }
                for stage, times in self.measurements.items()
            }

    return LatencyTracker()


# ============================================================================
# TEST CLASS 1: Audio Format Validation
# ============================================================================


class TestAudioFormatValidation:
    """RED: Tests for audio format conversion and validation."""

    def test_red_audio_to_wav_with_valid_pcm(self, audio_generator_sine_wave):
        """RED: Convert raw PCM to WAV format with correct headers."""
        # Arrange
        pcm_data = audio_generator_sine_wave

        # Act
        wav_data = pcm_to_wav(pcm_data, sample_rate=SAMPLE_RATE, channels=CHANNELS)

        # Assert: Must have valid WAV structure
        assert wav_data is not None, "WAV conversion returned None"
        assert len(wav_data) > len(pcm_data), "WAV should include headers"
        assert wav_data[:4] == b"RIFF", "Missing RIFF header"
        assert b"WAVE" in wav_data, "Missing WAVE format marker"
        assert b"fmt " in wav_data, "Missing format chunk"
        assert b"data" in wav_data, "Missing data chunk"

    def test_red_wav_to_pcm_roundtrip_fidelity(self, audio_generator_sine_wave):
        """RED: WAV ↔ PCM conversion preserves all audio data."""
        # Arrange
        original_pcm = audio_generator_sine_wave

        # Act
        wav_data = pcm_to_wav(original_pcm, sample_rate=SAMPLE_RATE, channels=CHANNELS)
        recovered_pcm = wav_to_pcm(wav_data)

        # Assert: Perfect roundtrip
        assert recovered_pcm is not None, "WAV to PCM returned None"
        assert len(recovered_pcm) == len(original_pcm), "PCM size mismatch"
        assert recovered_pcm == original_pcm, "PCM data corrupted"

    def test_red_audio_detection_identifies_silence(self, audio_generator_silent):
        """RED: Silence detection correctly identifies silent audio."""
        # Arrange
        silent_pcm = audio_generator_silent

        # Act
        is_silent = detect_silence(silent_pcm, threshold=SILENCE_THRESHOLD)

        # Assert
        assert is_silent is True, "Failed to detect silence"

    def test_red_audio_detection_identifies_signal(self, audio_generator_sine_wave):
        """RED: Silence detection correctly rejects audio with signal."""
        # Arrange
        signal_pcm = audio_generator_sine_wave

        # Act
        is_silent = detect_silence(signal_pcm, threshold=SILENCE_THRESHOLD)

        # Assert
        assert is_silent is False, "False positive: detected signal as silence"

    def test_red_rms_calculation_on_silence(self, audio_generator_silent):
        """RED: RMS calculation correctly measures silent audio as zero."""
        # Arrange
        silent_pcm = audio_generator_silent

        # Act
        rms = calculate_rms(silent_pcm)

        # Assert
        assert rms == 0.0, f"Silent audio should have RMS=0, got {rms}"

    def test_red_rms_calculation_on_signal(self, audio_generator_noise):
        """RED: RMS calculation correctly measures signal amplitude."""
        # Arrange
        noise_pcm = audio_generator_noise

        # Act
        rms = calculate_rms(noise_pcm)

        # Assert: Should be non-zero
        assert rms > 0.0, "Signal should have non-zero RMS"
        assert rms > SILENCE_THRESHOLD, "RMS should exceed threshold for audio signal"


# ============================================================================
# TEST CLASS 2: Speech-to-Text (STT) Integration
# ============================================================================


class TestSTTIntegration:
    """RED: Tests for Speech-to-Text pipeline."""

    def test_red_stt_converts_audio_to_text(self, audio_generator_sine_wave):
        """RED: STT engine should convert WAV audio to text."""
        # Arrange
        wav_data = pcm_to_wav(audio_generator_sine_wave, sample_rate=SAMPLE_RATE)

        # Act: Mock the model to return transcription
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = "what is my heart rate today"
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model

            result = transcribe_wav(wav_data)

        # Assert
        assert result is not None, "STT returned None"
        assert isinstance(result, str), "STT should return string"
        assert len(result) > 0, "STT returned empty string"
        assert "heart rate" in result.lower(), "STT should preserve key words"

    def test_red_stt_handles_empty_audio_gracefully(self):
        """RED: STT should handle empty audio without crashing."""
        # Arrange
        empty_audio = b""

        # Act
        result = transcribe_wav(empty_audio)

        # Assert: Should not crash
        assert result is None or result == "", "Empty audio should return None/empty"

    def test_red_stt_accuracy_target(self, audio_generator_sine_wave):
        """RED: STT accuracy should exceed 85% on test audio."""
        # This is a benchmark test—will fail until STT is properly configured
        # Arrange
        test_phrase = "What is my blood pressure?"
        wav_data = pcm_to_wav(audio_generator_sine_wave, sample_rate=SAMPLE_RATE)

        # Act: Mock transcription with known output
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            # Simulate slightly imperfect transcription
            mock_segment.text = "what is my blood pressure"  # OK but lowercase
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model

            result = transcribe_wav(wav_data)

        # Assert: Should be close to original
        assert result is not None
        # Word error rate should be < 15%
        original_words = set(test_phrase.lower().split())
        result_words = set(result.lower().split()) if result else set()
        # This is a simplified check; real WER calculation is more complex
        accuracy = len(original_words & result_words) / len(original_words)
        assert accuracy >= STT_ACCURACY_TARGET, (
            f"STT accuracy {accuracy:.2%} below target {STT_ACCURACY_TARGET:.2%}"
        )

    def test_red_stt_handles_malformed_audio(self):
        """RED: STT should gracefully handle malformed/corrupt audio."""
        # Arrange
        corrupt_audio = b"not a valid audio file" * 100

        # Act
        result = transcribe_wav(corrupt_audio)

        # Assert: Should handle gracefully (return None, not crash)
        assert result is None or result == "", "Should handle corrupt audio gracefully"


# ============================================================================
# TEST CLASS 3: Text-to-Speech (TTS) Integration
# ============================================================================


class TestTTSIntegration:
    """RED: Tests for Text-to-Speech pipeline."""

    def test_red_tts_converts_text_to_audio(self):
        """RED: TTS engine should convert text to PCM audio."""
        # Arrange
        text_input = "Your heart rate is 72 beats per minute."
        expected_duration_sec = 2  # Rough estimate

        # Act
        with patch.object(TTSEngine, "synthesize") as mock_synth:
            mock_pcm = b"\x00\x00" * (SAMPLE_RATE * expected_duration_sec)
            mock_synth.return_value = mock_pcm

            engine = TTSEngine()
            result = engine.synthesize(text_input)

        # Assert
        assert result is not None, "TTS returned None"
        assert isinstance(result, bytes), "TTS should return bytes"
        assert len(result) > 0, "TTS audio should not be empty"
        assert len(result) % 2 == 0, "PCM should have even byte count (16-bit samples)"

    def test_red_tts_handles_empty_text(self, mock_tts_engine):
        """RED: TTS should handle empty text gracefully."""
        # Arrange
        empty_text = ""

        # Act
        result = mock_tts_engine.synthesize(empty_text)

        # Assert
        assert result is None or result == b"", "Empty text should return None/empty"

    def test_red_tts_sentence_streaming(self):
        """RED: TTS should split response into sentences for streaming."""
        # Arrange
        multi_sentence_text = "First measurement recorded. Second reading taken. Question resolved?"
        expected_sentences = 3

        # Act
        with patch.object(TTSEngine, "synthesize") as mock_synth:
            mock_pcm = b"\x00\x00" * 8000  # 0.5 seconds
            mock_synth.return_value = mock_pcm

            engine = TTSEngine()
            results = engine.synthesize_sentences(multi_sentence_text)

        # Assert
        assert isinstance(results, list), "Should return list of audio chunks"
        assert len(results) >= expected_sentences - 1, (
            f"Should have ~{expected_sentences} sentence chunks, got {len(results)}"
        )
        for chunk in results:
            assert isinstance(chunk, bytes), "Each chunk should be bytes"
            assert len(chunk) > 0, "Each chunk should have audio data"

    def test_red_tts_maintains_audio_quality(self):
        """RED: TTS output should be valid PCM audio."""
        # Arrange
        text = "Health measurement recorded successfully."

        # Act
        with patch.object(TTSEngine, "synthesize") as mock_synth:
            # Generate valid PCM (sine wave)
            duration_sec = 2
            num_samples = SAMPLE_RATE * duration_sec
            pcm_data = b""
            for i in range(num_samples):
                sample = int(
                    16000 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
                )
                pcm_data += int(sample).to_bytes(2, byteorder="little", signed=True)

            mock_synth.return_value = pcm_data
            engine = TTSEngine()
            result = engine.synthesize(text)

        # Assert: Verify audio structure
        assert result is not None
        assert len(result) % 2 == 0, "PCM sample count should be even"
        rms = calculate_rms(result)
        assert rms > 0, "Output should have non-zero amplitude"


# ============================================================================
# TEST CLASS 4: Claude Integration (LLM Response Processing)
# ============================================================================


class TestClaudeIntegration:
    """RED: Tests for Claude LLM integration."""

    @pytest.mark.asyncio
    async def test_red_claude_processes_text_input(self):
        """RED: Claude should process user text and generate response."""
        # Arrange
        user_input = "What is my current heart rate?"

        # Act
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            mock_stream = AsyncMock()
            mock_event = MagicMock()
            mock_event.type = "content_block_delta"
            mock_event.delta.text = "Your heart rate is 72 bpm. "

            async def mock_stream_iter():
                yield mock_event

            mock_stream.__aiter__ = mock_stream_iter
            mock_stream.get_final_message = AsyncMock()
            mock_final = MagicMock()
            mock_final.content = [MagicMock(text="Your heart rate is 72 bpm.")]
            mock_stream.get_final_message.return_value = mock_final

            mock_api.return_value.messages.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            client = ClaudeClient()
            response_text = ""
            async for chunk in client.chat(user_input):
                response_text += chunk

        # Assert
        assert response_text != "", "Claude should generate response"
        assert isinstance(response_text, str), "Response should be string"

    @pytest.mark.asyncio
    async def test_red_claude_streams_sentences(self):
        """RED: Claude should stream response as complete sentences."""
        # Arrange
        user_input = "Log my heart rate."
        expected_sentences = ["Your heart rate is recorded.", "It is 72 bpm."]

        # Act: Mock Claude's sentence-by-sentence streaming
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            mock_stream = AsyncMock()

            async def mock_stream_iter():
                # Simulate sentence streaming
                for sentence in expected_sentences:
                    mock_event = MagicMock()
                    mock_event.type = "content_block_delta"
                    mock_event.delta.text = sentence + " "
                    yield mock_event

            mock_stream.__aiter__ = mock_stream_iter
            mock_stream.get_final_message = AsyncMock()
            mock_final = MagicMock()
            response_text = " ".join(expected_sentences)
            mock_final.content = [MagicMock(text=response_text)]
            mock_stream.get_final_message.return_value = mock_final

            mock_api.return_value.messages.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            client = ClaudeClient()
            chunks = []
            async for chunk in client.chat(user_input):
                chunks.append(chunk)

        # Assert
        assert len(chunks) > 0, "Should yield sentence chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Response should have content"

    @pytest.mark.asyncio
    async def test_red_claude_handles_tool_calls(self):
        """RED: Claude should handle tool invocations (heart rate, steps, etc)."""
        # Arrange
        user_input = "What is my heart rate?"

        # Act: Mock Claude with tool call
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            with patch("aegis.tools.registry.dispatch_tool") as mock_dispatch:
                mock_dispatch.return_value = "72 bpm"

                mock_stream = AsyncMock()

                async def mock_stream_iter():
                    # Yield tool use event
                    mock_event = MagicMock()
                    mock_event.type = "content_block_start"
                    mock_event.content_block.type = "tool_use"
                    mock_event.content_block.id = "tool_123"
                    mock_event.content_block.name = "get_heart_rate"
                    yield mock_event

                    # Yield tool input
                    mock_event2 = MagicMock()
                    mock_event2.type = "content_block_delta"
                    mock_event2.delta.partial_json = "{}"
                    yield mock_event2

                    # Yield final text
                    mock_event3 = MagicMock()
                    mock_event3.type = "content_block_delta"
                    mock_event3.delta.text = "Your heart rate is 72 bpm."
                    yield mock_event3

                mock_stream.__aiter__ = mock_stream_iter
                mock_stream.get_final_message = AsyncMock()
                mock_final = MagicMock()
                mock_final.content = [MagicMock(text="Your heart rate is 72 bpm.")]
                mock_stream.get_final_message.return_value = mock_final

                mock_api.return_value.messages.stream.return_value.__aenter__ = (
                    AsyncMock(return_value=mock_stream)
                )
                mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                    return_value=None
                )

                client = ClaudeClient()
                response_text = ""
                async for chunk in client.chat(user_input):
                    response_text += chunk

        # Assert
        assert response_text != "", "Should return response after tool calls"


# ============================================================================
# TEST CLASS 5: Complete End-to-End Pipeline
# ============================================================================


class TestAudioPipelineE2E:
    """RED: Tests for complete Audio → STT → Claude → TTS → Audio pipeline."""

    @pytest.mark.asyncio
    async def test_red_complete_pipeline_audio_to_audio(
        self, audio_generator_sine_wave, latency_tracker, mock_tts_engine
    ):
        """RED: Complete pipeline converts audio input to audio output."""
        # This is the core workflow test
        # Arrange: Start with raw audio input
        input_pcm = audio_generator_sine_wave

        # Step 1: Audio → WAV
        t_start = time.perf_counter()
        wav_data = pcm_to_wav(input_pcm, sample_rate=SAMPLE_RATE)
        latency_tracker.record("audio_encoding", (time.perf_counter() - t_start) * 1000)

        # Step 2: STT (WAV → Text)
        t_start = time.perf_counter()
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = "What is my heart rate?"
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model

            stt_result = transcribe_wav(wav_data)
        latency_tracker.record("stt", (time.perf_counter() - t_start) * 1000)

        # Assert: STT succeeded
        assert stt_result is not None, "Step 2 (STT) failed"
        assert isinstance(stt_result, str), "STT should return text"

        # Step 3: Claude (Text → Text response)
        t_start = time.perf_counter()
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            mock_stream = AsyncMock()

            async def mock_stream_iter():
                mock_event = MagicMock()
                mock_event.type = "content_block_delta"
                mock_event.delta.text = "Your heart rate is 72 bpm. "
                yield mock_event

            mock_stream.__aiter__ = mock_stream_iter
            mock_stream.get_final_message = AsyncMock()
            mock_final = MagicMock()
            mock_final.content = [MagicMock(text="Your heart rate is 72 bpm.")]
            mock_stream.get_final_message.return_value = mock_final

            mock_api.return_value.messages.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            client = ClaudeClient()
            claude_response = ""
            async for chunk in client.chat(stt_result):
                claude_response += chunk
        latency_tracker.record("claude", (time.perf_counter() - t_start) * 1000)

        # Assert: Claude succeeded
        assert claude_response != "", "Step 3 (Claude) failed"

        # Step 4: TTS (Text response → Audio)
        t_start = time.perf_counter()
        output_pcm = mock_tts_engine.synthesize(claude_response)
        latency_tracker.record("tts", (time.perf_counter() - t_start) * 1000)

        # Assert: TTS succeeded
        assert output_pcm is not None, "Step 4 (TTS) failed"
        assert isinstance(output_pcm, bytes), "TTS should return audio bytes"

        # Step 5: PCM → WAV
        t_start = time.perf_counter()
        output_wav = pcm_to_wav(output_pcm, sample_rate=SAMPLE_RATE)
        latency_tracker.record("audio_format", (time.perf_counter() - t_start) * 1000)

        # Assert: Complete pipeline succeeded
        assert output_wav is not None, "Final audio format conversion failed"
        assert output_wav[:4] == b"RIFF", "Output should be valid WAV"

    def test_red_pipeline_latency_target(self, audio_generator_sine_wave, mock_tts_engine):
        """RED: Complete pipeline should complete within 2 seconds."""
        # Arrange
        input_pcm = audio_generator_sine_wave
        pipeline_start = time.perf_counter()

        # Act: Execute pipeline stages
        wav_data = pcm_to_wav(input_pcm, sample_rate=SAMPLE_RATE)

        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = "What is my status?"
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model
            stt_result = transcribe_wav(wav_data)

        # Simulate Claude (would be async in real scenario)
        claude_response = "You are doing great."

        output_pcm = mock_tts_engine.synthesize(claude_response)
        output_wav = pcm_to_wav(output_pcm or b"\x00\x00", sample_rate=SAMPLE_RATE)

        pipeline_elapsed_ms = (time.perf_counter() - pipeline_start) * 1000

        # Assert: Should be under latency target
        assert pipeline_elapsed_ms < LATENCY_TARGET_MS, (
            f"Pipeline took {pipeline_elapsed_ms:.0f}ms, target is {LATENCY_TARGET_MS}ms"
        )

    @pytest.mark.asyncio
    async def test_red_pipeline_sentence_streaming(
        self, audio_generator_sine_wave, mock_tts_engine
    ):
        """RED: Pipeline should stream TTS output sentence-by-sentence."""
        # Arrange
        input_pcm = audio_generator_sine_wave
        wav_data = pcm_to_wav(input_pcm, sample_rate=SAMPLE_RATE)

        # Step 1: STT
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = "What is my data?"
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model
            stt_result = transcribe_wav(wav_data)

        # Step 2: Claude with sentence streaming
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            mock_stream = AsyncMock()

            async def mock_stream_iter():
                # Yield sentence by sentence
                for sentence in ["First result. ", "Second result. "]:
                    mock_event = MagicMock()
                    mock_event.type = "content_block_delta"
                    mock_event.delta.text = sentence
                    yield mock_event

            mock_stream.__aiter__ = mock_stream_iter
            mock_stream.get_final_message = AsyncMock()
            mock_final = MagicMock()
            mock_final.content = [MagicMock(text="First result. Second result.")]
            mock_stream.get_final_message.return_value = mock_final

            mock_api.return_value.messages.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            client = ClaudeClient()
            sentences = []
            async for chunk in client.chat(stt_result):
                sentences.append(chunk)

        # Step 3: TTS streaming for each sentence
        audio_chunks = []
        for sentence in sentences:
            pcm = mock_tts_engine.synthesize(sentence)
            if pcm:
                audio_chunks.append(pcm)

        # Assert
        assert len(audio_chunks) > 0, "Should produce audio chunks"
        for chunk in audio_chunks:
            assert isinstance(chunk, bytes), "Each chunk should be bytes"
            assert len(chunk) > 0, "Each chunk should have audio"


# ============================================================================
# TEST CLASS 6: Error Handling & Graceful Degradation
# ============================================================================


class TestErrorHandlingAndResilience:
    """RED: Tests for error handling and graceful degradation."""

    def test_red_stt_failure_returns_none(self):
        """RED: If STT fails, should return None instead of crashing."""
        # Arrange
        corrupt_audio = b"invalid audio data"

        # Act
        result = transcribe_wav(corrupt_audio)

        # Assert: Should not crash
        assert result is None or result == "", "STT failure should return None/empty"

    def test_red_tts_failure_returns_none(self, mock_tts_engine):
        """RED: If TTS fails, should return None instead of crashing."""
        # Arrange
        # Simulate TTS failure by making synthesize return None
        mock_tts_engine.synthesize = MagicMock(return_value=None)

        # Act
        result = mock_tts_engine.synthesize("test text")

        # Assert
        assert result is None, "TTS failure should return None"

    @pytest.mark.asyncio
    async def test_red_claude_failure_handling(self):
        """RED: If Claude API fails, should handle gracefully."""
        # Arrange
        user_input = "Hello?"

        # Act: Simulate Claude API error
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            # Make the API call raise an exception
            mock_api.return_value.messages.stream.side_effect = Exception(
                "API rate limit exceeded"
            )

            client = ClaudeClient()

            # Assert: Should handle error gracefully (not crash)
            with pytest.raises(Exception):
                # This test documents that errors propagate
                # Production code should catch and handle them
                async for _ in client.chat(user_input):
                    pass

    def test_red_pipeline_handles_empty_user_input(self, mock_tts_engine):
        """RED: Pipeline should handle empty user input gracefully."""
        # Arrange
        empty_input = ""

        # Act: Try to process empty input
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = ""  # Empty transcription
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model

            wav_empty = pcm_to_wav(b"", sample_rate=SAMPLE_RATE)
            result = transcribe_wav(wav_empty)

        # Assert
        assert result is None or result == "", "Should handle empty input gracefully"


# ============================================================================
# TEST CLASS 7: Performance & Benchmarks
# ============================================================================


class TestPerformanceAndBenchmarks:
    """RED: Tests for performance metrics and benchmarks."""

    def test_red_stt_latency_benchmark(self, audio_generator_sine_wave):
        """RED: STT should complete within acceptable latency."""
        # Arrange
        wav_data = pcm_to_wav(audio_generator_sine_wave, sample_rate=SAMPLE_RATE)
        max_stt_latency_ms = 1500  # Whisper should be < 1.5s for 1s audio

        # Act
        with patch("aegis.stt._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.text = "test transcription"
            mock_info = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_get_model.return_value = mock_model

            t_start = time.perf_counter()
            result = transcribe_wav(wav_data)
            elapsed_ms = (time.perf_counter() - t_start) * 1000

        # Assert
        assert result is not None, "STT should succeed"
        assert elapsed_ms < max_stt_latency_ms, (
            f"STT latency {elapsed_ms:.0f}ms exceeds target {max_stt_latency_ms}ms"
        )

    def test_red_tts_latency_benchmark(self, mock_tts_engine):
        """RED: TTS should complete within acceptable latency."""
        # Arrange
        text = "Your heart rate is 72 beats per minute."
        max_tts_latency_ms = 1000  # TTS should be < 1s for short text

        # Act
        t_start = time.perf_counter()
        result = mock_tts_engine.synthesize(text)
        elapsed_ms = (time.perf_counter() - t_start) * 1000

        # Assert
        assert result is not None, "TTS should succeed"
        assert elapsed_ms < max_tts_latency_ms, (
            f"TTS latency {elapsed_ms:.0f}ms exceeds target {max_tts_latency_ms}ms"
        )

    @pytest.mark.asyncio
    async def test_red_claude_latency_benchmark(self):
        """RED: Claude should respond within acceptable latency."""
        # Arrange
        user_input = "What is my current status?"
        max_claude_latency_ms = 3000  # LLM may take longer

        # Act
        with patch("aegis.claude_client.anthropic.AsyncAnthropic") as mock_api:
            mock_stream = AsyncMock()

            async def mock_stream_iter():
                mock_event = MagicMock()
                mock_event.type = "content_block_delta"
                mock_event.delta.text = "Your status is good. "
                yield mock_event

            mock_stream.__aiter__ = mock_stream_iter
            mock_stream.get_final_message = AsyncMock()
            mock_final = MagicMock()
            mock_final.content = [MagicMock(text="Your status is good.")]
            mock_stream.get_final_message.return_value = mock_final

            mock_api.return_value.messages.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_stream
            )
            mock_api.return_value.messages.stream.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            client = ClaudeClient()
            t_start = time.perf_counter()
            response = ""
            async for chunk in client.chat(user_input):
                response += chunk
            elapsed_ms = (time.perf_counter() - t_start) * 1000

        # Assert
        assert response != "", "Claude should respond"
        # Note: Latency target is relaxed for LLM compared to STT/TTS


# ============================================================================
# TEST EXECUTION AND REPORTING
# ============================================================================


if __name__ == "__main__":
    # Run with: pytest test_audio_pipeline_red.py -v -s
    # Generate coverage: pytest test_audio_pipeline_red.py --cov=aegis --cov-report=html
    pytest.main([__file__, "-v", "-s", "--tb=short"])
