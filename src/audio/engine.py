"""
src/audio/engine.py
===================
Motor de audio: integra síntesis, mapping y pygame.mixer.

ARQUITECTURA DEL AUDIO EN PYGAME:
==================================
pygame.mixer trabaja con objetos Sound que se reproducen en "canales".
Un canal es una voz simultánea. pygame.mixer.pre_init() debe llamarse
ANTES de pygame.init() para configurar sample_rate y buffer_size.

FLUJO DE UN EVENTO SONORO:
    SoundEvent → synthesis.py → array numpy → pygame.Sound → channel.play()

PROBLEMAS COMUNES Y SOLUCIONES:
================================

1. Clipping (distorsión dura)
   Causa: suma de ondas supera ±1 antes de convertir a int16.
   Solución: normalización en mix_waves() + amplitud por voz ∝ 1/√n_voces.

2. Audio entrecortado (buffer underrun)
   Causa: buffer_size muy pequeño. El hilo de audio no puede llenar el buffer
   a tiempo → silencios breves repetidos.
   Solución: buffer_size=512 o 1024 (compromiso latencia/estabilidad).
   En sistemas lentos, aumentar a 2048.

3. Saturación de polifonía
   Causa: demasiados canales activos simultáneamente.
   Solución: max_voices limita los eventos por frame. La implementación
   usa un pool de canales y recicla los más viejos.

4. Latencia de síntesis
   Causa: generar audio en el hilo principal bloquea la visualización.
   Solución MVP: aceptar latencia ~1 frame (ok para 10fps).
   Solución avanzada: síntesis en hilo separado con cola thread-safe.
"""

import numpy as np
import pygame
from src.audio.synthesis import (
    generate_sine, generate_sawtooth, generate_square, generate_triangle,
    apply_adsr, wave_to_stereo_panned
)
from src.audio.mapping import get_mapper, SoundEvent
from src.automata.grid import Grid
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Diccionario de generadores por tipo de onda
GENERATORS = {
    "sine":     generate_sine,
    "sawtooth": generate_sawtooth,
    "square":   generate_square,
    "triangle": generate_triangle,
}


class AudioEngine:
    """
    Motor de audio que conecta el autómata con pygame.mixer.

    Gestiona:
    - Inicialización del mixer
    - Pool de canales de audio
    - Traducción de SoundEvents a sonido real
    - Control de volumen y mute
    """

    def __init__(self, config: Config):
        self.config = config
        self.muted = False
        self._init_mixer()
        self.mapper = get_mapper(config)
        # Pool de canales: pygame permite máximo N canales simultáneos
        self.n_channels = config.max_voices + 4  # Margen extra
        pygame.mixer.set_num_channels(self.n_channels)
        self._channels = [pygame.mixer.Channel(i) for i in range(self.n_channels)]
        self._channel_idx = 0  # Round-robin: siempre usamos el siguiente canal
        logger.info(f"AudioEngine iniciado | SR={config.sample_rate}Hz | "
                    f"Buffer={config.buffer_size} | Canales={self.n_channels}")

    def _init_mixer(self):
        """
        Inicializa pygame.mixer con los parámetros correctos.

        IMPORTANTE: pre_init DEBE llamarse antes de pygame.init().
        Si ya fue inicializado (en main.py llamamos pygame.init() primero),
        esto no tendrá efecto. Por eso en main.py el orden es:
            pygame.init() → AudioEngine.__init__() → ...
        Pero AudioEngine llama pre_init internamente como salvaguarda.
        """
        pygame.mixer.pre_init(
            frequency=self.config.sample_rate,
            size=-16,              # -16 = int16 con signo (estándar)
            channels=self.config.channels,
            buffer=self.config.buffer_size
        )
        pygame.mixer.init()
        # Verificar que la configuración se aplicó correctamente
        actual = pygame.mixer.get_init()
        if actual:
            logger.debug(f"Mixer inicializado: SR={actual[0]}Hz, bits={actual[1]}, ch={actual[2]}")
        else:
            logger.error("Fallo al inicializar pygame.mixer")

    def sonify(self, grid: Grid, birth_mask: np.ndarray, death_mask: np.ndarray):
        """
        Punto de entrada principal: toma el estado del autómata y produce audio.

        Llamado una vez por frame desde main.py.

        Parámetros
        ----------
        grid : Grid
            Estado actual de la cuadrícula.
        birth_mask : np.ndarray (bool)
            Máscara de celdas que nacieron en este step.
        death_mask : np.ndarray (bool)
            Máscara de celdas que murieron en este step.
        """
        if self.muted:
            return

        events = self.mapper.map(grid, birth_mask, death_mask)

        for event in events:
            self._play_event(event)

    def _play_event(self, event: SoundEvent):
        """
        Sintetiza y reproduce un SoundEvent en el siguiente canal disponible.

        Round-robin: usamos self._channel_idx y avanzamos, volviendo a 0
        cuando llegamos al final. Si el canal está activo, lo interrumpimos
        (el canal más viejo sacrificado por el más nuevo).
        """
        try:
            wave = self._synthesize(event)
            sound = pygame.sndarray.make_sound(wave)

            ch = self._channels[self._channel_idx]
            ch.play(sound)
            self._channel_idx = (self._channel_idx + 1) % self.n_channels

        except Exception as e:
            logger.warning(f"Error reproduciendo evento: {e}")

    def _synthesize(self, event: SoundEvent) -> np.ndarray:
        """
        Genera el array de audio int16 para un SoundEvent.

        Pipeline: generar onda → aplicar ADSR → convertir a estéreo int16.
        """
        generator = GENERATORS.get(event.waveform, generate_sine)

        wave = generator(
            freq=event.freq,
            duration=event.duration,
            sample_rate=self.config.sample_rate,
            amplitude=event.amplitude
        )

        wave = apply_adsr(wave, self.config)
        stereo = wave_to_stereo_panned(wave, event.pan, self.config)
        return stereo

    def adjust_volume(self, delta: float):
        """Ajusta volumen maestro en ±delta."""
        self.config.master_volume = float(np.clip(self.config.master_volume + delta, 0.0, 1.0))
        logger.debug(f"Volumen: {self.config.master_volume:.2f}")

    def toggle_mute(self):
        """Silenciar/activar audio."""
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.stop()
        logger.info(f"Audio {'silenciado' if self.muted else 'activado'}")

    def update_mapper(self):
        """Actualiza el mapper cuando config.mapping cambia en tiempo real."""
        self.mapper = get_mapper(self.config)
        logger.info(f"Mapping cambiado a: {self.config.mapping}")

    def shutdown(self):
        """Libera recursos del mixer."""
        pygame.mixer.stop()
        pygame.mixer.quit()
        logger.info("AudioEngine apagado.")
