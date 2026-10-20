---
name: personaje
description: Da cuerpo y voz a tus personajes - diseña el "objeto con cara" (forma, una parte que actúa, colores, ojos, cejas y boca) o el humano, lo guarda como datos en personajes/<id>/personaje.json, saca su hoja de expresiones y su fotograma para que lo apruebes y hace el casting de voz con 6 frases de prueba (biblioteca pública de ElevenLabs). Rellena su ficha en docs/biblia.md. Usar con "/personaje" o cuando quieras crear o cambiar un personaje.
argument-hint: "[cosa|humano] [nombre]"
---

# /personaje — tu personaje en un fotograma y con voz

Español claro; a quien manda, de tú. Gratis salvo el casting de voz (créditos de ElevenLabs: avisa con la cifra antes).
Antes lee `docs/territorio.md` (quién nota cosas), `docs/publico.md` (acento) y `docs/biblia.md`.
La guía completa de cómo se describe un personaje (formas, colores, acabados, cara, brazos, accesorios, humanos) es
`docs/personajes.md`: léela antes de escribir nada. Si ya existe `personajes/<id>/personaje.json` (la plantilla trae
de ejemplo `lucio`, `estudiante`, `moka` y `barista`), parte de él en vez de empezar de cero.

## Cómo se guarda un personaje
Una **carpeta con datos**, no un modelo 3D hecho a mano (el constructor lo construye por código):
```
personajes/<id>/
  personaje.json   ← lo que lo define (formato de docs/personajes.md: role, display_name, voice, placeholder, object/human)
  hoja.png         ← su hoja de expresiones (la saca `reels personaje <id>`)
  fotograma.png    ← el fotograma que apruebas (lo saca el mismo comando)
  casting.md       ← las 6 frases de prueba y las notas de cada voz
  casting/<voz>/   ← los audios de prueba (no van a git)
```
`<id>` en minúsculas, sin tildes ni espacios. Una vez aprobado, el aspecto **se congela**: luego solo se pulen
expresividad, luz y ropa.

## 1. Diseñar (puerta: eliges una variante)
Para **la cosa** (objeto con cara) propón **3 variantes** en texto, cada una con: **forma** (una de las de
`docs/personajes.md`, la silueta que se reconoce en miniatura), **la parte que actúa** y qué hace al alarmarse, dudar o
estar triste, **2–3 colores** que se distingan a tamaño de teléfono (nada de logos ni colores de marca real),
**ojos, cejas y boca**, y **3 rasgos de miniatura**. Lo que hace reconocible a un personaje: nombre en el diálogo +
color + personalidad.
Para **el humano**: pelo (`hair_style`: corto, `curly`, `bob`, `long`), gafas, ropa y colores (`human`).
✋ **Puerta**: elige una variante (o mezcla). Escribe `personajes/<id>/personaje.json` y valida:
`uv run python -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" personajes/<id>/personaje.json`

## 2. La ficha en la biblia
Rellena su apartado en `docs/biblia.md` (NOMBRE · ASPECTO · HABLA con 2 ejemplos · NUNCA · ACTÚA CON · RELACIÓN).
El NUNCA es obligatorio (p. ej. "nunca sermonea", "nunca explica el chiste"). Cuando ya estén la cosa y el humano,
rellena también el apartado de secundarios de la biblia (o escribe "ninguno por ahora"): si queda el hueco, el lote
4·6 no se sella.

## 3. Verlo (gratis)
`uv run reels personaje <id> --no-abrir` (1–3 min): saca `hoja.png` (8 emociones, 4 bocas, gestos, parpadeo) y
`fotograma.png`. Enséñale las dos (léelas tú también) y ✋ **puerta**: ¿se reconoce en miniatura? ¿Se ve la parte que
actúa? ¿Alguna emoción no se lee? Si no, ajusta `personaje.json` y repite (máximo 3 vueltas antes de cambiar de variante).

## 4. Casting de voz (cuesta poco: avisa antes)
1. Escribe en `personajes/<id>/casting.md`, bajo `## Frases`, **6 frases de prueba** numeradas ("1. **neutral**:
   …"), una por registro: **neutral**, **susurro**, **duda**, **sarcasmo**, **confesión** y **remate**. Con su forma
   de hablar de la biblia, ≤ 8 palabras, con la puntuación que marca el ritmo.
2. Busca candidatas (gratis) con el acento de `docs/publico.md`:
   `uv run python .claude/skills/personaje/casting.py buscar --genero male --acento "latin american" --texto calida`
   (prueba 2–3 búsquedas: `--edad`, `--uso conversational`, otras palabras). Descarta las voces "de anuncio" o de
   narrador de documental: si suena a locutor de colchones, no es tu personaje. Propón **2–3 candidatas** con su porqué.
3. Estima y pregunta: `uv run python .claude/skills/personaje/casting.py estimar <id> 3` (≈ 120–150 créditos por voz
   con v4). ✋ Con su OK: `… casting.py probar <id> <voice_id> <voice_id> …` (añade las voces a "My Voices", gratis,
   y deja las 6 frases de cada una en `personajes/<id>/casting/<voz>/`, más `todas.mp3` seguidas).
   Si prefiere la web: elevenlabs.io → Voices → Voice Library, las mismas frases en "Text to Speech" con v4.
4. `… casting.py medir <id>` (gratis): tono, ritmo y si se entiende cada frase. Ayuda a comparar, pero **elige quien
   manda, de oído** ("tu oído es el juez, no un modelo"): que escuche `todas.mp3` de cada candidata.
5. En `casting.md`, una tabla: `voz · acento · cómo suena cada frase (1–5) · notas` y la elegida con su porqué.
6. Guarda la elegida en `personaje.json` → `voice.voice_id`, `voice.name` y una nota en `voice_note`.
**Clonar una voz**: solo **tu propia voz** (o la de alguien que te dé permiso por escrito); nunca la de otra persona,
un famoso o un personaje con dueño. Pide plan de pago y grabar unos minutos con buen micrófono. No hace falta.

## 5. Reparto
Si este personaje va a ser el de siempre, ponlo en `reparto.json` (`"cosa": {"personaje": "<id>"}` o `"humano"`);
si no, cada guion lo elige en `characters`. Comprueba el JSON después.

## 6. Cierre
En 4 líneas: quién es, cómo se ve, qué voz tiene y qué falta. Apunta el gasto del casting en `docs/decisiones.md`.
Si sigue el curso: `/tarrito comprobar` sella los lotes 4·4 (personaje), 4·5 (voz) y 4·6 (biblia).
