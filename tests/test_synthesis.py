"""
tests/test_synthesis.py
=======================
Tests unitarios para síntesis de audio.
"""

import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audio.synthesis import (
    midi_to_freq, generate_sine, generate_sawtooth,
    apply_adsr, mix_waves, wave_to_stereo_int16
)
from src.utils.config import Config


@pytest.fixture
def config():
    return Config()


class TestMidiToFreq:
    def test_a4(self):
        assert abs(midi_to_freq(69) - 440.0) < 0.01

    def test_middle_c(self):
        assert abs(midi_to_freq(60) - 261.63) < 0.1

    def test_octave_relationship(self):
        """Una octava = doble de frecuencia."""
        f_low = midi_to_freq(60)
        f_high = midi_to_freq(72)  # C5
        assert abs(f_high / f_low - 2.0) < 0.01


class TestGenerateSine:
    def test_length(self, config):
        wave = generate_sine(440.0, 1.0, config.sample_rate)
        assert len(wave) == config.sample_rate

    def test_amplitude_range(self, config):
        wave = generate_sine(440.0, 0.5, config.sample_rate, amplitude=0.8)
        assert wave.max() <= 0.81  # Pequeña tolerancia numérica
        assert wave.min() >= -0.81

    def test_returns_float64(self, config):
        wave = generate_sine(440.0, 0.1, config.sample_rate)
        assert wave.dtype == np.float64


class TestApplyADSR:
    def test_starts_at_zero(self, config):
        """La envolvente empieza en 0 (attack desde silencio)."""
        wave = np.ones(config.sample_rate)
        result = apply_adsr(wave, config)
        assert abs(result[0]) < 0.01

    def test_ends_near_zero(self, config):
        """La envolvente termina cerca de 0 (release hacia silencio)."""
        wave = np.ones(config.sample_rate)
        result = apply_adsr(wave, config)
        assert abs(result[-1]) < 0.05

    def test_same_length(self, config):
        wave = np.ones(1000)
        result = apply_adsr(wave, config)
        assert len(result) == len(wave)


class TestMixWaves:
    def test_no_clipping_many_waves(self):
        """La mezcla normalizada no supera ±1.0."""
        waves = [np.ones(1000) * 0.8 for _ in range(10)]
        mixed = mix_waves(waves, normalize=True)
        assert mixed.max() <= 1.001  # Tolerancia de float

    def test_empty_list(self):
        result = mix_waves([])
        assert len(result) == 1

    def test_different_lengths_padded(self):
        w1 = np.ones(100)
        w2 = np.ones(200)
        mixed = mix_waves([w1, w2])
        assert len(mixed) == 200


class TestWaveToStereoInt16:
    def test_shape(self, config):
        wave = generate_sine(440, 0.1, config.sample_rate)
        stereo = wave_to_stereo_int16(wave, config)
        assert stereo.ndim == 2
        assert stereo.shape[1] == 2  # Estéreo = 2 canales

    def test_dtype_int16(self, config):
        wave = generate_sine(440, 0.1, config.sample_rate)
        stereo = wave_to_stereo_int16(wave, config)
        assert stereo.dtype == np.int16

    def test_no_overflow(self, config):
        """Los valores int16 deben estar en el rango válido."""
        wave = np.ones(1000)  # Amplitud máxima
        stereo = wave_to_stereo_int16(wave, config)
        assert stereo.max() <= 32767
        assert stereo.min() >= -32768
