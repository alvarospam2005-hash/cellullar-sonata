# Contributing to CellularSonata

Contributions are welcome. The codebase is intentionally modular so that most additions touch a single file.

## Where to add things

| What you want to add | Where |
|----------------------|-------|
| New CA rule | `src/automata/grid.py` → `RULES` dict |
| New waveform | `src/audio/synthesis.py` → new `generate_*` function, then register in `src/audio/engine.py` → `GENERATORS` |
| New sonification strategy | `src/audio/mapping.py` → new class, register in `get_mapper()` |
| New visual element | `src/visual/renderer.py` → new `_draw_*` method |
| New config parameter | `src/utils/config.py` → add field to `Config` dataclass |

## Code style

- Follow the existing docstring format (module-level + class-level + method-level).
- No magic numbers — all constants belong in `config.py` or as named module-level variables.
- New audio functions must be tested in `tests/test_synthesis.py`.
- New CA rules must be validated against a known pattern in `tests/test_grid.py`.

## Running tests before submitting

```bash
pytest tests/ -v
```

All tests must pass.
