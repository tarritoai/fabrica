# personajes/

Tus personajes y tu narrador, uno por carpeta: `personajes/<id>/personaje.json` (quién es, qué pieza lo dibuja y con
qué props, y su voz). Los crea `/personaje`. El narrador (`personajes/narrador/`) solo tiene voz.

Un guion usa a un personaje por su id: en `"voices": {"narrador": "narrador"}` y, si sale en pantalla, con su pieza
y sus props en los actores del plano. Su hoja de expresiones: `uv run reels personaje <id>` → `personajes/<id>/hoja.png`.
