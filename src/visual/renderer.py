"""
src/visual/renderer.py
======================
Renderizado visual con pygame.

Responsabilidades:
- Dibujar la cuadrícula del autómata
- Distinguir visualmente: vivas, muertas, recién nacidas, muriendo
- Mostrar HUD con información en tiempo real
- Mostrar ayuda de controles
- Coordinar transformación píxel ↔ celda (para input de ratón)

ESTRATEGIA DE RENDERIZADO:
============================
pygame.Surface.fill() es la operación más rápida para fondo.
Luego iteramos solo las celdas VIVAS (optimización: no dibujar muertos).
Para células recién nacidas/muriendo, necesitamos el estado anterior,
por eso main.py guarda prev_state antes de grid.step().

Para cuadrículas grandes (>100×80) la iteración Python pura puede ser lenta.
Optimización futura: pygame.surfarray para render vectorizado.
"""

import pygame
import numpy as np
from src.automata.grid import Grid
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

FONT_MONO = None   # Inicializado en __init__
FONT_SMALL = None


class Renderer:
    """
    Renderizador del estado del autómata.

    Parámetros
    ----------
    config : Config
        Configuración global del proyecto.
    grid : Grid
        Referencia a la cuadrícula (para acceso a estado en cada frame).
    """

    def __init__(self, config: Config, grid: Grid):
        self.config = config
        self.grid = grid

        # Crear ventana principal
        self.screen = pygame.display.set_mode(
            (config.window_width, config.window_height)
        )
        pygame.display.set_caption(config.window_title)

        # Superficies
        # La cuadrícula se dibuja en grid_surface y luego se blit a screen.
        # Esto permite efectos de post-proceso futuros (blur, fade, etc.)
        self.grid_surface = pygame.Surface(
            (config.window_width, config.grid_height * config.cell_size)
        )

        # Fuentes
        pygame.font.init()
        self.font_hud = pygame.font.SysFont("monospace", 13)
        self.font_help = pygame.font.SysFont("monospace", 11)

        # Estado del HUD
        self.show_help = False
        self.show_grid_lines = config.show_grid_lines

        # Cache de rectángulos por celda (evita recalcular cada frame)
        cs = config.cell_size
        self._cell_rects = {
            (row, col): pygame.Rect(col * cs, row * cs, cs - 1, cs - 1)
            for row in range(config.grid_height)
            for col in range(config.grid_width)
        }

        logger.info(f"Renderer inicializado | {config.window_width}×{config.window_height}px")

    # ── Dibujo principal ──────────────────────────────────────────────────────

    def draw(self, paused: bool = False):
        """
        Dibuja un frame completo.
        
        Orden: fondo → celdas → líneas de cuadrícula → HUD.
        """
        self._draw_grid()
        self._draw_hud(paused)

        if self.show_help:
            self._draw_help_overlay()

        # Blit grid_surface a pantalla principal
        self.screen.blit(self.grid_surface, (0, 0))

    def _draw_grid(self):
        """
        Dibuja todas las celdas.

        Solo iteramos las celdas VIVAS (las muertas = fondo ya pintado).
        Optimización: np.argwhere devuelve solo posiciones no-cero.
        """
        # Fondo
        self.grid_surface.fill(self.config.color_dead)

        # Líneas de cuadrícula (opcional, costoso en grids grandes)
        if self.show_grid_lines and self.config.cell_size >= 5:
            self._draw_grid_lines()

        # Celdas vivas
        alive_positions = np.argwhere(self.grid.cells == 1)
        color = self.config.color_alive
        for row, col in alive_positions:
            rect = self._cell_rects[(row, col)]
            pygame.draw.rect(self.grid_surface, color, rect)

    def _draw_grid_lines(self):
        """Dibuja líneas de la cuadrícula. Solo llamar si cell_size >= 5."""
        w = self.config.window_width
        h = self.config.grid_height * self.config.cell_size
        cs = self.config.cell_size
        c = self.config.color_grid

        for x in range(0, w, cs):
            pygame.draw.line(self.grid_surface, c, (x, 0), (x, h))
        for y in range(0, h, cs):
            pygame.draw.line(self.grid_surface, c, (0, y), (w, y))

    def _draw_hud(self, paused: bool):
        """
        Panel HUD inferior con estadísticas en tiempo real.
        """
        hud_y = self.config.grid_height * self.config.cell_size
        hud_rect = pygame.Rect(0, hud_y, self.config.window_width, self.config.hud_height)
        pygame.draw.rect(self.screen, (20, 20, 30), hud_rect)

        # Línea superior del HUD
        pygame.draw.line(
            self.screen, (60, 60, 80),
            (0, hud_y), (self.config.window_width, hud_y), 1
        )

        # Texto de estado
        state_str = "⏸ PAUSA" if paused else "▶ RUN"
        lines = [
            f"{state_str}  |  Gen: {self.grid.generation:05d}  |  "
            f"Población: {self.grid.population:04d}  |  "
            f"Densidad: {self.grid.density:.1%}",

            f"Regla: {self.config.rule}  |  "
            f"Mapping: {self.config.mapping}  |  "
            f"FPS: {self.config.fps}  |  "
            f"Vol: {self.config.master_volume:.0%}  |  "
            f"[H] Ayuda",
        ]

        colors = [(200, 230, 200), (150, 180, 200)]
        for i, (line, color) in enumerate(zip(lines, colors)):
            surf = self.font_hud.render(line, True, color)
            self.screen.blit(surf, (8, hud_y + 8 + i * 18))

        # Barra de densidad visual
        bar_x = self.config.window_width - 120
        bar_y = hud_y + 10
        bar_w = 100
        bar_h = 8
        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * self.grid.density)
        density_color = self._density_color(self.grid.density)
        if fill_w > 0:
            pygame.draw.rect(self.screen, density_color, (bar_x, bar_y, fill_w, bar_h))

    def _density_color(self, density: float) -> tuple:
        """Color de barra según densidad: verde (baja) → amarillo → rojo (alta)."""
        if density < 0.3:
            return (50, 200, 80)
        elif density < 0.6:
            return (200, 200, 50)
        else:
            return (200, 60, 60)

    def _draw_help_overlay(self):
        """
        Overlay semitransparente con todos los controles.
        """
        overlay = pygame.Surface(
            (self.config.window_width, self.config.grid_height * self.config.cell_size),
            pygame.SRCALPHA
        )
        overlay.fill((10, 10, 20, 200))  # RGBA: casi opaco
        self.screen.blit(overlay, (0, 0))

        controls = [
            ("CONTROLES", None),
            ("", None),
            ("ESPACIO",  "Pausar / Avanzar un paso (pausado)"),
            ("P",        "Pausar/reanudar"),
            ("R",        "Reiniciar aleatoriamente"),
            ("C",        "Limpiar cuadrícula"),
            ("G",        "Insertar glider"),
            ("↑ / ↓",    "Aumentar/reducir velocidad (FPS)"),
            ("+ / -",    "Subir/bajar volumen"),
            ("M",        "Silenciar audio"),
            ("1 / 2 / 3","Mapping: básico / musical / espectral"),
            ("H",        "Mostrar/ocultar esta ayuda"),
            ("Q / ESC",  "Salir"),
            ("", None),
            ("RATÓN",    "Click/arrastrar = toggle celdas"),
        ]

        x_key = 40
        x_val = 160
        y = 60

        for key, val in controls:
            if val is None:
                # Título o separador
                surf = self.font_hud.render(key, True, (200, 200, 100))
                self.screen.blit(surf, (x_key, y))
            else:
                k_surf = self.font_help.render(key, True, (150, 220, 150))
                v_surf = self.font_help.render(val, True, (200, 200, 200))
                self.screen.blit(k_surf, (x_key, y))
                self.screen.blit(v_surf, (x_val, y))
            y += 16

    # ── Utilidades ────────────────────────────────────────────────────────────

    def pixel_to_cell(self, px: int, py: int) -> tuple | None:
        """
        Convierte coordenadas de pantalla a (col, row) de celda.
        Retorna None si el click está fuera de la cuadrícula.
        """
        cs = self.config.cell_size
        grid_h = self.config.grid_height * cs

        if py >= grid_h:  # Click en HUD, ignorar
            return None

        col = px // cs
        row = py // cs

        if 0 <= row < self.config.grid_height and 0 <= col < self.config.grid_width:
            return (col, row)
        return None

    def toggle_help(self):
        self.show_help = not self.show_help

    def toggle_grid_lines(self):
        self.show_grid_lines = not self.show_grid_lines
