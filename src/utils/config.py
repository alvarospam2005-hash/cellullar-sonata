"""
src/utils/config.py
===================
Configuración centralizada del proyecto.

Centralizar aquí TODOS los parámetros evita magic numbers dispersos
por el código. Facilita también cambiar configuración sin tocar lógica.
"""

from dataclasses import dataclass, field
from typing import Tuple, List


@dataclass
class Config:
    # ── Cuadrícula ────────────────────────────────────────────────────────────
    grid_width: int = 80          # Columnas
    grid_height: int = 60         # Filas
    rule: str = "conway"          # Regla del autómata

    # ── Visual ────────────────────────────────────────────────────────────────
    cell_size: int = 10           # Píxeles por celda
    fps: int = 10                 # Generaciones por segundo
    window_title: str = "CellularSonata"
    color_alive: Tuple[int,int,int] = (0, 220, 130)    # Verde neón
    color_dead: Tuple[int,int,int] = (15, 15, 25)      # Negro azulado
    color_newborn: Tuple[int,int,int] = (255, 255, 200) # Amarillo claro (recién nacidas)
    color_dying: Tuple[int,int,int] = (180, 60, 60)    # Rojo (muriendo)
    color_grid: Tuple[int,int,int] = (30, 30, 40)      # Líneas de cuadrícula
    show_grid_lines: bool = True
    hud_height: int = 60          # Píxeles del panel HUD inferior

    # ── Audio ─────────────────────────────────────────────────────────────────
    sample_rate: int = 44100      # Hz estándar CD
    buffer_size: int = 512        # Muestras por buffer (↓ = menos latencia, ↑ = más estable)
    channels: int = 2             # Estéreo
    max_voices: int = 8           # Voces simultáneas máximas (previene polifonía excesiva)
    master_volume: float = 0.6    # Volumen maestro [0.0, 1.0]
    mapping: str = "musical"      # Estrategia de sonificación

    # ── Síntesis ─────────────────────────────────────────────────────────────
    adsr_attack: float = 0.01     # segundos
    adsr_decay: float = 0.05      # segundos
    adsr_sustain: float = 0.7     # nivel [0.0, 1.0]
    adsr_release: float = 0.15    # segundos
    note_duration: float = 0.3    # Duración base de nota en segundos

    # ── Mapping musical (escala pentatónica menor por defecto) ────────────────
    # MIDI notes: C4=60, D4=62, Eb4=63, G4=67, Bb4=70, C5=72...
    scale_midi: List[int] = field(default_factory=lambda: [
        48, 51, 53, 55, 58,   # C3 pentatónica menor
        60, 63, 65, 67, 70,   # C4 pentatónica menor
        72, 75, 77, 79, 82,   # C5 pentatónica menor
    ])

    # ── Propiedades calculadas ────────────────────────────────────────────────
    @property
    def window_width(self) -> int:
        return self.grid_width * self.cell_size

    @property
    def window_height(self) -> int:
        return self.grid_height * self.cell_size + self.hud_height
