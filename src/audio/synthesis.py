"""
src/audio/synthesis.py
======================
Síntesis de audio: osciladores y envolvente ADSR.

CONCEPTOS CLAVE:
----------------
1. Representación digital del audio
   Un sonido digital es simplemente un array de floats en [-1.0, 1.0].
   A 44100 Hz, 1 segundo = 44100 muestras. Cada valor indica la amplitud
   de la onda en ese instante (similar a posición de membrana de altavoz).

2. Frecuencia a partir de nota MIDI
   MIDI note 69 = A4 = 440 Hz. La fórmula estándar es:
       freq = 440 * 2^((midi - 69) / 12)
   Cada semitono es un factor de 2^(1/12) ≈ 1.0595.

3. Generación de onda senoidal
   Sin(2π·f·t) donde t = [0, 1/sr, 2/sr, ...] vector de tiempos.
   Usamos NumPy vectorizado para generar miles de muestras en microsegundos.

4. ADSR (Attack, Decay, Sustain, Release)
   Envolvente que modula la amplitud en el tiempo:
   - Attack: rampa de 0 a 1 (sube)
   - Decay: rampa de 1 a sustain_level (baja un poco)
   - Sustain: nivel constante (mientras dura la nota)
   - Release: rampa de sustain_level a 0 (desvanece)
   Sin ADSR las notas "clican" al empezar/terminar (artefacto de audio).

5. Clipping
   Si la suma de varias ondas supera ±1.0, se produce distorsión dura.
   Solución: normalizar y limitar antes de convertir a int16 para pygame.
"""

import numpy as np
from src.utils.config import Config


def midi_to_freq(midi_note: int) -> float:
    """Convierte nota MIDI a frecuencia en Hz. A4=69=440Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def generate_sine(freq: float, duration: float, sample_rate: int,
                  amplitude: float = 1.0) -> np.ndarray:
    """
    Genera una onda senoidal pura.

    Parámetros
    ----------
    freq : float
        Frecuencia en Hz.
    duration : float
        Duración en segundos.
    sample_rate : int
        Muestras por segundo (Hz).
    amplitude : float
        Amplitud pico [0.0, 1.0].

    Retorna
    -------
    np.ndarray (float64, shape: (n_samples,))
        Valores de la onda en [-amplitude, +amplitude].
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)


def generate_sawtooth(freq: float, duration: float, sample_rate: int,
                      amplitude: float = 1.0, n_harmonics: int = 8) -> np.ndarray:
    """
    Genera onda diente de sierra mediante suma de armónicos (síntesis aditiva).
    
    Una sierra perfecta = suma de Sen(n·f) / n para n=1,2,3,...
    Limitamos los armónicos para evitar aliasing (frecuencias fantasma).
    Timbre más brillante y agresivo que el seno.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    wave = np.zeros(n_samples)
    for k in range(1, n_harmonics + 1):
        if k * freq < sample_rate / 2:  # Criterio de Nyquist: evitar aliasing
            wave += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * freq * t) / k
    # Normalizar a rango [-1, 1] antes de aplicar amplitud
    max_val = np.max(np.abs(wave)) or 1.0
    return amplitude * (wave / max_val)


def generate_square(freq: float, duration: float, sample_rate: int,
                    amplitude: float = 1.0, n_harmonics: int = 8) -> np.ndarray:
    """
    Onda cuadrada: solo armónicos impares (n=1,3,5,...) con amplitud 1/n.
    Timbre hueco, similar a clarinete.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    wave = np.zeros(n_samples)
    for k in range(1, n_harmonics * 2, 2):  # Solo impares
        if k * freq < sample_rate / 2:
            wave += np.sin(2 * np.pi * k * freq * t) / k
    max_val = np.max(np.abs(wave)) or 1.0
    return amplitude * (wave / max_val)


def generate_triangle(freq: float, duration: float, sample_rate: int,
                      amplitude: float = 1.0) -> np.ndarray:
    """
    Onda triangular: armónicos impares con amplitud 1/n².
    Más suave que la cuadrada, sin bordes abruptos.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    wave = np.zeros(n_samples)
    for k in range(1, 10, 2):
        if k * freq < sample_rate / 2:
            sign = (-1) ** ((k - 1) // 2)
            wave += sign * np.sin(2 * np.pi * k * freq * t) / (k ** 2)
    max_val = np.max(np.abs(wave)) or 1.0
    return amplitude * (wave / max_val)


def apply_adsr(wave: np.ndarray, config: Config) -> np.ndarray:
    """
    Aplica envolvente ADSR a una onda.

    La envolvente es un array multiplicador que va de 0 a 1 y vuelve a 0,
    con la forma característica ataque-decaimiento-sostenido-liberación.

    CRÍTICO para calidad de audio: sin esto, cada nota produce un "clic"
    audible al empezar y terminar (discontinuidad en la señal).

    Parámetros
    ----------
    wave : np.ndarray
        Onda de audio sin procesar.
    config : Config
        Contiene attack, decay, sustain, release en segundos/nivel.

    Retorna
    -------
    np.ndarray
        Onda con la envolvente aplicada.
    """
    sr = config.sample_rate
    n = len(wave)

    # Convertir tiempos ADSR a número de muestras
    a_samp = min(int(config.adsr_attack * sr), n)
    d_samp = min(int(config.adsr_decay * sr), n - a_samp)
    r_samp = min(int(config.adsr_release * sr), n)
    s_samp = max(n - a_samp - d_samp - r_samp, 0)

    # Construir envolvente como concatenación de rampas lineales
    envelope = np.concatenate([
        np.linspace(0.0, 1.0, a_samp, endpoint=False),          # Attack
        np.linspace(1.0, config.adsr_sustain, d_samp, endpoint=False),  # Decay
        np.full(s_samp, config.adsr_sustain),                    # Sustain
        np.linspace(config.adsr_sustain, 0.0, r_samp),           # Release
    ])

    # Ajustar longitud exacta (puede diferir por redondeo)
    if len(envelope) < n:
        envelope = np.pad(envelope, (0, n - len(envelope)))
    else:
        envelope = envelope[:n]

    return wave * envelope


def mix_waves(waves: list, normalize: bool = True) -> np.ndarray:
    """
    Mezcla múltiples ondas sumándolas y normalizando para evitar clipping.

    El clipping ocurre cuando la suma supera ±1.0 antes de convertir a int16.
    Normalizar divide por el máximo absoluto si supera 1.0.

    NOTA: normalización post-facto puede reducir dinámica. Una estrategia
    más sofisticada es ajustar amplitude por voz desde el principio
    (ver AudioEngine.compute_voice_amplitude).

    Parámetros
    ----------
    waves : list of np.ndarray
        Lista de ondas. Deben tener la misma longitud.
    normalize : bool
        Si True, normaliza la mezcla para evitar clipping.

    Retorna
    -------
    np.ndarray (float64)
        Mezcla de todas las ondas.
    """
    if not waves:
        return np.zeros(1)

    # Igualar longitudes (la más larga gana, las demás se rellenan con ceros)
    max_len = max(len(w) for w in waves)
    padded = [np.pad(w, (0, max_len - len(w))) for w in waves]

    mixed = np.sum(padded, axis=0)

    if normalize:
        peak = np.max(np.abs(mixed))
        if peak > 1.0:
            mixed /= peak  # Normalización suave: mantiene relaciones de amplitud

    return mixed


def wave_to_stereo_int16(wave: np.ndarray, config: Config) -> np.ndarray:
    """
    Convierte onda mono float64 a formato estéreo int16 para pygame.mixer.

    pygame.sndarray.make_sound() espera array int16 de shape (n_samples, 2).
    El rango int16 es [-32768, 32767].

    Parámetros
    ----------
    wave : np.ndarray (float64, mono)
        Valores en [-1.0, 1.0].
    config : Config
        Para aplicar volumen maestro.

    Retorna
    -------
    np.ndarray (int16, shape: (n_samples, 2))
    """
    # Aplicar volumen maestro y asegurar que no hay clipping
    scaled = np.clip(wave * config.master_volume, -1.0, 1.0)

    # Convertir a int16
    int16_wave = (scaled * 32767).astype(np.int16)

    # Duplicar canal (mono → estéreo)
    return np.column_stack([int16_wave, int16_wave])


def wave_to_stereo_panned(wave: np.ndarray, pan: float, config: Config) -> np.ndarray:
    """
    Convierte onda mono a estéreo con paneo.

    Parámetros
    ----------
    pan : float
        -1.0 = todo izquierda, 0.0 = centro, +1.0 = todo derecha.
        Usamos ley de paneo de potencia constante (constant-power panning):
        L = cos(θ), R = sin(θ) donde θ ∈ [0, π/2].
    """
    import math
    theta = (pan + 1.0) / 2.0 * (math.pi / 2.0)  # mapear [-1,1] a [0, π/2]
    left_gain = math.cos(theta)
    right_gain = math.sin(theta)

    scaled = np.clip(wave * config.master_volume, -1.0, 1.0)
    left = (scaled * left_gain * 32767).astype(np.int16)
    right = (scaled * right_gain * 32767).astype(np.int16)
    return np.column_stack([left, right])
