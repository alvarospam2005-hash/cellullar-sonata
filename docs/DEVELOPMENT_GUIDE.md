# Guía de Desarrollo: CellularSonata

Este documento explica el proyecto fase a fase, con la justificación técnica
de cada decisión. Está pensado para acompañar el código durante el desarrollo
y como documento para evaluación académica.

---

## FASE 1 — MVP (Semana 1)

**Objetivo**: Sistema funcional con autómata visual y audio básico.

### 1.1 El autómata celular con NumPy

El corazón del sistema es `Grid.step()` en `src/automata/grid.py`.

La evolución del autómata se reduce a contar vecinos para cada celda.
La implementación ingenua sería un doble bucle Python:

```python
# LENTO — no usar en producción
for row in range(self.rows):
    for col in range(self.cols):
        neighbors = count_neighbors(row, col)
        ...
```

Este enfoque tarda O(n·m) iteraciones Python puras. Para una cuadrícula
80×60 = 4800 celdas, a 10 FPS = 48000 iteraciones/segundo. En Python esto
es lento y la visualización se "congela".

La solución es **convolución 2D con NumPy/SciPy**:

```python
from scipy.signal import convolve2d
neighbor_count = convolve2d(self.cells, MOORE_KERNEL, mode="same", boundary="wrap")
```

`convolve2d` aplica el kernel (filtro 3×3 de unos) a toda la imagen a la vez,
usando código C optimizado internamente. El resultado es un array donde cada
valor es la suma de los vecinos de esa posición. Esto es **O(n·m) en C**,
unas 100× más rápido que el bucle Python.

`boundary="wrap"` implementa condiciones de borde periódicas: la cuadrícula
actúa como un toro (el borde derecho conecta con el izquierdo).

### 1.2 Audio básico con pygame.mixer

pygame.mixer requiere que los sonidos estén en formato int16 estéreo.
El flujo es:

1. `generate_sine(freq, duration, sr)` → array float64 en [-1, 1]
2. `apply_adsr(wave, config)` → suaviza los bordes
3. `wave_to_stereo_int16(wave, config)` → array int16 shape (n, 2)
4. `pygame.sndarray.make_sound(array)` → objeto `pygame.Sound`
5. `channel.play(sound)` → reproducción

**¿Por qué int16 y no float32?**  
pygame.mixer trabaja internamente con int16 (herencia de SDL). Si intentas
pasar float32 directamente, obtendrás ruido aleatorio. La conversión es:
`int16 = float64 * 32767`.

**¿Por qué ADSR?**  
Sin envolvente, las notas tienen inicio y fin abruptos. Una discontinuidad
en la señal digital produce un "clic" audible (Gibbs phenomenon en el dominio
del tiempo). El attack de 10ms es suficiente para eliminar el artefacto.

---

## FASE 2 — Mapping musical (Semana 1-2)

**Objetivo**: Hacer que el sistema "suene bien" con lógica musical.

### 2.1 Selección de escala

La escala pentatónica menor tiene 5 notas: C, Eb, F, G, Bb.
Sus intervalos son: menor 3ª, segunda mayor, segunda mayor, menor 3ª.
**No hay semitonos ni tritono** → cualquier combinación suena consonante.

Esto es crucial para generación automática. Una escala mayor o cromática
produciría disonnancias cuando el autómata activa celdas contiguas.

La implementación usa MIDI notes directamente, lo que permite transposición
sencilla: cambiar la nota base (ej. de C3=48 a D3=50) transpone toda la escala.

### 2.2 Control de amplitud por densidad

Cuando muchas celdas nacen simultáneamente, la suma de voces puede saturar.
La estrategia es asignar amplitud proporcional a `1/√n_voces`:

```python
base_amp = 0.5 / max(np.sqrt(n_voices), 1.0)
```

Esto mantiene la **potencia acústica** aproximadamente constante:
- 1 voz: amp = 0.5
- 4 voces: amp = 0.25 cada una → suma RMS ≈ igual a 1 voz
- 16 voces: amp = 0.125 cada una → suma RMS ≈ similar

La razón de usar √n en lugar de simplemente /n es la ley de adición de
potencias acústicas: la energía total es la suma de las energías individuales,
y la amplitud es la raíz de la energía.

### 2.3 Selección de voces de "borde"

En lugar de seleccionar nacimientos aleatoriamente, priorizamos los que están
en los **bordes de clústeres** (vecindad mixta). Una célula con 2-3 vecinos
está en el borde de una estructura; con 6-8 vecinos está en el interior.

```python
scores = np.abs(neighbor_count[positions[:, 0], positions[:, 1]] - 4)
```

Esta heurística hace que el sonido refleje la **actividad dinámica** del
autómata (expansión/contracción de estructuras) mejor que el interior
estático.

---

## FASE 3 — Mapping espectral (Semana 2)

**Objetivo**: Explorar un mapping más abstracto y experimental.

### 3.1 El concepto de "ecualizador vivo"

En el mapping espectral, la cuadrícula se divide en bandas verticales,
cada una mapeada a una frecuencia del rango audible (80Hz–3200Hz).
La densidad de cada banda controla si esa frecuencia está presente.

Conceptualmente: el autómata es un **ecualizador gráfico** donde las
columnas son bandas de frecuencia. Una estructura horizontal activa bandas
contiguas (tono complejo); una estructura dispersa activa frecuencias
separadas (acorde).

Las frecuencias de las bandas se distribuyen **logarítmicamente** (no
linealemente) porque la percepción auditiva de altura es logarítmica:
la octava entre 100-200Hz parece igual de "grande" que 1000-2000Hz.

### 3.2 Diferencia con mapping musical

El mapping musical es **discreto**: nacen células → suenan notas → silencio.
El mapping espectral es **continuo**: el estado actual define el espectro
de forma sostenida.

Esto produce texturas evolución lenta en lugar de eventos puntales,
adecuado para exploración textural y música de proceso.

---

## FASE 4 — Calidad y presentación (Semana 3)

### 4.1 Tests con pytest

El módulo `tests/` contiene tests unitarios para los componentes críticos:
- `test_grid.py`: valida reglas de Conway con casos conocidos (block, blinker)
- `test_synthesis.py`: valida que el audio generado está en rango correcto

Ejecutar: `pytest tests/ -v`

Los tests de autómata usan **estructuras conocidas** de la literatura
del Game of Life: el bloque 2×2 (estable) y el blinker (período 2)
son especificaciones formales de las reglas.

### 4.2 Arquitectura limpia

El principio arquitectónico central es la **separación de responsabilidades**:

- `grid.py` no sabe nada de audio ni de pygame
- `synthesis.py` no sabe nada del autómata ni de mapping
- `mapping.py` depende de `grid.py` (lectura) y `synthesis.py` (tipos)
- `engine.py` orquesta audio pero no toca la lógica del autómata
- `renderer.py` depende de `grid.py` (lectura) y `config.py`
- `main.py` orquesta todo

Esta estructura permite **probar cada módulo independientemente** y
facilita la extensión: añadir un nuevo tipo de onda, un nuevo mapping,
o una nueva regla de autómata sin tocar el resto.

---

## Errores comunes y soluciones

### "pygame.error: No available audio device"
El sistema no tiene salida de audio. Verificar que los auriculares/altavoces
estén conectados y que el sistema tenga drivers de audio.

### Audio muy ruidoso o distorsionado
Probablemente clipping. Reducir `master_volume` en `config.py` o aumentar
`max_voices` para que la amplitud por voz sea menor.

### Audio entrecortado
Aumentar `buffer_size` en `config.py`: cambiar 512 → 1024 → 2048.
A mayor buffer, más estabilidad pero más latencia.

### La cuadrícula es muy lenta (FPS bajos)
Reducir `grid_width`/`grid_height`, o desactivar las líneas de cuadrícula
(`show_grid_lines = False` en config.py).

### ImportError: No module named 'scipy'
Ejecutar: `pip install -r requirements.txt`

---

## Extensiones sugeridas para mayor nota

1. **Exportación MIDI**: guardar los SoundEvents como archivo MIDI usando music21.
   Permite analizar la "composición" generada en un DAW.

2. **Síntesis FM**: añadir un oscilador modulador a `synthesis.py`.
   Permite timbres mucho más ricos con poco coste computacional.

3. **Reglas personalizadas**: leer una cadena "B3/S23" de la línea de comandos
   y parsearla dinámicamente.

4. **Grabación de audio**: escribir los buffers de audio a un archivo WAV
   usando `scipy.io.wavfile.write()`.

5. **Análisis de estadísticas**: guardar población y densidad por generación
   en un CSV, visualizar con matplotlib la evolución temporal.
