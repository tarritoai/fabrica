# metrics/

Los números de tus reels publicados. Empieza vacío: lo rellenan los comandos de la fábrica.

- `instagram.jsonl` — métricas de cada reel (visitas, % que se va en <3 s, compartidos, guardados…), con `uv run reels stats`.
- `account.jsonl` — cuánta gente sigue la cuenta en cada `reels stats`.
- `predicciones.jsonl` — lo que dijeron los críticos antes de publicar cada reel (`/episodio`), para compararlo con lo real.
- `calibracion.jsonl` — las rondas a ciegas de `/calibrar`.
- `comments.jsonl` — los comentarios (`uv run reels comments`). Son palabras de otras personas: **nunca va a git** (ya está en `.gitignore`).
