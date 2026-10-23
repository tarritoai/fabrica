---
name: referencias
description: Aprende del género con reels de otras cuentas que TÚ has guardado a mano en references/inbox/ (la fábrica nunca descarga reels de nadie). Los desmonta gratis, compara aciertos con fallos de la misma cuenta y deja patrones, lo ya visto, ingredientes y mejoras visuales. Usar una vez al mes, cuando digas que has guardado reels, o con "/referencias".
---

# /referencias — aprender del género sin copiarlo

Español claro; a quien manda, de tú. Gratis (solo suscripción, sin trabajadores extra).

## Reglas
- **Nada se descarga automáticamente.** Ni con herramientas, ni con el navegador, ni con scripts: las condiciones de
  las plataformas no lo permiten. Los reels los guarda quien manda, a mano, en `references/inbox/` (un .mp4 por
  reel; si quiere, con un `.txt` al lado con visitas, "me gusta", comentarios, la cuenta y la fecha).
- Los reels ajenos **nunca van a git** ni se comparten. Solo se versionan `patterns.md` y `visto.md`.
- Se aprende **el mecanismo**, nunca la premisa, el chiste o el diseño concreto.

## 0. Si la bandeja está vacía
Explica qué conviene guardar (5–10 reels bastan):
- de 2–3 cuentas de su nicho, **los más vistos y los menos vistos de la misma época** (lo que enseña es comparar
  dentro de la misma cuenta: mismo público, misma cara; cambia la idea y el arranque);
- que apunte las visitas en el `.txt`: sin números solo se compara a ojo;
- cómo guardarlos: desde la app o la web, con la opción de descargar o guardar de la propia plataforma cuando la
  cuenta lo permite, o grabando la pantalla del teléfono. Si un reel no se puede guardar, basta con el enlace y una
  descripción en el `.txt`.

## 1. Desmontar (gratis)
Para cada vídeo: `uv run reels ref references/inbox/<video>.mp4` → `references/<nombre>/` con `sheet_cuts.png`
(un fotograma por plano), `sheet_1fps.png`, `transcript.txt` (con tiempos) e `info.json` (duración y cortes).
Luego mueve el .mp4 y su `.txt` a `references/<nombre>/`.

## 2. Analizar (tú, mirando las imágenes y la transcripción)
Por reel: **segundos 0–3** (qué se ve, qué se lee, qué se oye y por qué engancha o no) · **estructura** (premisa,
escalera, giro, final, duración, segundos por plano) · **el momento que se comparte** y **lo que provoca
comentarios** · **recursos** (pantallas, texto, música, silencios, cámara) · **números** si los hay.
Luego, por cuenta: **¿qué tienen los aciertos que no tengan los fallos?** Eso es un patrón; un reel suelto, no.

## 3. Guardar
- `references/patterns.md`: apartado `## Lote AAAA-MM` con los patrones nuevos y los que se confirman o contradicen.
  Condensa: que no pase de ~40 líneas.
- `references/visto.md`: una línea por premisa muy vista (`- premisa · dónde · AAAA-MM`). La leen el jurado, los
  ideadores y el espectador experto.
- Ingredientes nuevos (verdades, momentos, géneros, mecanismos) → `ideas/fuentes.md`.
- Lo que hacen visualmente mejor (luz, cámara, expresividad, ritmo, pantallas) → `docs/backlog-visual.md`.

## 4. A quien manda (puerta: qué probar)
En 5–8 líneas: qué hacen los mejores que tú no haces, qué haces ya mejor, y 1–2 cosas para probar.
✋ Cada cosa que quiera probar entra como hipótesis en `docs/hipotesis.md` **solo con su OK** (con el formato de ese
archivo: qué predice, cómo se mide, estado abierta).
