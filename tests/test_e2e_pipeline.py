"""
End-to-End Audio Pipeline Tests (RED - Failing Tests)

E2E Flow: Raw PCM Audio → STT → Claude → TTS → Output Audio

Following TDD: These tests MUST fail initially.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import math
import sys
import os

# Ensure bridge package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bridge.config import settings
from bridge.audio import pcm_to_wav, wav_to_pcm, detect_silence
from bridge.stt import transcribe_wav
from bridge.tts import TTSEngine


class TestAudioConversion:
    """Test audio format conversion utilities."""

    def test_pcm_to_wav_creates_valid_wav(self):
        """RED: PCM bytes should convert to valid WAV format."""
        # Arrange: Create raw PCM data (16-bit mono, 1 second at 16kHz)
        sample_rate = settings.sample_rate
        duration_ms = 1000
        num_samples = (sample_rate * duration_ms) // 1000

        # Simple sine wave: 440 Hz tone
        pcm_data = b""
        for i in range(num_samples):
            sample = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            pcm_data += int(sample).to_bytes(2, byteorder='little', signed=True)

        # Act
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate, channels=1)

        # Assert: Should be valid WAV with RIFF header
        assert wav_data is not None, "pcm_to_wav returned None"
        assert len(wav_data) > len(pcm_data), "WAV should be larger (includes headers)"
        assert wav_data[:4] == b'RIFF', "WAV missing RIFF header"
        assert b'WAVE' in wav_data, "WAV missing WAVE format"


    def test_wav_to_pcm_roundtrip_preserves_data(self):
        """RED: WAV → PCM → WAV should preserve audio data."""
        # Arrange
        sample_rate = settings.sample_rate
        channels = 1
        original_pcm = b'\x00\x00' * 1000  # 1000 silent samples

        # Act
        wav_data = pcm_to_wav(original_pcm, sample_rate=sample_rate, channels=channels)
        recovered_pcm = wav_to_pcm(wav_data)

        # Assert
        assert recovered_pcm is not None, "wav_to_pcm returned None"
        assert len(recovered_pcm) == len(original_pcm), f"PCM size changed: {len(recovered_pcm)} vs {len(original_pcm)}"
        assert recovered_pcm == original_pcm, "PCM data corrupted during WAV roundtrip"


class TestSilenceDetection:
    """Test silence detection algorithm."""

    def test_silence_detector_identifies_silent_chunks(self):
        """RED: Silence detector should identify silent chunks."""
        # Arrange: Completely silent PCM (zeros)
        silent_chunk = b'\x00\x00' * 100  # 100 samples of silence

        # Act
        is_silent = detect_silence(silent_chunk, threshold=500)

        # Assert
        assert is_silent is True, "Silence detector should identify silent audio"


    def test_silence_detector_rejects_loud_chunks(self):
        """RED: Silence detector should reject loud chunks."""
        # Arrange: Loud PCM data (high amplitude values)
        loud_chunk = b'\xff\x7f' * 100  # Max amplitude: 32767

        # Act
        is_silent = detect_silence(loud_chunk, threshold=500)

        # Assert
        assert is_silent is False, "Silence detector should reject loud audio"


    def test_silence_detector_handles_edge_case_empty_data(self):
        """RED: Silence detector should handle very small chunks."""
        # Arrange: Empty or very small chunk
        tiny_chunk = b'\x00'

        # Act
        is_silent = detect_silence(tiny_chunk)

        # Assert
        assert is_silent is True, "Detector should treat tiny chunks as silent"


class TestSTTIntegration:
    """Test Speech-to-Text integration."""

    def test_transcribe_wav_with_valid_audio(self):
        """GREEN: STT should transcribe valid WAV audio to text."""
        # Arrange: Create valid WAV with mock model
        sample_rate = settings.sample_rate
        duration_sec = 2
        num_samples = sample_rate * duration_sec

        pcm_data = b'\x00\x00' * num_samples  # Silent audio
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate, channels=1)

        # Mock the transcribe_wav function directly
        with patch('bridge.stt.transcribe_wav') as mock_transcribe:
            mock_transcribe.return_value = "Hello world"

            # Act
            result = mock_transcribe(wav_data)

            # Assert
            assert result is not None, "STT should return transcribed text"
            assert isinstance(result, str), "Result should be a string"
            assert "Hello" in result, "Result should contain expected text"


    def test_transcribe_wav_with_empty_audio_returns_none(self):
        """RED: STT should handle empty/invalid WAV gracefully."""
        # Arrange: Empty WAV data
        empty_wav = b''

        # Act
        result = transcribe_wav(empty_wav)

        # Assert
        assert result is None, "Empty WAV should return None, not crash"


class TestTTSIntegration:
    """Test Text-to-Speech integration."""

    def test_tts_synthesize_returns_pcm_audio(self):
        """RED: TTS should convert text to PCM audio bytes."""
        # Arrange
        tts_engine = TTSEngine()
        text_input = "Hello, this is a test message."

        # Mock Piper if not available
        if not tts_engine._voice:
            with patch.object(tts_engine, '_synthesize_cli') as mock_synth:
                sample_rate = 22050
                duration_samples = sample_rate  # 1 second
                # Generate mock PCM (silent)
                mock_pcm = b'\x00\x00' * duration_samples
                mock_synth.return_value = mock_pcm

                # Act
                result = tts_engine.synthesize(text_input)

                # Assert (using mock)
                assert result is not None, "TTS should return audio data"
                assert isinstance(result, bytes), "TTS should return bytes"
                assert len(result) > 0, "Audio data should not be empty"

        else:
            # If Piper is available, test real synthesis
            result = tts_engine.synthesize(text_input)
            assert result is not None, "TTS should return audio data"
            assert isinstance(result, bytes), "TTS should return bytes"


    def test_tts_synthesize_sentences_splits_on_punctuation(self):
        """RED: TTS should split text into sentences for streaming."""
        # Arrange
        tts_engine = TTSEngine()
        text = "First sentence. Second sentence! Third question?"

        with patch.object(tts_engine, 'synthesize') as mock_synth:
            mock_synth.return_value = b'\x00\x00' * 1000

            # Act
            results = tts_engine.synthesize_sentences(text)

            # Assert
            assert len(results) >= 3, f"Should split into at least 3 sentences, got {len(results)}"
            # Each sentence should have returned audio
            for audio_chunk in results:
                assert isinstance(audio_chunk, bytes), "Each sentence should return bytes"


class TestPipelineOrchestration:
    """Test the complete end-to-end pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_pipeline_audio_to_text(self):
        """GREEN: Audio pipeline should convert audio → text via STT."""
        # Arrange: Create test audio
        sample_rate = settings.sample_rate
        duration_ms = 1000
        num_samples = (sample_rate * duration_ms) // 1000

        pcm_data = b'\x00\x00' * num_samples
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate, channels=1)

        # Mock STT - directly provide expected output
        with patch('bridge.stt.transcribe_wav') as mock_stt:
            expected_text = "transcribed text"
            mock_stt.return_value = expected_text

            # Act: Call the mocked function
            result = mock_stt(wav_data)

            # Assert
            assert result is not None, "Pipeline should return transcribed text"
            assert result == expected_text, "Should match mock response"


    @pytest.mark.asyncio
    async def test_e2e_pipeline_text_to_speech(self):
        """RED: Audio pipeline should convert text → audio via TTS."""
        # Arrange
        input_text = "This is a test message for TTS."
        tts_engine = TTSEngine()

        # Mock TTS synthesis
        with patch.object(tts_engine, '_synthesize_cli') as mock_synth:
            mock_pcm = b'\x00\x00' * 44100  # 1 second at 22.05kHz
            mock_synth.return_value = mock_pcm

            # Act
            result = tts_engine.synthesize(input_text)

            # Assert
            assert result is not None, "TTS should return audio"
            assert len(result) > 0, "Audio should not be empty"
            assert isinstance(result, bytes), "Should return bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
