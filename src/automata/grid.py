"""
src/automata/grid.py
====================
Lógica del autómata celular.

Implementa Game of Life y variantes usando NumPy para eficiencia.
La operación clave es la convolución 2D con un kernel de vecindad Moore,
que cuenta vecinos vivos de todas las celdas simultáneamente en una sola
operación vectorizada —mucho más rápido que iterar celda a celda.

Reglas soportadas (notación B/S = Born/Survive):
    conway   → B3/S23      (Conway's Game of Life)
    highlife → B36/S23     (HighLife, produce replicadores)
    seeds    → B2/S         (Seeds: ninguna célula sobrevive)
    daynight → B3678/S34678 (Day & Night: simétrico vivo/muerto)
"""

import numpy as np
from scipy.signal import convolve2d
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Reglas en formato diccionario: born=[n vecinos], survive=[n vecinos]
RULES = {
    "conway":   {"born": [3],        "survive": [2, 3]},
    "highlife": {"born": [3, 6],     "survive": [2, 3]},
    "seeds":    {"born": [2],        "survive": []},
    "daynight": {"born": [3,6,7,8], "survive": [3,4,6,7,8]},
}

# Kernel de vecindad de Moore (8 vecinos, sin contar la celda central)
MOORE_KERNEL = np.array([
    [1, 1, 1],
    [1, 0, 1],
    [1, 1, 1]
], dtype=np.uint8)


class Grid:
    """
    Cuadrícula del autómata celular.

    Atributos
    ---------
    cells : np.ndarray (height × width, dtype=uint8)
        Estado actual. 1 = viva, 0 = muerta.
    generation : int
        Número de generación actual.
    population : int
        Número de celdas vivas.
    """

    def __init__(self, config: Config):
        self.config = config
        self.rows = config.grid_height
        self.cols = config.grid_width
        self.rule = RULES.get(config.rule, RULES["conway"])
        self.cells = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.generation = 0
        logger.info(f"Grid {self.rows}×{self.cols} | Regla: {config.rule}")

    # ── Propiedades ───────────────────────────────────────────────────────────

    @property
    def population(self) -> int:
        return int(self.cells.sum())

    @property
    def density(self) -> float:
        return self.population / (self.rows * self.cols)

    # ── Inicialización ────────────────────────────────────────────────────────

    def randomize(self, density: float = 0.25) -> None:
        """Población aleatoria con densidad dada [0.0, 1.0]."""
        self.cells = (np.random.rand(self.rows, self.cols) < density).astype(np.uint8)
        self.generation = 0
        logger.debug(f"Grid aleatorio | densidad={density:.0%} | población={self.population}")

    def clear(self) -> None:
        """Borra todas las celdas."""
        self.cells[:] = 0
        self.generation = 0

    def load_glider(self, offset: tuple = (1, 1)) -> None:
        """
        Inserta un glider (planeador) clásico de Conway.
        El glider es el oscilador más pequeño con desplazamiento.
        """
        r, c = offset
        pattern = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [1, 1, 1]
        ], dtype=np.uint8)
        self.cells[r:r+3, c:c+3] = pattern
        logger.debug(f"Glider insertado en ({r}, {c})")

    def load_pattern(self, pattern: np.ndarray, row: int, col: int) -> None:
        """Inserta un patrón arbitrario (array 2D) en la posición dada."""
        h, w = pattern.shape
        r2 = min(row + h, self.rows)
        c2 = min(col + w, self.cols)
        self.cells[row:r2, col:c2] = pattern[:r2-row, :c2-col]

    # ── Evolución ─────────────────────────────────────────────────────────────

    def step(self) -> None:
        """
        Avanza una generación aplicando las reglas B/S.

        Algoritmo:
        1. Convolución 2D del estado actual con el kernel Moore → cuenta
           vecinos vivos para cada celda (valor 0–8).
        2. Aplicar regla Born: celda muerta con n vecinos ∈ born → nace.
        3. Aplicar regla Survive: celda viva con n vecinos ∈ survive → vive.
        4. El resto muere o permanece muerta.

        'wrap' en convolve2d implementa condiciones de borde periódicas
        (la cuadrícula se "envuelve" como un toro).
        """
        neighbor_count = convolve2d(
            self.cells, MOORE_KERNEL, mode="same", boundary="wrap"
        )

        born = np.isin(neighbor_count, self.rule["born"]) & (self.cells == 0)
        survive = np.isin(neighbor_count, self.rule["survive"]) & (self.cells == 1)

        self.cells = (born | survive).astype(np.uint8)
        self.generation += 1

    def get_delta(self, prev_state: np.ndarray):
        """
        Calcula qué celdas nacieron y murieron respecto a prev_state.

        Retorna
        -------
        birth_mask : np.ndarray (bool)
            Celdas que NO existían antes y ahora sí.
        death_mask : np.ndarray (bool)
            Celdas que existían antes y ahora no.
        """
        birth_mask = (prev_state == 0) & (self.cells == 1)
        death_mask = (prev_state == 1) & (self.cells == 0)
        return birth_mask, death_mask

    # ── Edición interactiva ───────────────────────────────────────────────────

    def toggle_cell(self, row: int, col: int) -> None:
        """Alterna el estado de una celda (click de ratón)."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.cells[row, col] ^= 1

    def set_cell(self, row: int, col: int, state: int) -> None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.cells[row, col] = state

    # ── Análisis ─────────────────────────────────────────────────────────────

    def get_column_densities(self) -> np.ndarray:
        """
        Densidad de células vivas por columna, normalizada [0, 1].
        Útil para el mapping sonoro espacial (izquierda→derecha = grave→agudo).
        """
        return self.cells.mean(axis=0)  # shape: (cols,)

    def get_row_densities(self) -> np.ndarray:
        """Densidad por fila, normalizada [0, 1]."""
        return self.cells.mean(axis=1)  # shape: (rows,)

    def get_quadrant_densities(self) -> np.ndarray:
        """
        Divide la cuadrícula en 4 cuadrantes y retorna la densidad de cada uno.
        Útil para asignar timbre o canal a zonas del espacio.
        """
        r2, c2 = self.rows // 2, self.cols // 2
        return np.array([
            self.cells[:r2, :c2].mean(),   # top-left
            self.cells[:r2, c2:].mean(),   # top-right
            self.cells[r2:, :c2].mean(),   # bottom-left
            self.cells[r2:, c2:].mean(),   # bottom-right
        ])
