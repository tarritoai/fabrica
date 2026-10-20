# episodes/

Tus episodios. Cada episodio es una carpeta `episodes/<slug>/` (el slug es un nombre corto en minúsculas con guiones,
p. ej. `mi-primer-reel`) con su `script.json`: el guion beat a beat, que es lo único que se versiona en git.
Todo lo demás (voces, escena 3D, fotogramas, vídeos, `estado.md`, `critica.md`) lo generan los comandos y se queda
en tu ordenador. Empieza vacía: el primero lo crea `/episodio`.

`humo/` es la prueba gratis de la fábrica: la regenera `uv run reels humo` cada vez (no la edites).
Los campos de `script.json` están explicados en `docs/piezas.md`.
