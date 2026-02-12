"""Test audio processing utilities."""

import struct

from aegis.audio import pcm_to_wav, wav_to_pcm, detect_silence, calculate_rms


def test_pcm_to_wav_roundtrip():
    # Generate 100ms of silence (16kHz, 16-bit mono)
    n_samples = 1600
    pcm_data = struct.pack(f"<{n_samples}h", *([0] * n_samples))

    wav_data = pcm_to_wav(pcm_data, sample_rate=16000)
    assert wav_data[:4] == b"RIFF"

    recovered = wav_to_pcm(wav_data)
    assert recovered == pcm_data


def test_detect_silence_on_silent():
    n_samples = 1600
    silent_pcm = struct.pack(f"<{n_samples}h", *([0] * n_samples))
    assert detect_silence(silent_pcm, threshold=500) is True


def test_detect_silence_on_loud():
    import math
    n_samples = 1600
    # Generate a 1kHz tone
    samples = [int(16000 * math.sin(2 * math.pi * 1000 * i / 16000)) for i in range(n_samples)]
    loud_pcm = struct.pack(f"<{n_samples}h", *samples)
    assert detect_silence(loud_pcm, threshold=500) is False


def test_calculate_rms():
    n_samples = 160
    silent_pcm = struct.pack(f"<{n_samples}h", *([0] * n_samples))
    assert calculate_rms(silent_pcm) == 0.0

    loud_pcm = struct.pack(f"<{n_samples}h", *([10000] * n_samples))
    assert calculate_rms(loud_pcm) == 10000.0
