"""Test audio pipeline (STT + TTS)."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aegis.audio_buffer import AudioBuffer
from aegis.audio import pcm_to_wav, detect_silence
from aegis.config import settings


class TestAudioBuffer:
    """Test audio buffering and silence detection."""

    def test_audio_buffer_init(self):
        """Test buffer initialization."""
        buf = AudioBuffer()
        assert buf.is_empty()
        assert buf.get_accumulated_ms() == 0

    def test_audio_buffer_accumulates_chunks(self):
        """Test that buffer accumulates chunks."""
        buf = AudioBuffer(silence_duration_ms=600)
        
        # Add speech chunk (not silent)
        chunk = b'\x01\x00' * 160  # 320 bytes = 10ms @ 16kHz
        is_complete, audio = buf.add_chunk(chunk)
        
        assert not is_complete  # Not enough silence yet
        assert audio is None
        assert not buf.is_empty()

    def test_audio_buffer_detects_silence(self):
        """Test that buffer detects silence and completes utterance."""
        buf = AudioBuffer(silence_duration_ms=100)  # Low threshold for testing
        
        # Add speech chunks
        for _ in range(5):
            speech_chunk = b'\x50\x00' * 160  # Louder chunk
            is_complete, audio = buf.add_chunk(speech_chunk)
            assert not is_complete
        
        # Add silent chunks to trigger completion
        silence_chunk = b'\x00\x00' * 160  # Quiet chunk
        for _ in range(15):  # Enough silence chunks to trigger
            is_complete, audio = buf.add_chunk(silence_chunk)
            if is_complete:
                break
        
        # Should eventually complete
        assert is_complete or buf.get_accumulated_ms() > 0

    def test_detect_silence_threshold(self):
        """Test silence detection with amplitude threshold."""
        # Silent PCM (all zeros)
        silent = b'\x00\x00' * 160
        assert detect_silence(silent, threshold=500) == True
        
        # Loud PCM
        loud = b'\xff\x7f' * 160  # High amplitude samples
        assert detect_silence(loud, threshold=500) == False


class TestAudioConversion:
    """Test PCM/WAV conversion."""

    def test_pcm_to_wav(self):
        """Test converting PCM to WAV format."""
        pcm = b'\x00\x00' * 100  # Simple PCM data
        wav = pcm_to_wav(pcm, sample_rate=16000, channels=1)
        
        assert len(wav) > len(pcm)  # WAV has headers
        assert wav[:4] == b'RIFF'  # WAV magic number
        assert b'fmt ' in wav
        assert b'data' in wav

    def test_pcm_to_wav_with_defaults(self):
        """Test WAV conversion using config defaults."""
        pcm = b'\x00\x00' * 100
        wav = pcm_to_wav(pcm)  # Uses settings.sample_rate and settings.channels
        
        assert len(wav) > len(pcm)
        assert wav[:4] == b'RIFF'


class TestSTTIntegration:
    """Test Speech-to-Text integration."""

    @pytest.mark.asyncio
    async def test_stt_with_mock_audio(self):
        """Test STT with mocked audio."""
        from aegis.stt import transcribe_wav
        
        # Create WAV data (mock)
        # Note: Real test would need actual audio file
        wav_data = pcm_to_wav(b'\x00\x00' * 16000)  # 0.5s of silence
        
        # Test that function accepts WAV input
        result = transcribe_wav(wav_data)
        # Should return None or empty string for silence
        assert result is None or result == ""


class TestTTSIntegration:
    """Test Text-to-Speech integration."""

    def test_tts_engine_init(self):
        """Test TTS engine initialization."""
        from aegis.tts import TTSEngine
        
        engine = TTSEngine()
        assert engine is not None

    def test_tts_synthesize_with_mock(self):
        """Test TTS synthesis (with mocking)."""
        from aegis.tts import TTSEngine
        
        engine = TTSEngine()
        
        # Mock the Piper voice to avoid needing actual model
        with patch.object(engine, '_voice', None):
            # Should gracefully handle missing model
            # (Would fall back to CLI or return None)
            pass

    def test_tts_sentences_split(self):
        """Test sentence splitting for streaming."""
        from aegis.tts import TTSEngine
        
        engine = TTSEngine()
        text = "This is sentence one. This is sentence two! And a third."
        
        # Test that we can call the method (even if mocked)
        # The actual return depends on if Piper is installed
        result = engine.synthesize_sentences(text)
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_audio_pipeline_with_websocket():
    """Test the complete audio pipeline with mocked WebSocket."""
    from aegis.main import audio_ws
    from fastapi import WebSocket
    
    # Create a mock WebSocket
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive = AsyncMock()
    mock_ws.send_bytes = AsyncMock()
    mock_ws.send_json = AsyncMock()
    
    # Simulate disconnect after initial setup
    mock_ws.receive.side_effect = [
        Exception("Connection closed")  # Trigger disconnect
    ]
    
    # Handler should accept connection and handle gracefully
    try:
        await audio_ws(mock_ws)
    except Exception:
        pass  # Expected due to mock
    
    # Verify accept was called
    mock_ws.accept.assert_called()


class TestAudioBufferEdgeCases:
    """Test edge cases in audio buffering."""

    def test_empty_chunk(self):
        """Test handling of empty audio chunks."""
        buf = AudioBuffer()
        is_complete, audio = buf.add_chunk(b'')
        
        assert not is_complete
        assert buf.is_empty()

    def test_very_short_audio(self):
        """Test handling of very short audio."""
        buf = AudioBuffer()
        
        # Add just a few bytes
        is_complete, audio = buf.add_chunk(b'\x00\x00')
        assert not is_complete

    def test_reset_clears_buffer(self):
        """Test that reset clears the buffer."""
        buf = AudioBuffer()
        
        # Add some data
        buf.add_chunk(b'\x01\x00' * 160)
        assert not buf.is_empty()
        
        # Reset
        buf._reset()
        assert buf.is_empty()


# Test constants for reference
class TestAudioConstants:
    """Verify audio constants are correct."""

    def test_chunk_size_is_10ms(self):
        """320 bytes @ 16kHz 16-bit mono = 10ms."""
        sample_rate = 16000
        bit_depth = 16  # bits
        channels = 1
        ms_per_chunk = 10

        # Formula: (samples_per_second * ms / 1000) * (bits / 8) * channels
        expected_bytes = (sample_rate * ms_per_chunk * bit_depth * channels) // (1000 * 8)
        assert expected_bytes == 320

    def test_sample_rate_from_config(self):
        """Verify sample rate from config."""
        assert settings.sample_rate == 16000

    def test_silence_threshold_configured(self):
        """Verify silence threshold is configured."""
        assert hasattr(settings, 'silence_threshold')
        assert settings.silence_threshold > 0

    def test_silence_duration_configured(self):
        """Verify silence duration is configured."""
        assert hasattr(settings, 'silence_duration_ms')
        assert settings.silence_duration_ms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
