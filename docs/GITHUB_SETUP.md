# Cómo publicar CellularSonata en GitHub profesionalmente

Sigue estos pasos en orden. El resultado será un repositorio que llama la atención
en entrevistas de trabajo y evaluaciones académicas.

---

## 1. Crear el repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre: `cellular-sonata` (minúsculas, con guión — es la convención estándar)
3. Descripción: `Real-time cellular automaton with procedural audio sonification · Python`
4. Visibilidad: **Public**
5. **NO** marques "Add a README" ni "Add .gitignore" — ya los tienes
6. Clic en **Create repository**

---

## 2. Subir el código desde terminal

```bash
cd cellular-sonata/          # Entra en la carpeta del proyecto

git init
git add .
git commit -m "feat: initial release — CA engine, three sonification strategies, interactive splash"

git branch -M main
git remote add origin https://github.com/TU_USUARIO/cellular-sonata.git
git push -u origin main
```

---

## 3. Grabar el GIF de demo (CRÍTICO para el README)

El GIF es lo primero que ve cualquier visitante. Sin él el README queda incompleto.

### Opción A — Kap (macOS, gratuito)
1. Descarga https://getkap.co
2. Ejecuta `python main.py`
3. Graba ~20 segundos: empieza con la splash, selecciona una regla, deja correr el autómata
4. Exporta como GIF, tamaño ~800×600, 15 fps
5. Guarda como `docs/demo.gif`

### Opción B — ScreenToGif (Windows, gratuito)
1. Descarga https://www.screentogif.com
2. Usa "Screen recorder" sobre la ventana de pygame
3. Exporta: Optimize → "Lossy GIF", escala a 800px de ancho

### Opción C — ffmpeg (cualquier sistema)
```bash
# Graba pantalla a mp4 primero (ajusta :0.0 al display correcto en Linux)
ffmpeg -video_size 800x660 -framerate 15 -f x11grab -i :0.0 demo.mp4

# Convierte a GIF optimizado
ffmpeg -i demo.mp4 -vf "fps=12,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" docs/demo.gif
```

### Subir el GIF
```bash
git add docs/demo.gif
git commit -m "docs: add demo GIF"
git push
```

---

## 4. Configurar el repositorio en GitHub (interfaz web)

### Topics (palabras clave — mejoran la visibilidad)
En la página del repo → ⚙ (junto a About) → Topics:
```
python  pygame  cellular-automata  game-of-life  sonification  
generative-music  procedural-audio  creative-coding  sonology
```

### Description y Website
- Description: `Real-time cellular automaton with procedural audio sonification · Python`
- Website: déjalo vacío o pon tu portfolio si tienes

### Activar GitHub Pages para la documentación (opcional pero profesional)
Settings → Pages → Source: `main` branch, folder `/docs`
Si añades un `docs/index.md` básico, tendrás una web de documentación gratuita.

---

## 5. Crear un Release v1.0

Los releases son como "versiones oficiales" del proyecto, muy valorados en portfolios.

1. En GitHub → Releases → "Create a new release"
2. Tag: `v1.0.0`
3. Title: `v1.0.0 — Initial release`
4. Description:
```
## CellularSonata v1.0.0

First stable release.

### Features
- Conway's Game of Life and three variant rules (HighLife, Seeds, Day & Night)
- Three independent sonification strategies (basic, musical, spectral)
- Pentatonic minor scale mapping with per-zone timbre selection
- ADSR envelope synthesis, anti-clipping polyphony management
- Interactive splash screen with animated background
- Real-time parameter control (rule, mapping, speed, volume)

### Requirements
Python 3.10+, pygame ≥ 2.5, numpy ≥ 1.24, scipy ≥ 1.11
```
5. Marca "Set as latest release"
6. Publish release

---

## 6. Añadir el GIF al README (si no lo hiciste antes)

El README ya tiene esta línea:
```markdown
![Demo animation](docs/demo.gif)
```
Solo necesitas que el archivo `docs/demo.gif` exista en el repo.

---

## 7. Checklist final antes de entregar

- [ ] `python main.py` arranca sin errores en una instalación limpia
- [ ] `pytest tests/ -v` pasa todos los tests
- [ ] El GIF de demo está en `docs/demo.gif` y se ve en el README
- [ ] Los badges del README muestran las versiones correctas
- [ ] Hay al menos un Release (v1.0.0)
- [ ] El repo tiene Topics configurados
- [ ] El README tiene sección de referencias académicas
- [ ] `LICENSE` existe
- [ ] `CONTRIBUTING.md` existe

---

## Por qué todo esto importa

Un repositorio GitHub bien cuidado demuestra:

- **Comunicación técnica** — el README explica el proyecto a alguien que no lo conoce
- **Reproducibilidad** — `requirements.txt` + instrucciones claras permiten ejecutarlo en cualquier máquina
- **Madurez de proceso** — commits descriptivos, releases, tests, licencia
- **Criterio de diseño** — el README explica *por qué* se tomaron las decisiones técnicas, no solo *qué* hace el código

Estos son exactamente los criterios que evalúan los recruiters técnicos y los tribunales académicos.
