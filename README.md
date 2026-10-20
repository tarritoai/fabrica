# La fábrica (repo técnico)

Pipeline que convierte un guion (`script.json`) en un reel vertical animado en 3D, dirigido desde Claude Code:

```
script.json ─► voces (ElevenLabs) ─► tiempos + labios (whisper.cpp + Rhubarb) ─► escena 3D (Blender, sin ventana)
            ─► pantallas y montaje (Remotion) ─► mezcla y volumen (ffmpeg) ─► final.mp4
```

Funciona en Mac (Apple Silicon), Windows 10/11 nativo y Linux. Lo único que cuesta dinero son las voces
(ElevenLabs) y, opcionalmente, el render en una GPU alquilada (Vast.ai). Todo lo demás es local y gratis.

## Instalar (alumnos)

En Claude Code (2.1.275 o posterior), abierto en la carpeta vacía que será tu fábrica (`C:\fabrica` en Windows,
`~/fabrica` en Mac y Linux):

```
/plugin install fabrica --marketplace tarritoai/fabrica
/fabrica:instalar
```

`/fabrica:instalar` elige contigo la carpeta de tu fábrica, instala todo **sin contraseñas de administrador** y
termina con tu primer vídeo. Si algo falla: `/fabrica:tarrito` y pega el error. Detalle del plugin y de la ruta sin
git: [`plugin/README.md`](plugin/README.md).

## Estructura

```
fabrica/
├── plantilla/          el proyecto que se copia a la carpeta del alumno (su fábrica, versionada con git)
│   ├── reels/          CLI en Python (`uv run reels …`): schema, lint, voz, timeline, build, render, compose, check
│   │   ├── system.py   TODO lo que depende del sistema operativo (rutas, binarios, abrir archivos, UTF-8, no dormir)
│   │   ├── cast.py     capa de reparto: nombres del alumno → ids internos del 3D
│   │   ├── doctor.py   revisión por SO con el comando exacto para arreglar cada cosa
│   │   └── smoke.py    prueba de humo gratis + prueba de velocidad de render
│   ├── blender/        escena 3D 100 % por código (corre dentro de Blender, solo stdlib + bpy)
│   ├── remotion/       pantallas de móvil/portátil, subtítulos y montaje final (fuentes incluidas, sin red)
│   ├── assets/         personajes, efectos (CC0), muebles Kenney (CC0), marca vacía, audio del humo
│   │   └── LICENCIAS.md  qué se incluye, con qué licencia, y qué se quedó fuera y por qué
│   ├── reparto.json    cómo se llaman los personajes en los guiones del alumno
│   ├── docs/ style/    referencia de piezas + plantillas de memoria (hipótesis, decisiones, guía de estilo…)
│   ├── ideas/ metrics/ reviews/ references/ episodes/   vacías, con un README de qué irá ahí
│   ├── .claude/        skills y agentes DEL PROYECTO (/episodio, /ideas, /revision, /referencias, /calibrar…)
│   ├── CLAUDE.md       instrucciones para Claude Code (responde en español, qué cuesta dinero…)
│   └── tests/          pytest: multiplataforma, reparto, schema, lint, doctor
├── .claude-plugin/     marketplace «tarritoai» (marketplace.json) y su variante sin git (marketplace-sin-git.json)
├── plugin/             plugin de Claude Code: /fabrica:instalar, /fabrica:tarrito, /fabrica:actualizar
│   └── scripts/        el instalador (fabrica.sh / fabrica.ps1 → fabrica.py, solo biblioteca estándar)
├── tests/              tests del instalador (sin red: un servidor local simula las descargas)
├── .github/workflows/  CI: valida el plugin e instala de verdad en Windows, macOS (arm64) y Ubuntu 22.04/24.04
└── tools/              mantenimiento del repo (no va al alumno): gen_sfx.py (efectos CC0), gen_errores.py (tabla
                        de errores), check_version_bump.py (CI), empaquetar.py (zip del plugin sin git)
```

Por qué así: las skills de un plugin se invocan con espacio de nombres (`/fabrica:x`) y sus agentes ignoran
`permissionMode`/hooks; además el sistema aprende escribiendo en sus propios archivos (`docs/`, agentes que
`/calibrar` reescribe). Por eso las skills y agentes del día a día viven en `plantilla/.claude/` (nombres cortos,
editables por el alumno) y el plugin solo instala, tutoriza y actualiza. El código también vive en la plantilla:
el curso enseña a añadir piezas (editar `schema.py`, `blender/`, `remotion/`), y `node_modules`, `.venv`, el modelo
de whisper y la caché de voces (dinero) no deben reinstalarse con cada actualización del plugin.

## Probarlo (desde `plantilla/`)

```bash
uv sync                              # Python 3.12 + dependencias (uv descarga Python si hace falta)
(cd remotion && npm ci)              # Remotion
uv run reels descargar-modelo        # modelo de whisper (~470 MB) a models/
uv run reels doctor                  # todo en verde; si no, el comando exacto para tu SO
uv run reels humo                    # vídeo de 7 s de punta a punta, gratis, sin cuentas → episodes/humo/final.mp4
uv run pytest -q                     # tests (no usan servicios de pago)
```

Para CI o máquinas sin GPU: `uv run reels humo --no-abrir --motor cycles` (Cycles en CPU en vez de EEVEE, calidad
mínima). `uv run reels doctor --json` da el estado en JSON y `--prueba-render` mide cuánto tardaría un reel de 30 s
y recomienda horno local o alquilado.

## Decisiones de diseño multiplataforma (P0)

- **Un solo sitio para el SO**: `reels/system.py`. Programas: variable en `.env` (`BLENDER_BIN`, `FFMPEG_BIN`,
  `RHUBARB_BIN`, `WHISPER_BIN`…) → PATH (al que se añaden `tools/`, `tools/<x>/`, `~/.local/bin` y
  `~/.local/opt/*/bin` en Linux, Homebrew en Mac) → rutas típicas de Blender por SO.
- **Nada de shell**: todos los subprocesos van con listas de argumentos (rutas con espacios y tildes, como
  `C:\Users\María José\fabrica`, viajan intactas). Remotion se lanza con `node …/remotion-cli.js` (no `npx`, que en
  Windows es un `.cmd`), y sus props siempre en archivo (también la portada).
- **UTF-8 explícito** en toda lectura/escritura de texto y en la salida de subprocesos (whisper en Windows); la
  consola se reconfigura a UTF-8 (Claude Code lee la salida por una tubería) y los hijos heredan `PYTHONUTF8=1`.
  Un test estático impide que vuelva a entrar código sin `encoding`.
- `os.devnull` en vez de `/dev/null` (ssh a Vast desde Windows); el script que reubica las pantallas en la nube
  entiende rutas `C:\…`.
- Abrir resultados con el abridor del SO (`os.startfile` / `open` / `xdg-open`), sin fallar si no hay.
- `requires-python >=3.12` (el código usa f-strings de 3.12) + `.python-version`.
- ffmpeg ≥ 7 comprobado por la opción real que hace falta (`afir … irnorm`), no solo por el número de versión.
- Rhubarb con `-r phonetic` (el reconocedor por defecto solo sabe inglés); comprobado con un test.
- El render pide al SO que no se duerma (`caffeinate` / `SetThreadExecutionState` / `systemd-inhibit`).
- Fuentes de Remotion incluidas (OFL): el montaje ya no depende de Google Fonts (fallaba por timeout).

## Reparto por papeles

El 3D está construido alrededor de dos *huecos* con ids internos fijos: `novato` (papel **humano**) y `claude` (papel
**cosa**), en ~90 sitios de `blender/`. Desde P1 el hueco no dice quién lo ocupa: `reels/cast.py` resuelve, por guion,
qué personaje interpreta cada papel (`reparto.json` por defecto → `reparto` del guion → inferencia desde `characters`:
el primer humano y la primera cosa listados) y lo escribe en `Episode.reparto` y en `timeline["cast"]`; Blender
(`lib.character_meta`, `build_scene.load_character`) construye el cuerpo del intérprete en el hueco. Los personajes son
datos (`personajes/<id>/personaje.json` o `assets/characters/<id>/character.json`) y el enum `Character` se amplía al
importar con las carpetas que existan. Renombrar los huecos (codemod `novato`→`humano`) sigue siendo posible, pero ya
no hace falta para que cualquier alumno use a sus personajes; las regresiones se comprueban con
`tools/visual_diff.py` (fotogramas del humo antes/después, idénticos píxel a píxel) y `tools/regresion_humo.sh`
(compara el humo con la referencia revisada a ojo de `tools/regresion/humo/`). Las piezas de la marca (tarro,
cuarto-isla, mundo) viven en `marca/` y no se distribuyen (ver `marca/README.md`).

Constructor "objeto con cara": `blender/rigs/thing.py` (10 formas, cara proyectada sobre la superficie con párpados,
cejas y bocas por visemas, parte que actúa con `act_poses`, luz de la lámpara). Decorados genéricos:
`blender/sets_generic.py` (`estudio`, `mostrador`, `exterior`). Hoja de expresiones: `reels personaje <id>`.
Detalle técnico: `curso/investigacion/fabrica-p1-generalidad.md` (en el repo del curso).

## Identidad de los commits
Este repo se publicará como `tarritoai/…`: los commits van siempre como `tarritoai <noreply@tarritoai.invalid>`
(configurado en local con `git config user.name/user.email`).
