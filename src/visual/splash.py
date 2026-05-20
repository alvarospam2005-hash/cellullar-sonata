"""
src/visual/splash.py  —  Pantalla de inicio de CellularSonata
Flechas dibujadas como polígonos pygame (sin depender de glifos Unicode).
"""

import pygame
import numpy as np
from scipy.signal import convolve2d
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_MOORE   = np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.uint8)
RULES    = ["conway", "highlife", "seeds", "daynight"]
MAPPINGS = ["basic", "musical", "spectral"]

BG     = (8,   12,  20)
CELL_C = (30, 160,  80)
WHITE  = (255, 255, 255)
GREEN  = (0,   210, 110)
GREY   = (155, 175, 165)
DIM    = (65,   85,  75)
SEL_BG = (12,   45,  28)
SEL_BR = (0,   150,  75)
UNSEL  = (95,  120, 108)


def draw_arrow_left(surf, cx, cy, size, color):
    """Triángulo apuntando a la izquierda, centrado en (cx, cy)."""
    pts = [(cx - size, cy), (cx + size, cy - size), (cx + size, cy + size)]
    pygame.draw.polygon(surf, color, pts)

def draw_arrow_right(surf, cx, cy, size, color):
    pts = [(cx + size, cy), (cx - size, cy - size), (cx - size, cy + size)]
    pygame.draw.polygon(surf, color, pts)

def draw_arrow_up(surf, cx, cy, size, color):
    pts = [(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)]
    pygame.draw.polygon(surf, color, pts)

def draw_arrow_down(surf, cx, cy, size, color):
    pts = [(cx, cy + size), (cx - size, cy - size), (cx + size, cy - size)]
    pygame.draw.polygon(surf, color, pts)


class SplashScreen:
    def __init__(self, config: Config):
        self.config      = config
        self.w           = config.window_width
        self.h           = config.window_height
        self.rule_idx    = RULES.index(config.rule)
        self.mapping_idx = MAPPINGS.index(config.mapping)

        self.bg_cols  = self.w // 10
        self.bg_rows  = self.h // 10
        self.bg_cells = (np.random.rand(self.bg_rows, self.bg_cols) < 0.30).astype(np.uint8)
        self._tick    = 0

        pygame.font.init()
        self.fT = pygame.font.SysFont("monospace", 46, bold=True)
        self.fL = pygame.font.SysFont("monospace", 24, bold=True)
        self.fS = pygame.font.SysFont("monospace", 18)

        self.screen = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption("CellularSonata")

    # ── Bucle ─────────────────────────────────────────────────────────────────

    def run(self) -> bool:
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    r = self._key(event.key)
                    if r is not None:
                        return r
            self._step_bg()
            self._draw()
            pygame.display.flip()
            clock.tick(15)

    def _key(self, key):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.config.rule    = RULES[self.rule_idx]
            self.config.mapping = MAPPINGS[self.mapping_idx]
            return True
        if key in (pygame.K_ESCAPE, pygame.K_q):
            return False
        if key == pygame.K_LEFT:
            self.rule_idx = (self.rule_idx - 1) % len(RULES)
        if key == pygame.K_RIGHT:
            self.rule_idx = (self.rule_idx + 1) % len(RULES)
        if key == pygame.K_UP:
            self.mapping_idx = (self.mapping_idx - 1) % len(MAPPINGS)
        if key == pygame.K_DOWN:
            self.mapping_idx = (self.mapping_idx + 1) % len(MAPPINGS)
        return None

    # ── Fondo animado ─────────────────────────────────────────────────────────

    def _step_bg(self):
        self._tick += 1
        if self._tick % 4 != 0:
            return
        nc   = convolve2d(self.bg_cells, _MOORE, mode="same", boundary="wrap")
        born = (nc == 3) & (self.bg_cells == 0)
        surv = np.isin(nc, [2, 3]) & (self.bg_cells == 1)
        self.bg_cells = (born | surv).astype(np.uint8)
        if self.bg_cells.sum() < self.bg_cols * self.bg_rows * 0.04:
            noise = (np.random.rand(self.bg_rows, self.bg_cols) < 0.12).astype(np.uint8)
            self.bg_cells = np.clip(self.bg_cells + noise, 0, 1).astype(np.uint8)

    # ── Helpers de render ─────────────────────────────────────────────────────

    def _draw_bg(self):
        px = 10
        for row, col in np.argwhere(self.bg_cells):
            alpha = 0.15 + 0.20 * ((row + col) % 5) / 4
            c = tuple(int(v * alpha) for v in CELL_C)
            pygame.draw.rect(self.screen, c, (col*px, row*px, px-1, px-1))

    def _blit_cx(self, surf, y):
        self.screen.blit(surf, surf.get_rect(centerx=self.w//2, top=y))

    def _render(self, text, font, color):
        return font.render(text, True, color)

    def _hline(self, y):
        pygame.draw.line(self.screen, DIM, (60, y), (self.w - 60, y), 1)

    # ── Secciones ─────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(BG)
        self._draw_bg()
        self._draw_title()
        self._draw_rule()
        self._draw_mapping()
        self._draw_controls()

    def _draw_title(self):
        self._blit_cx(self._render("CellularSonata", self.fT, GREEN), 28)
        self._blit_cx(self._render("Automata celular  -  Sonificacion en tiempo real",
                                   self.fS, GREY), 84)
        self._hline(116)

    def _draw_rule(self):
        cx, y0 = self.w // 2, 130
        self._blit_cx(self._render("REGLA", self.fS, DIM), y0)

        prev = RULES[(self.rule_idx - 1) % len(RULES)]
        cur  = RULES[self.rule_idx].upper()
        nxt  = RULES[(self.rule_idx + 1) % len(RULES)]

        s_prev = self._render(prev, self.fS, UNSEL)
        s_cur  = self._render(cur,  self.fL, WHITE)
        s_nxt  = self._render(nxt,  self.fS, UNSEL)

        arr_w  = 12          # Tamaño del triángulo (px desde centro)
        gap    = 24
        row_y  = y0 + 32
        mid_h  = s_cur.get_height()

        total = arr_w*2 + gap + s_prev.get_width() + gap + \
                s_cur.get_width() + gap + s_nxt.get_width() + gap + arr_w*2
        x = cx - total // 2

        # Flecha izquierda
        draw_arrow_left(self.screen, x + arr_w, row_y + mid_h//2, arr_w, GREEN)
        x += arr_w*2 + gap

        # Valor anterior
        self.screen.blit(s_prev, (x, row_y + (mid_h - s_prev.get_height())//2))
        x += s_prev.get_width() + gap

        # Valor actual con caja
        pad = 12
        box = pygame.Rect(x - pad, row_y - 4, s_cur.get_width() + pad*2, mid_h + 8)
        pygame.draw.rect(self.screen, SEL_BG, box, border_radius=6)
        pygame.draw.rect(self.screen, SEL_BR, box, 2, border_radius=6)
        self.screen.blit(s_cur, (x, row_y))
        x += s_cur.get_width() + gap

        # Valor siguiente
        self.screen.blit(s_nxt, (x, row_y + (mid_h - s_nxt.get_height())//2))
        x += s_nxt.get_width() + gap

        # Flecha derecha
        draw_arrow_right(self.screen, x + arr_w, row_y + mid_h//2, arr_w, GREEN)

        self._hline(row_y + mid_h + 16)

    def _draw_mapping(self):
        cx  = self.w // 2
        y0  = 230
        self._blit_cx(self._render("MAPPING SONORO", self.fS, DIM), y0)

        arr_sz = 10
        row_h  = 44

        # Flecha arriba
        draw_arrow_up(self.screen, cx, y0 + 28, arr_sz, GREEN)

        for i, opt in enumerate(MAPPINGS):
            ry = y0 + 46 + i * row_h
            if i == self.mapping_idx:
                s   = self._render(opt.upper(), self.fL, WHITE)
                box = s.get_rect(centerx=cx, top=ry-4).inflate(40, 10)
                pygame.draw.rect(self.screen, SEL_BG, box, border_radius=6)
                pygame.draw.rect(self.screen, SEL_BR, box, 2, border_radius=6)
                self._blit_cx(s, ry)
            else:
                s = self._render(opt, self.fS, UNSEL)
                self._blit_cx(s, ry + 6)

        bot = y0 + 46 + len(MAPPINGS) * row_h + 4
        draw_arrow_down(self.screen, cx, bot, arr_sz, GREEN)
        self._hline(bot + 20)

    def _draw_controls(self):
        cx = self.w // 2

        # Posición vertical: desde la última línea divisora hasta el borde
        last_line = self._last_line_y()
        avail     = self.h - last_line - 12

        # Dos bloques: controles de splash + controles de simulación
        splash_items = [
            ("Flechas izq/der", "cambiar regla"),
            ("Flechas arr/aba", "cambiar mapping"),
            ("ENTER",           "iniciar"),
            ("ESC",             "salir"),
        ]
        sim_items = [
            ("Flechas arr/aba", "velocidad (FPS)"),
            ("+ / -",           "volumen"),
        ]

        lh      = 30   # Altura de cada fila de control
        sep_h   = 28   # Altura del separador "en simulacion"
        block_h = len(splash_items)*lh + sep_h + len(sim_items)*lh
        y       = last_line + (avail - block_h) // 2

        for key, val in splash_items:
            sk = self._render(key,        self.fL, GREEN)
            sv = self._render("  " + val, self.fL, WHITE)
            total = sk.get_width() + sv.get_width()
            x = cx - total // 2
            self.screen.blit(sk, (x, y))
            self.screen.blit(sv, (x + sk.get_width(), y))
            y += lh

        y += 6
        sep = self._render("[ en simulacion ]", self.fS, DIM)
        self._blit_cx(sep, y)
        y += sep_h

        for key, val in sim_items:
            sk = self._render(key,        self.fS, GREEN)
            sv = self._render("  " + val, self.fS, GREY)
            total = sk.get_width() + sv.get_width()
            x = cx - total // 2
            self.screen.blit(sk, (x, y))
            self.screen.blit(sv, (x + sk.get_width(), y))
            y += lh

    def _last_line_y(self):
        y0  = 230
        bot = y0 + 46 + len(MAPPINGS) * 44 + 4
        return bot + 20
