"""
tests/test_grid.py
==================
Tests unitarios para el módulo de autómata celular.

Ejecutar con: pytest tests/
"""

import numpy as np
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.automata.grid import Grid
from src.utils.config import Config


@pytest.fixture
def small_config():
    """Configuración mínima para tests."""
    return Config(grid_width=10, grid_height=10, rule="conway")


@pytest.fixture
def grid(small_config):
    return Grid(small_config)


class TestGridInit:
    def test_initial_state_all_dead(self, grid):
        assert grid.cells.sum() == 0

    def test_dimensions(self, grid):
        assert grid.cells.shape == (10, 10)

    def test_generation_starts_at_zero(self, grid):
        assert grid.generation == 0


class TestGridPopulation:
    def test_randomize_increases_population(self, grid):
        grid.randomize(density=0.5)
        assert grid.population > 0

    def test_clear_zeroes_population(self, grid):
        grid.randomize(density=0.5)
        grid.clear()
        assert grid.population == 0

    def test_density_property(self, grid):
        grid.randomize(density=0.25)
        assert 0.0 <= grid.density <= 1.0


class TestConwayRules:
    """
    Casos conocidos del Game of Life para validar la implementación.
    """

    def test_underpopulation_kills(self, grid):
        """Una célula con menos de 2 vecinos muere."""
        grid.cells[5, 5] = 1  # Celda sola
        grid.step()
        assert grid.cells[5, 5] == 0

    def test_overcrowding_kills(self, grid):
        """Una célula con más de 3 vecinos muere."""
        # Centro con 4 vecinos
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(0,0)]:
            grid.cells[5+dr, 5+dc] = 1
        before = grid.cells[5, 5]
        grid.step()
        assert grid.cells[5, 5] == 0  # Muere por superpoblación (4 vecinos)

    def test_reproduction(self, grid):
        """Una celda muerta con exactamente 3 vecinos nace."""
        # 3 vecinos alrededor de (5,6)
        grid.cells[5, 5] = 1
        grid.cells[4, 6] = 1
        grid.cells[6, 6] = 1
        grid.step()
        assert grid.cells[5, 6] == 1  # Debería nacer

    def test_block_is_stable(self, grid):
        """El bloque 2×2 es un oscilador período 1 (estable)."""
        grid.cells[4:6, 4:6] = 1
        initial_pop = grid.population
        grid.step()
        assert grid.population == initial_pop
        assert grid.cells[4:6, 4:6].sum() == 4

    def test_blinker_period_2(self, grid):
        """El blinker tiene período 2."""
        # Blinker horizontal en (5, 4-6)
        grid.cells[5, 4] = 1
        grid.cells[5, 5] = 1
        grid.cells[5, 6] = 1

        grid.step()
        # Debería convertirse en blinker vertical
        assert grid.cells[4, 5] == 1
        assert grid.cells[5, 5] == 1
        assert grid.cells[6, 5] == 1

        grid.step()
        # Vuelve al horizontal
        assert grid.cells[5, 4] == 1
        assert grid.cells[5, 5] == 1
        assert grid.cells[5, 6] == 1

    def test_generation_increments(self, grid):
        grid.randomize()
        grid.step()
        assert grid.generation == 1
        grid.step()
        assert grid.generation == 2


class TestDelta:
    def test_get_delta_birth(self, grid):
        """Detecta correctamente nacimientos."""
        # Setup para que nazca (5,5): 3 vecinos
        grid.cells[4, 5] = 1
        grid.cells[6, 5] = 1
        grid.cells[5, 4] = 1

        prev = grid.cells.copy()
        grid.step()
        births, deaths = grid.get_delta(prev)

        assert births[5, 5] == True  # (5,5) nació

    def test_get_delta_death(self, grid):
        """Detecta correctamente muertes."""
        grid.cells[5, 5] = 1  # Sola, morirá
        prev = grid.cells.copy()
        grid.step()
        births, deaths = grid.get_delta(prev)

        assert deaths[5, 5] == True  # (5,5) murió


class TestColumnDensities:
    def test_shape(self, grid):
        grid.randomize(0.3)
        densities = grid.get_column_densities()
        assert densities.shape == (10,)

    def test_range(self, grid):
        grid.randomize(0.5)
        d = grid.get_column_densities()
        assert d.min() >= 0.0
        assert d.max() <= 1.0
