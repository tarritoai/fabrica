# Plugin `fabrica` (Claude Code)

Instalación en un paso, dentro de Claude Code (versión 2.1.275 o posterior):

```
/plugin install fabrica --marketplace tarritoai/fabrica
```

Después, `/fabrica:instalar`. Desde la terminal, sin abrir Claude: `claude plugin install fabrica --marketplace
tarritoai/fabrica` (2.1.292+). Sin git en el ordenador (Windows sin Git for Windows): ver «Sin git» abajo.

## Qué trae

Solo lo que vive **fuera** del proyecto del alumno; las skills y agentes del día a día (`/episodio`, `/ideas`,
`/revision`…) vienen en la plantilla (`plantilla/.claude/`), editables por el alumno y por `/calibrar`.

| Skill | Qué hace |
|---|---|
| `/fabrica:instalar [carpeta]` | Comprueba el ordenador, propone una carpeta corta (sin OneDrive ni tildes), copia la plantilla, descarga las herramientas en esa carpeta **sin permisos de administrador** (Blender 5.2.2, ffmpeg ≥ 7, whisper.cpp 1.9.5 + modelo `ggml-small`, Rhubarb 1.14.0, Node 24 LTS; uv con su instalador oficial), `uv sync` + `npm ci`, `reels doctor` y el primer vídeo (`reels humo`). Ofrece activar las actualizaciones automáticas y `language: spanish`. |
| `/fabrica:tarrito [comprobar [lote] \| error]` | Tutor: diagnostica un error pegado con la tabla de errores conocidos (funciona antes de que haya nada instalado), traduce pantallas en inglés y, con `comprobar 1·5`, revisa el entregable de una lección. Comprobador hay uno, el del proyecto (`plantilla/.claude/skills/tarrito/comprobar.py` + `plantilla/curso/comprobaciones.json`, sellos en `curso/progreso.json`): con la fábrica instalada, `comprobar` delega en él (dentro de la fábrica la orden es `/tarrito comprobar [lote]`); antes de instalar solo mira los lotes 0·2, 1·1 y 1·3, sin sellar. |
| `/fabrica:nave [carpeta]` | Abre la **segunda fábrica**, la 2D «¿Y si…?» (`plantilla-2d/`), en su propia carpeta (`~/nave-2d`, `C:\nave-2d`): sin Blender, Rhubarb ni gráfica (ffmpeg, whisper + modelo, Node). Si ya hay una fábrica 3D en esta computadora, **reutiliza** sus herramientas y su modelo (enlaces duros: sin descargar ni ocupar el doble) y, con permiso, su clave de ElevenLabs (`clave`, sin mostrarla). Termina con su humo 2D. También `/fabrica:instalar 2d`. |
| `/fabrica:actualizar` | Trae la plantilla nueva con una regla de 3 vías por archivo: lo que el alumno cambió se queda; su memoria (`docs/` de lo aprendido, `ideas/`, `episodes/`, `style/`, marca, reparto) no se toca nunca; copia de seguridad en `.fabrica/copias/`. |

Las skills no improvisan comandos: llaman a `scripts/fabrica.sh` (Mac/Linux) o `scripts/fabrica.ps1` (Windows), que
instalan `uv` si falta y ejecutan `scripts/fabrica.py` (solo biblioteca estándar de Python). Cada paso es repetible:
las descargas se reanudan donde se cortaron, se comprueban con SHA-256 y quedan apuntadas en el `.env` del
proyecto (`BLENDER_BIN`, `FFMPEG_BIN`…), que es lo primero que mira `reels/system.py`.

```
fabrica.sh sistema [--tipo 2d] [--carpeta DIR]   ¿sirve este ordenador y esta carpeta?
fabrica.sh preparar [--tipo 2d] --proyecto DIR   copia la plantilla 3D (o la 2D) (no pisa nada)
fabrica.sh herramientas --proyecto DIR [--solo blender,ffmpeg,whisper,modelo,rhubarb,node,emojis] [--forzar]
fabrica.sh dependencias --proyecto DIR       uv sync + npm ci + navegador de Remotion
fabrica.sh doctor --proyecto DIR             uv run reels doctor
fabrica.sh humo --proyecto DIR [--motor cycles] [--sin-comprobar] [--abrir]
fabrica.sh todo [--tipo 2d] --proyecto DIR [--hasta PASO] todos los pasos seguidos (CI)
fabrica.sh clave --proyecto DIR [--desde OTRA]   la misma clave de ElevenLabs que otra fábrica tuya (sin mostrarla)
fabrica.sh ajustes [--auto-update] [--idioma spanish] [--estado]
fabrica.sh actualizar --proyecto DIR [--aplicar]
fabrica.sh comprobar [LOTE] [--respuesta "…"] --proyecto DIR
fabrica.sh diagnosticar "TEXTO" | --archivo LOG | --codigo ID
fabrica.sh estado --proyecto DIR · fabrica.sh abrir video|carpeta|env --proyecto DIR
```

Cada proyecto guarda su tipo en `.fabrica/plantilla.json` (`"tipo": "3d" | "2d"`): después de `preparar`, los demás
pasos (herramientas, humo, actualizar) saben de qué fábrica se trata. Las fábricas de una computadora se apuntan en
`<caché>/../fabricas.json`, y cada una lleva en `.fabrica/naves.json` dónde está la otra (lo usa el comprobador del
curso para los lotes A·1–A·5, que se pueden comprobar desde cualquiera de las dos).

## Dónde está la plantilla

El plugin se copia a la caché de Claude Code sin las carpetas `plantilla/` y `plantilla-2d/` (están fuera de `plugin/`).
El instalador busca la que toca, por orden: `plugin/plantilla` (zip sin git) → `../plantilla` (marketplace local / clon del repo) → el clon del
marketplace que guarda Claude Code (`plugins/known_marketplaces.json` → `installLocation`) → descarga de GitHub de la
etiqueta `fabrica--v<versión>` (o `main`). Gana la versión más alta.

## Sin git

Claude Code necesita `git` para añadir un marketplace de GitHub (`Executable not found in $PATH: "git"`). Para esos
ordenadores existe `.claude-plugin/marketplace-sin-git.json`, cuyo plugin es un zip (`dist/fabrica-plugin.zip`, con la
plantilla dentro) que la CI sube a cada release `fabrica--v*`:

```
/plugin install fabrica --marketplace https://raw.githubusercontent.com/tarritoai/fabrica/main/.claude-plugin/marketplace-sin-git.json
```

## Versión

`.claude-plugin/plugin.json` lleva una versión semántica que **hay que subir** en cada cambio de `plugin/` (la CI lo
exige): los alumnos solo reciben una copia nueva del plugin cuando cambia. Publicar: subir la versión, fusionar en
`main` y crear la etiqueta `fabrica--vX.Y.Z` (`claude plugin tag plugin` la crea comprobando que todo coincide).
