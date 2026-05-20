"""
CellularSonata - Autómata Celular con Sonificación en Tiempo Real
=================================================================
Punto de entrada principal del proyecto.

Arquitectura:
    main.py  →  orquesta los módulos
    src/automata/  →  lógica del autómata celular (Game of Life + variantes)
    src/audio/     →  síntesis de audio, mezcla, ADSR
    src/visual/    →  renderizado pygame, interfaz gráfica
    src/utils/     →  configuración, helpers, logging

Uso:
    python main.py
    python main.py --rule conway       # Game of Life estándar
    python main.py --rule highlife     # HighLife (B36/S23)
    python main.py --mapping musical   # Mapping sonoro musical
    python main.py --mapping spectral  # Mapping espectral experimental
"""

import sys
import argparse
import pygame
from src.automata.grid import Grid
from src.audio.engine import AudioEngine
from src.visual.renderer import Renderer
from src.visual.splash import SplashScreen
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="CellularSonata: Autómata celular con sonificación en tiempo real"
    )
    parser.add_argument(
        "--rule",
        choices=["conway", "highlife", "seeds", "daynight"],
        default="conway",
        help="Regla del autómata celular (default: conway)"
    )
    parser.add_argument(
        "--mapping",
        choices=["basic", "musical", "spectral"],
        default="musical",
        help="Estrategia de mapping sonoro (default: musical)"
    )
    parser.add_argument(
        "--width", type=int, default=80,
        help="Columnas de la cuadrícula (default: 80)"
    )
    parser.add_argument(
        "--height", type=int, default=60,
        help="Filas de la cuadrícula (default: 60)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = Config(
        grid_width=args.width,
        grid_height=args.height,
        rule=args.rule,
        mapping=args.mapping
    )

    logger.info(f"Iniciando CellularSonata | Regla: {config.rule} | Mapping: {config.mapping}")

    # Inicializar pygame para la splash (solo display, sin audio aún)
    pygame.init()

    # ── Pantalla de inicio ────────────────────────────────────────────────────
    # La splash muestra el autómata de fondo animado y permite elegir
    # regla y mapping antes de arrancar el simulador completo.
    splash = SplashScreen(config)
    if not splash.run():
        pygame.quit()
        logger.info("Salida desde la pantalla de inicio.")
        sys.exit(0)
    # config.rule y config.mapping ya fueron actualizados por la splash

    logger.info(f"Arrancando simulador | Regla: {config.rule} | Mapping: {config.mapping}")

    # Inicializar resto de subsistemas (audio después de splash para no bloquear)
    audio_engine = AudioEngine(config)
    grid = Grid(config)
    renderer = Renderer(config, grid)

    # Poblar con patrón inicial aleatorio (25% de densidad)
    grid.randomize(density=0.25)

    clock = pygame.time.Clock()
    running = True
    paused = False
    step_mode = False  # True = avanza un paso por tecla ESPACIO

    logger.info("Bucle principal iniciado. Controles en pantalla (tecla H).")

    while running:
        # ── Eventos ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                running, paused, step_mode = handle_keydown(
                    event, grid, audio_engine, config, running, paused, step_mode
                )

            elif event.type == pygame.MOUSEBUTTONDOWN:
                handle_mouse(event, grid, renderer)

            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0]:  # Arrastrar con botón izquierdo
                    handle_mouse(event, grid, renderer)

        # ── Lógica ───────────────────────────────────────────────────────────
        if not paused:
            prev_state = grid.cells.copy()
            grid.step()
            birth_mask, death_mask = grid.get_delta(prev_state)
            audio_engine.sonify(grid, birth_mask, death_mask)

        elif step_mode:
            prev_state = grid.cells.copy()
            grid.step()
            birth_mask, death_mask = grid.get_delta(prev_state)
            audio_engine.sonify(grid, birth_mask, death_mask)
            step_mode = False

        # ── Render ───────────────────────────────────────────────────────────
        renderer.draw(paused)
        pygame.display.flip()
        clock.tick(config.fps)

    # ── Limpieza ─────────────────────────────────────────────────────────────
    audio_engine.shutdown()
    pygame.quit()
    logger.info("CellularSonata cerrado correctamente.")
    sys.exit(0)


def handle_keydown(event, grid, audio_engine, config, running, paused, step_mode):
    """Gestiona todas las teclas. Centralizado para mantener main() limpio."""
    key = event.key

    if key == pygame.K_ESCAPE or key == pygame.K_q:
        running = False

    elif key == pygame.K_SPACE:
        if paused:
            step_mode = True       # Un paso en modo pausa
        else:
            paused = not paused    # Toggle pausa

    elif key == pygame.K_p:
        paused = not paused

    elif key == pygame.K_r:
        grid.randomize(density=0.25)

    elif key == pygame.K_c:
        grid.clear()

    elif key == pygame.K_g:
        grid.load_glider(offset=(5, 5))

    elif key == pygame.K_UP:
        config.fps = min(config.fps + 2, 60)

    elif key == pygame.K_DOWN:
        config.fps = max(config.fps - 2, 1)

    elif key == pygame.K_PLUS or key == pygame.K_EQUALS:
        audio_engine.adjust_volume(+0.05)

    elif key == pygame.K_MINUS:
        audio_engine.adjust_volume(-0.05)

    elif key == pygame.K_m:
        audio_engine.toggle_mute()

    elif key == pygame.K_1:
        config.mapping = "basic"
    elif key == pygame.K_2:
        config.mapping = "musical"
    elif key == pygame.K_3:
        config.mapping = "spectral"

    return running, paused, step_mode


def handle_mouse(event, grid, renderer):
    """Convierte posición del ratón a coordenada de celda y la alterna."""
    mx, my = pygame.mouse.get_pos()
    cell = renderer.pixel_to_cell(mx, my)
    if cell:
        col, row = cell
        grid.toggle_cell(row, col)


if __name__ == "__main__":
    main()
