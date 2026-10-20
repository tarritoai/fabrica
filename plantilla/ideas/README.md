# ideas/

El banco de ideas para tus próximos reels. Lo rellena `/ideas` (y tú, cuando apuntes algo suelto).

- `banco.jsonl` — una idea por línea, **todas**: las vivas y las muertas. Estados: `propuesta` → `elegida` →
  `hecha` (con su `slug`), o `descartada` (con su `motivo`, para siempre: así no vuelve) / `archivada` (perdió dos
  rondas o sobraba; se recupera si la pides). Como mucho ~20 `propuesta` vivas. Lo lee `/episodio`.
- `inbox.md` — ideas sueltas tuyas y de los comentarios. Tienen prioridad en la siguiente `/ideas`.
- `fuentes.md` — ingredientes para idear: verdades mecánicas, momentos vividos, géneros, mecanismos que funcionaron.
- `rondas/AAAA-MM-DD.md` — el acta de cada ronda de `/ideas`: las fichas, la tabla del jurado y lo que dijeron los
  espectadores y `cuidado`.
- `mis-ideas.md` y `jurado-mio.md` — tus ejercicios del curso (lotes 5·1 y 5·2).

Cada línea del banco (JSON, sin saltos de línea dentro):
`{"id": "AAAAMMDD-NN", "fecha": "AAAA-MM-DD", "titulo": "...", "lente": "vida|verdades|formatos|exito|salvaje|tuya",
"origen": "ideador|bandeja|comentario|tuya", "estado": "propuesta", "logline": "...", "segundo_0": "...",
"primera_frase": "...", "final": "...", "puntos": 34, "notas": "...", "motivo": "...", "rondas_perdidas": 0,
"slug": "..."}` (`motivo`, solo en `descartada` y `archivada`; `slug`, solo en `elegida` y `hecha`).
