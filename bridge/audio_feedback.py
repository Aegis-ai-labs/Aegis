"""Audio feedback tones — listening chime, thinking tone, success chime."""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000  # 16kHz to match system


def generate_listening_chime() -> bytes:
    """
    Generate a pleasant "listening" chime (ascending notes).
    Returns 16-bit PCM bytes at 16kHz.
    """
    duration = 0.15  # 150ms
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Two ascending tones: C5 (523Hz) → E5 (659Hz)
    # Reduced amplitude (0.2 instead of 0.3) for small speakers to prevent distortion
    tone1 = np.sin(2 * np.pi * 523 * t[:samples//2]) * 0.2
    tone2 = np.sin(2 * np.pi * 659 * t[samples//2:]) * 0.2
    
    audio = np.concatenate([tone1, tone2])
    
    # Convert to 16-bit PCM
    pcm_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    return pcm_int16.tobytes()


def generate_thinking_tone() -> bytes:
    """
    Generate a "thinking" tone (subtle pulsing).
    Returns 16-bit PCM bytes at 16kHz.
    """
    duration = 0.2  # 200ms
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Low frequency pulse: 220Hz (A3) with 4Hz amplitude modulation
    # Reduced amplitude (0.15 instead of 0.2) for small speakers to prevent distortion
    carrier = np.sin(2 * np.pi * 220 * t)
    modulator = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
    audio = carrier * modulator * 0.15
    
    # Convert to 16-bit PCM
    pcm_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    return pcm_int16.tobytes()


def generate_success_chime() -> bytes:
    """
    Generate a "success" chime (completion tone).
    Returns 16-bit PCM bytes at 16kHz.
    """
    duration = 0.2  # 200ms
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples)
    
    # Descending harmonious tones: G5 (784Hz) → C5 (523Hz)
    # Reduced amplitude (0.18 instead of 0.25) for small speakers to prevent distortion
    tone1 = np.sin(2 * np.pi * 784 * t[:samples//2]) * 0.18
    tone2 = np.sin(2 * np.pi * 523 * t[samples//2:]) * 0.18
    
    audio = np.concatenate([tone1, tone2])
    
    # Fade out
    fade = np.linspace(1.0, 0.3, len(audio))
    audio = audio * fade
    
    # Convert to 16-bit PCM
    pcm_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    return pcm_int16.tobytes()
