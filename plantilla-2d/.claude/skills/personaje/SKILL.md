---
name: personaje
description: Crea o cambia un personaje de la fábrica 2D - su aspecto (un Persona o una Cosa con parámetros, o una pieza dibujada a medida por el dibujante) con su hoja de expresiones, y su voz (de la biblioteca de ElevenLabs o DISEÑADA desde una descripción, con 3 muestras para elegir). También el narrador de la cuenta, que solo tiene voz. Usar con "/personaje <nombre>", "quiero un narrador", "diseña una voz" o cuando una historia necesite a alguien nuevo.
argument-hint: "<id del personaje o «narrador»> [descripción]"
---

# /personaje — aspecto y voz

Español claro, de tú. Las decisiones de gusto son de quien manda: tú enseñas y recomiendas.
Un personaje vive en `personajes/<id>/personaje.json`:
```json
{"id": "lola", "display_name": "Lola", "role": "personaje", "description": "…",
 "piece": "Persona", "props": {"pelo": "moño", "ropa": "vestido", "color": "turquesa"},
 "voice": {"voice_id": "…", "name": "…", "origin": "biblioteca | diseñada", "stability": 0.5}}
```
El **narrador** es `personajes/narrador/personaje.json` con `"piece": null` (no sale en pantalla).

## 1. Quién es (gratis)
Pregunta lo justo (de una en una): quién es, cómo habla, qué nunca haría, cómo se le reconoce de un vistazo (3 rasgos).
Escríbelo en `docs/biblia.md` (su bloque, sin `<…>`).

## 2. Aspecto (solo si sale en pantalla; gratis)
1. **Primero, ¿basta con lo que existe?** `Persona` (ropa, pelo, sombrero, barba, gafas, sostiene, gag…) o `Cosa`
   (forma, colores) cubren la mayoría (`docs/piezas.md`). Propón los props y haz la hoja:
   escribe el JSON y `uv run reels personaje <id> --no-abrir` → `personajes/<id>/hoja.png`. Enséñala con Read.
2. Si no basta (un animal, una criatura, una forma muy suya): lanza al subagente `dibujante` con la descripción, los
   3 rasgos y para qué historias es. Él dibuja `remotion/src/personajes/<id>.tsx`, lo comprueba y te da la hoja.
   Pasa la hoja al `ojo` (modo hoja) si hay dudas.
3. ✋ **OK de quien manda** al aspecto. Corrige lo que pida. Una vez aprobado, el aspecto se congela.

## 3. Voz (la biblioteca es gratis; diseñar y probar cuestan)
Dos caminos; explícalos en dos líneas y recomienda:
- **De la biblioteca** (gratis buscar): `uv run reels voice-search "<narrador, abuelo…>" --acento peninsular`.
  Enseña 4–6 con su descripción; quien manda las escucha en la web (o con su `preview_url`). Al elegir:
  `uv run reels voice-use <voice_id> --personaje <id>`. Ojo: una voz de la biblioteca la puede retirar su autor.
- **Diseñada** (unos 120 créditos por 3 muestras; avisa antes con la cifra y el saldo de `uv run reels doctor`): la
  voz es suya y nadie la retira. Escribe con quien manda la descripción («narrador de España, cuarentón, seco, con
  sorna, rápido») y lanza `uv run reels voice-design "<descripción>"` → abre `muestras.html`. Quien manda escucha
  y elige; `uv run reels voice-save <n> --nombre "<nombre>" --personaje <id>` (gratis) la guarda en su cuenta y en
  el JSON.
Prueba final (unos pocos créditos, con OK): `uv run reels voice-try <id> --frase "<una frase suya>"`.

## 4. «Actúalo tú» (opcional, cuesta)
Si una frase no sale como quiere, puede grabarla él mismo (con el teléfono o la computadora) con el ritmo exacto y
la fábrica la convierte a la voz del personaje: `uv run reels voice-act <slug> <beat> <ruta-de-su-grabación>`.
Cuesta según lo que dure (unos segundos ≈ pocas decenas de créditos): avisa antes. Solo su propia voz, nunca la de
otra persona sin permiso.

## Cierre
Comprueba que `personajes/<id>/personaje.json` tiene `voice.voice_id` (y `piece` + hoja si sale en pantalla) y que
`docs/biblia.md` lo describe. Si sigue el curso y es el narrador: `/tarrito comprobar A·3`.
