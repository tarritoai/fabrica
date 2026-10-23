---
name: nave
description: Instala la segunda fábrica del curso, la «nave de enfrente» - una fábrica de reels 2D «¿Y si…?» (dibujo por código, narrador de ElevenLabs, contador) que no necesita Blender ni tarjeta gráfica - en su propia carpeta, al lado de la fábrica 3D si ya existe (reutiliza lo que ya está descargado), sin contraseñas de administrador, y termina con su primer reel de prueba gratis. Úsala cuando el alumno escriba /fabrica:nave, /fabrica:instalar 2d, pida la fábrica 2D o la de «¿Y si…?», o llegue al lote A·2 del curso.
argument-hint: "[carpeta para la nave]"
allowed-tools:
  - Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" *)
  - Bash(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - PowerShell(powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" *)
  - Read
---

# Abrir la nave de enfrente (la fábrica 2D)

Llevas de la mano a alguien que quizá ya instaló su fábrica 3D (o no) y que no sabe de terminales. Objetivo: su
nave 2D funcionando y su primer reel 2D abierto en pantalla, sin sustos. **Es la misma receta que su fábrica**: una
carpeta, unas reglas, unos trabajadores, unas puertas, una voz. Cambia el motor: aquí se dibuja por código.

## Reglas (no se negocian)
Las mismas de `/fabrica:instalar` (léelas si no las tienes presentes: `${CLAUDE_PLUGIN_ROOT}/skills/instalar/SKILL.md`,
apartado «Reglas»): español llano y frases cortas; **solo** el comando FABRICA de abajo (nada de `apt`, `brew`,
`winget`, `npm -g`…); nunca `sudo` ni contraseñas; **nunca pidas ni enseñes claves**; todo se puede repetir.

## El comando FABRICA
- **Mac y Linux:** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh" PASO [opciones]`
- **Windows** (da igual Git Bash o PowerShell):
  `powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1" PASO [opciones]`
Tiempo máximo de la herramienta (600000 ms) en cada paso; `herramientas`, `dependencias` y `humo`, **en segundo
plano** (run_in_background), esperando el aviso. `--proyecto` siempre entre comillas dobles y sin barra al final.
Si un paso falla, termina con «✘ … Qué hacer … (código del error: …)»: explícalo en llano, repite el paso o busca el
código en `${CLAUDE_PLUGIN_ROOT}/skills/tarrito/errores-conocidos.md`.

## Pasos

### 0. Bienvenida (no ejecutes nada todavía)
En 3–4 líneas: vamos a abrir una segunda fábrica, de reels 2D («¿Y si…?»), en **otra carpeta** (la tuya no se toca);
no necesita Blender ni tarjeta gráfica; si ya tienes la fábrica 3D, reutiliza lo descargado y tarda 5–15 minutos;
si no, 20–40 (unos 700 MB de descargas). Sin contraseñas. Al final verás tu primer reel 2D. ¿Empezamos?

### 1. ¿Dónde vive la nave?
1. `FABRICA sistema --tipo 2d` → resume en una línea. Si sale «✘» en los bloqueos, explícalo con cariño y para.
2. Propón la carpeta: la que escribió al llamar a la skill (`$ARGUMENTS`, quitando un «2d» si lo puso) o la
   recomendada (`C:\nave-2d` en Windows, `nave-2d` en su carpeta personal en Mac y Linux: **al lado** de `fabrica`).
   Nunca dentro de la fábrica 3D ni en OneDrive / iCloud / Dropbox. **Espera su respuesta.**
3. `FABRICA sistema --tipo 2d --carpeta "CARPETA"`. Los «✘», explícalos; los «!» son avisos.

### 2. Preparar la carpeta (segundos)
`FABRICA preparar --tipo 2d --proyecto "CARPETA"` → copia la nave (código, trabajadores, órdenes, ejemplo) y la
apunta junto a su fábrica 3D (para que `/tarrito comprobar` encuentre los lotes del módulo en las dos).

### 3. Las herramientas
`FABRICA herramientas --proyecto "CARPETA"` (en segundo plano). Son cuatro: **ffmpeg** (montaje de vídeo y sonido),
**whisper** (el «oído»), su **modelo** y **Node** (el dibujo y el montaje). Si ya tiene la fábrica 3D, las coge de
allí **sin descargar nada** («reutilizado de tu otra fábrica»). Si se corta, se repite igual: sigue donde se quedó.
En Mac, los avisos `mac-rosetta` / `mac-sin-herramientas` se resuelven como en `/fabrica:instalar` (paso 3).

### 4. Las piezas de Python y del dibujo (2–5 minutos)
`FABRICA dependencias --proyecto "CARPETA"` (en segundo plano).

### 5. Revisión
`FABRICA doctor --proyecto "CARPETA"`. Todo en ✔ = listo (la clave de ElevenLabs vacía es normal hoy). Con «✘», no
ejecutes los comandos de la flecha →: repite el paso de esta skill que toca esa pieza (p. ej.
`FABRICA herramientas --proyecto "CARPETA" --solo ffmpeg --forzar`).

### 6. Su primer reel 2D (menos de un minuto)
`FABRICA humo --proyecto "CARPETA" --abrir` (en segundo plano). Mientras, cuéntale: guion revisado → voz ya grabada
(gratis) → dibujo de cada fotograma → música y efectos → el «oído» comprueba cada frase. Al acabar se abre solo; si
no, `FABRICA abrir video --proyecto "CARPETA"`. Celébralo: «esto también ha salido de tu computadora».

### 7. La clave de ElevenLabs (pregunta antes)
Si tiene la fábrica 3D con su clave: «¿Uso en la nave la misma clave de ElevenLabs que tu fábrica 3D? No la verás
ni la veré: se copia de un archivo a otro.» Si dice que sí: `FABRICA clave --proyecto "CARPETA"`. Si no tiene, la
pegará más adelante en su `.env` (`FABRICA abrir env --proyecto "CARPETA"`); hoy no hace falta.

### 8. Cierre: abrir Claude en la nave
Igual que con su fábrica: Claude se abre **dentro de la carpeta de la nave** para tener sus órdenes (`/episodio`,
`/personaje`, `/humo`…).
- **Windows 11:** Explorador → su carpeta (`C:\nave-2d`) → clic derecho en un hueco → «Abrir en Terminal» → `claude`.
  **Windows 10:** Mayúsculas + clic derecho → «Abrir la ventana de PowerShell aquí» → `claude`.
- **Mac:** Terminal → `cd ~/nave-2d` → `claude`. **Linux:** clic derecho → «Abrir en una terminal» → `claude`.
Lo primero allí, gratis: `uv run reels ejemplo quijote-gafas` (el reel de ejemplo entero, con sus voces ya grabadas).
Si sigue el curso: `/tarrito comprobar A·2`. Que cierre esta conversación (`/exit`) y abra la nueva.

## Reparar o repetir
Todo es seguro de repetir: lo que está bien no se toca. `FABRICA estado --proyecto "CARPETA"` dice qué hay; el
registro completo está en `CARPETA/logs/instalacion.log`. Para actualizarla más adelante: `/fabrica:actualizar`
desde la carpeta de la nave.
