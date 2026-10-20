---
name: humo
description: Prueba de humo GRATIS - hace un vídeo de unos 6 s de punta a punta en tu computadora (guion, escena 3D, render, montaje y comprobación) con una voz ya grabada, sin cuentas ni claves. Sirve para saber que la fábrica funciona. Usar con "/humo", después de instalar o cuando algo deje de funcionar.
argument-hint: "[rapido|draft|preview]"
---

# /humo — tu primer vídeo feo (y gratis)

"Primero que funcione entero; luego, bonito." Español claro; a quien manda, de tú. **No gasta nada**: ni créditos
de voz, ni nube, ni claves.

## 1. Avisar
Di en 2 líneas qué va a pasar: "Voy a fabricar un vídeo de unos 6 segundos de punta a punta en tu computadora. Tarda
entre 2 y 15 minutos según la máquina; puedes mirar cómo avanza."

## 2. Lanzar
- Orden: `uv run reels humo --no-abrir` (y `--calidad draft` o `--calidad preview` si lo pidió; por defecto, la más
  rápida).
- Es largo: lánzalo en segundo plano si puedes y quédate con las últimas ~20 líneas.
- Los pasos que verás: 1 guion (revisión gratis) → 2 escena → 3 render → 4 montaje → 5 comprobación (la fábrica
  vuelve a escuchar el vídeo para ver que cada frase suena en su plano).

## 3. Si sale bien
- Termina con `✔ ¡La fábrica funciona!` y la ruta del vídeo: `episodes/humo/final.mp4`.
- Comprueba que existe y pesa algo (al menos 200 KB y 4 s: es lo que pide el lote 1·5) y ábrelo para quien manda con el comando de su sistema
  (macOS `open`, Windows `start ""`, Linux `xdg-open`).
- Explica en 3 líneas qué ha demostrado: que están bien Blender (el 3D), Remotion (el montaje), ffmpeg (el vídeo) y
  whisper (el oído que comprueba). La voz venía grabada: la de verdad llegará con ElevenLabs.
- Si sigue el curso: `/tarrito comprobar` sella el lote 1·5.

## 4. Si falla
1. No pegues el error entero: tradúcelo a una frase ("falta Blender", "no encuentra el modelo de whisper").
2. Ejecuta `uv run reels doctor` y lee las líneas con ✘: cada una trae el comando exacto para su sistema.
3. Casos típicos:
   - **falta el modelo de whisper** → `uv run reels descargar-modelo` (unos 470 MB) y otra vez `/humo`;
     o, para salir del paso, `uv run reels humo --no-abrir --sin-comprobar`;
   - **una pieza sin instalar** → el comando que da `doctor` (o `/fabrica:instalar`);
   - **máquina virtual o sin tarjeta gráfica** → `uv run reels humo --no-abrir --motor cycles` (más lento, pero va);
   - **se queda sin espacio** → el humo necesita ~1 GB libre.
4. Si después de eso sigue fallando, guarda las últimas 40 líneas en `logs/humo-error.txt` y dile que lo comparta
   en el canal de ayuda del curso (sin claves: el log no las lleva).
