"""
src/audio/mapping.py
====================
Estrategias de mapping sonoro: traducción de estado del autómata a parámetros musicales.

El mapping sonoro es el núcleo conceptual del proyecto desde una perspectiva
de Sonología. Define CÓMO el sistema computacional se traduce a experiencia auditiva.

TRES ESTRATEGIAS IMPLEMENTADAS:
================================

1. BÁSICO (basic)
   - Cada celda que nace dispara una frecuencia fija según su posición.
   - Posición X → frecuencia (izquierda=grave, derecha=agudo).
   - Simple pero predecible. Bueno para entender la mecánica.

2. MUSICAL (musical) ← RECOMENDADO
   - Las celdas se mapean a una escala musical (pentatónica menor por defecto).
   - La posición X determina qué nota de la escala.
   - La densidad global controla el volumen.
   - La posición Y determina el tipo de onda (seno=bajo, sierra=agudo).
   - Resultado: suena musical y coherente.

3. ESPECTRAL (spectral)
   - Inspirado en síntesis granular y music de espectro.
   - La densidad por columna controla amplitudes de "bandas" espectrales.
   - Produce texturas más abstractas y experimentales.
   - Justificación: el autómata como "ecualizador vivo" del espacio frecuencial.

DECISIONES DE DISEÑO:
=====================
- Escala pentatónica menor: 5 notas sin semitonos, nunca suena "mal".
  Usada en música folk mundial, blues, minimalismo. Robusta para generación
  automática porque carece de tritonos o intervalos disonantes problemáticos.

- Límite de voces (max_voices): la polifonía excesiva produce "masa" inaudible
  y colapsa el sistema. Con >12 voces simultáneas el cerebro no puede
  seguir líneas individuales (límite psicoacústico ≈ 4-6 voces claras).

- Prioridad de selección: entre todos los nacimientos posibles, seleccionamos
  los que están en posiciones más "interesantes" (bordes de clúster).
"""

import numpy as np
from typing import List, Tuple, Optional
from src.automata.grid import Grid
from src.audio.synthesis import midi_to_freq
from src.utils.config import Config


class SoundEvent:
    """
    Representa un evento sonoro a disparar en el motor de audio.

    Atributos
    ---------
    freq : float
        Frecuencia fundamental en Hz.
    amplitude : float
        Amplitud [0.0, 1.0].
    duration : float
        Duración en segundos.
    waveform : str
        Tipo de onda: 'sine', 'sawtooth', 'square', 'triangle'.
    pan : float
        Paneo estéreo [-1.0, 1.0].
    """
    def __init__(self, freq: float, amplitude: float = 0.5,
                 duration: float = 0.3, waveform: str = "sine",
                 pan: float = 0.0):
        self.freq = freq
        self.amplitude = amplitude
        self.duration = duration
        self.waveform = waveform
        self.pan = pan

    def __repr__(self):
        return f"SoundEvent(freq={self.freq:.1f}Hz, amp={self.amplitude:.2f}, wave={self.waveform})"


class BasicMapping:
    """
    Mapping básico: posición → frecuencia lineal.
    Cada columna dispara una frecuencia en rango [100, 2000] Hz.
    """
    def __init__(self, config: Config):
        self.config = config
        self.freq_min = 110.0   # A2
        self.freq_max = 1760.0  # A6

    def map(self, grid: Grid, birth_mask: np.ndarray, death_mask: np.ndarray
            ) -> List[SoundEvent]:
        events = []
        birth_positions = np.argwhere(birth_mask)  # Array de [row, col]

        # Limitar a max_voices eventos
        if len(birth_positions) > self.config.max_voices:
            indices = np.random.choice(len(birth_positions), self.config.max_voices, replace=False)
            birth_positions = birth_positions[indices]

        for row, col in birth_positions:
            # Mapeo lineal de columna a frecuencia
            t = col / max(grid.cols - 1, 1)  # Normalizar a [0, 1]
            freq = self.freq_min * (self.freq_max / self.freq_min) ** t  # Escala logarítmica
            pan = (t * 2) - 1  # [0,1] → [-1,1]
            events.append(SoundEvent(freq=freq, amplitude=0.4, duration=0.2, pan=pan))

        return events


class MusicalMapping:
    """
    Mapping musical: posición → nota en escala pentatónica.

    Principios:
    - Eje X (columna) → selección de nota en la escala
    - Eje Y (fila) → selección de timbre (onda)
    - Densidad global → amplitud de voces
    - Número de nacimientos → controla cuántas voces suenan

    La escala pentatónica menor (ej: C3, Eb3, F3, G3, Bb3) es la elección
    más segura para generación automática: ningún intervalo resulta
    disonante sin contexto armónico.
    """

    WAVEFORMS_BY_ZONE = {
        0: "sine",      # Zona superior: sonidos suaves
        1: "triangle",  # Zona media-alta
        2: "square",    # Zona media-baja
        3: "sawtooth",  # Zona inferior: sonidos brillantes
    }

    def __init__(self, config: Config):
        self.config = config
        self.scale = config.scale_midi
        self.n_scale = len(self.scale)

    def map(self, grid: Grid, birth_mask: np.ndarray, death_mask: np.ndarray
            ) -> List[SoundEvent]:

        birth_positions = np.argwhere(birth_mask)
        if len(birth_positions) == 0:
            return []

        density = grid.density

        # Amplitud inversamente proporcional a densidad: más celdas → cada una más suave
        # Esto previene clipping cuando hay muchos nacimientos simultáneos.
        # Fórmula: amp_base / sqrt(n_voices) (distribución de potencia uniforme)
        n_voices = min(len(birth_positions), self.config.max_voices)
        base_amp = 0.5 / max(np.sqrt(n_voices), 1.0)
        base_amp = np.clip(base_amp, 0.05, 0.4)

        # Selección de las voces más "interesantes"
        selected = self._select_voices(birth_positions, n_voices, grid)

        events = []
        for row, col in selected:
            # ── Nota ────────────────────────────────────────────────────
            scale_idx = int((col / grid.cols) * self.n_scale)
            scale_idx = np.clip(scale_idx, 0, self.n_scale - 1)
            midi_note = self.scale[scale_idx]
            freq = midi_to_freq(midi_note)

            # ── Duración ─────────────────────────────────────────────────
            # Mayor densidad → notas más cortas (textura más percusiva)
            duration = self.config.note_duration * (1.0 - density * 0.5)
            duration = max(duration, 0.08)

            # ── Timbre por zona vertical ──────────────────────────────────
            zone = int((row / grid.rows) * 4)
            zone = np.clip(zone, 0, 3)
            waveform = self.WAVEFORMS_BY_ZONE[zone]

            # ── Paneo: columna → posición estéreo ─────────────────────────
            pan = (col / grid.cols) * 2 - 1

            events.append(SoundEvent(
                freq=freq,
                amplitude=base_amp,
                duration=duration,
                waveform=waveform,
                pan=pan
            ))

        return events

    def _select_voices(self, positions: np.ndarray, n: int, grid: Grid
                       ) -> np.ndarray:
        """
        Selecciona las n posiciones más interesantes para sonificar.

        Criterio: preferir celdas en bordes de clústeres (vecindad mixta),
        que representan "actividad" en el borde de estructuras. Esta selección
        produce un sonido que refleja la dinámica del autómata mejor que
        un muestreo aleatorio.
        """
        if len(positions) <= n:
            return positions

        # Calcular "interés" = número de vecinos vivos (borde si 1-3 vecinos)
        from scipy.signal import convolve2d
        from src.automata.grid import MOORE_KERNEL
        neighbor_count = convolve2d(grid.cells, MOORE_KERNEL, mode="same", boundary="wrap")

        # Score = abs(neighbor_count - 4): máximo en bordes (2-3 vecinos), mínimo en interior
        scores = np.abs(neighbor_count[positions[:, 0], positions[:, 1]] - 4)
        top_indices = np.argsort(scores)[-n:]  # Los n más altos
        return positions[top_indices]


class SpectralMapping:
    """
    Mapping espectral experimental.

    La cuadrícula se divide en bandas verticales, cada una correspondiente
    a una "banda de frecuencia". La densidad de cada banda controla si esa
    frecuencia está presente en el sonido (como un ecualizador vivo).

    Inspiración teórica: análisis espectral inverso. En lugar de analizar
    un sonido para obtener su espectro, usamos el "espectro" del autómata
    para sintetizar el sonido.

    Resultado: texturas continuas que evolucionan con el patrón visual.
    Más adecuado para experimentación y música de proceso.
    """
    def __init__(self, config: Config):
        self.config = config
        # Dividir el rango audible en bandas logarítmicas
        self.n_bands = 16
        self.freqs = np.logspace(np.log10(80), np.log10(3200), self.n_bands)

    def map(self, grid: Grid, birth_mask: np.ndarray, death_mask: np.ndarray
            ) -> List[SoundEvent]:
        """
        En el mapping espectral, no disparamos eventos por nacimiento sino
        que generamos continuamente un sinusoide por banda cuya amplitud
        es la densidad de esa banda.
        """
        col_densities = grid.get_column_densities()  # (cols,)
        events = []

        bands_per_col = grid.cols / self.n_bands

        for i, freq in enumerate(self.freqs):
            col_start = int(i * bands_per_col)
            col_end = int((i + 1) * bands_per_col)
            col_end = min(col_end, grid.cols)

            band_density = col_densities[col_start:col_end].mean() if col_start < col_end else 0.0

            if band_density > 0.05:  # Umbral: no sonar bandas vacías
                amplitude = band_density * 0.3  # Escalar suavemente
                pan = (i / self.n_bands) * 2 - 1
                events.append(SoundEvent(
                    freq=float(freq),
                    amplitude=amplitude,
                    duration=1.0 / max(self.config.fps, 1) * 1.5,  # Ligeramente más larga que un frame
                    waveform="sine",
                    pan=pan
                ))

        # En mapping espectral no limitamos por max_voices de la misma forma,
        # pero sí limitamos para evitar sobrecarga de CPU
        return events[:self.config.max_voices * 2]


def get_mapper(config: Config):
    """Factory: retorna el mapper correcto según config.mapping."""
    mappers = {
        "basic": BasicMapping,
        "musical": MusicalMapping,
        "spectral": SpectralMapping,
    }
    cls = mappers.get(config.mapping, MusicalMapping)
    return cls(config)
