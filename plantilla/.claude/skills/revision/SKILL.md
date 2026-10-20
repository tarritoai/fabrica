---
name: revision
description: Revisión semanal de la cuenta. Junta las métricas (de la API de Instagram o las que metiste con /numeros), el analista las cruza con las hipótesis, el ojo compara los arranques que retienen con los que no, y se proponen cambios a lo que funciona (con tu OK) dejando la memoria más corta o igual. Usar una vez por semana, con "/revision" o cuando preguntes cómo van los reels.
argument-hint: "[desde AAAA-MM-DD]"
---

# /revision — qué hemos aprendido esta semana

Gratis salvo la suscripción (2–3 trabajadores: `analista`, `ojo` y, si toca, `/calibrar`). Español claro; a quien
manda, de tú. Recuerda la regla de oro: **un reel no demuestra nada; tres empiezan a hablar.**

## 1. Datos (gratis)
1. **¿De dónde salen los números?**
   - Si hay `IG_ACCESS_TOKEN` en `.env` (no lo leas: comprueba con `uv run reels doctor` si aparece configurado):
     `uv run reels stats` y `uv run reels comments` (si falla el permiso de comentarios, sigue sin ellos).
   - Si no, los números son los que se metieron a mano con `/numeros`. Mira la fecha del último registro de cada
     reel publicado: si algún reel de más de 48 h no tiene datos de los últimos 7 días, **para y propón `/numeros`**
     antes de seguir ("Me faltan los números de <slug>: ¿me los pegas?").
2. `uv run reels review` → la tabla de Instagram. Otras plataformas:
   `uv run python .claude/skills/numeros/numeros.py tabla --plataforma tiktok` (o `youtube`), si hay datos.
3. Un reel que sale como `?` (sin emparejar) es que falta `publicar/<slug>/<slug>.txt` con el texto que se pegó:
   avisa.
4. Mira la fecha del último informe en `reviews/`: lo de esta revisión es lo de después.

## 2. Análisis
- Lanza `analista` con la tabla (o las tablas) y la fecha del último informe.
- Revisa tú su informe: cada conclusión con número; nada confirmado con menos muestra de la que pide
  `docs/hipotesis.md`; los confusores (edad < 48 h, hora, dos el mismo día, variables pegadas) dichos donde
  aplican. Si exagera, corrígelo.
- **Lo visual**: con los reels maduros, los 2 que menos gente pierde en < 3 s y los 2 que más:
  `uv run reels sheet <slug> --start 0 --end 3 --fps 4` de cada uno, y las cuatro hojas juntas al `ojo` (modo
  movimiento): ¿qué tienen los primeros que no tengan los segundos (texto legible, brillo, cara, cuándo aparece lo
  que engancha)? Lo que salga → `docs/backlog-visual.md` o una hipótesis nueva (con OK).
- **¿Toca calibrar?** Si hay ≥ 8 reels maduros con datos y ≥ 3 nuevos desde la última calibración (o nunca se ha
  hecho), proponlo al final: "¿Hacemos `/calibrar`?". Con menos de 8, no: solo se describe.

## 3. Guardar y proponer (nada se aplica sin OK)
- Informe en `reviews/AAAA-MM-DD.md`: tabla, análisis, lo visual, propuestas.
- Historias e ideas de los comentarios (sin nombres) → `ideas/inbox.md`, una línea cada una.
- Mecanismos de lo que más se compartió → `ideas/fuentes.md` (apartado "Mecanismos que funcionaron").
- Enseña el **diff exacto** de los cambios que propones a `docs/hipotesis.md`, `docs/lo-que-funciona.md` y
  `style/guide.md`. ✋ **Puerta**: se aplican solo los que apruebe.
- Una regla confirmada que se pueda comprobar con código → propón añadirla a `reels lint` (con OK; es un cambio en
  `reels/lint.py`).

## 4. Que la memoria no crezca sin límite
Cada revisión deja los archivos **más cortos o igual** (se leen en cada chat). Propón estos recortes junto a lo
demás:
- `docs/decisiones.md`: las decisiones que se repiten se condensan en una regla de `docs/lo-que-funciona.md` (o del
  lint) y salen de aquí. Máximo ~30 líneas.
- `docs/lo-que-funciona.md`: máximo ~40 reglas; junta las que dicen lo mismo.
- `docs/hipotesis.md`: confirmadas → a lo-que-funciona y fuera de aquí; descartadas, una línea al final.
- `docs/backlog-visual.md`: los "Hecho" de hace más de un mes, fuera.
- `ideas/banco.jsonl`: las `archivada` de hace más de 3 meses pueden salir (las `descartada`, nunca).

## 5. A quien manda
En 5–8 líneas, sin tablas largas (están en el informe): cómo va la cuenta (también seguidores nuevos por cada
1.000 visitas), qué ha cambiado, qué se confirma o se cae, qué probamos en los próximos 3 reels y qué cambios
necesitan su OK. Si un reel fracasó: qué mirar (el salto < 3 s y el fotograma 0 primero), qué no hacer (cambiar
diez cosas a la vez) y que un fracaso es un dato, no un juicio.
