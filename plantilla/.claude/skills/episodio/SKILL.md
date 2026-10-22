---
name: episodio
description: Produce un reel de principio a fin a partir de una idea elegida, por capas de barato a caro y con una puerta tuya en cada capa - guion en tabla, revisores (lint, editor, oído, cuidado y los 5 espectadores, que fuerzan la reescritura v1 a v2 si alguien hace scroll), voz, animática con el ojo, preview, final y gancho B. Guarda el estado en episodes/<slug>/estado.md para seguir en un chat nuevo y avisa antes de gastar. Usar con "/episodio <idea o slug>" o cuando quieras hacer el siguiente reel.
argument-hint: "<id de idea | slug | idea descrita> [ligero|completo]"
---

# /episodio — de la idea elegida a `publicar/<slug>/`

**Principio:** cada error se caza en la capa más barata. Código gratis (`reels lint`) → críticos (suscripción) →
tú → gasto. Nada de pago (voz, nube) sin pasar antes las revisiones gratis y tu puerta.
Habla en español claro; a la persona que dirige, de tú. Las decisiones de gusto (voz, actuación, ritmo) son suyas.

## 0. Arranque y retomar
**De dónde sale la idea:**
- `/episodio <slug>` y existe `episodes/<slug>/estado.md` → **retoma**: lee el estado, di en 2 líneas dónde estaba
  ("Puerta 2 aprobada; toca la animática") y sigue. No rehagas nada aprobado.
- `/episodio <id>` → esa idea de `ideas/banco.jsonl` (búscala con grep; no leas el banco entero).
- `/episodio <una idea descrita>` → se usa tal cual y se apunta en el banco como `elegida` (origen `tuya`).
- `/episodio` sin más → la idea `elegida`. Si hay varias o ninguna, enseña las `elegida` y las 3 `propuesta` con más
  puntos y pregunta. Nunca elijas en silencio.

**Primera vez:** elige un slug corto en minúsculas y sin tildes, crea `episodes/<slug>/` y copia
`.claude/skills/episodio/estado-plantilla.md` a `episodes/<slug>/estado.md` rellenando cabecera e idea.
**Actualiza `estado.md` al pasar cada puerta** (marca `[x]` con fecha y lo que dijo), cada gasto y cada decisión.

Lee una vez por sesión: `CLAUDE.md`, `docs/territorio.md`, `docs/biblia.md`, `docs/lo-que-funciona.md`,
`style/guide.md`, `docs/hipotesis.md`, `docs/decisiones.md` y, para lo que se puede pedir en un guion,
`docs/piezas.md` y `reparto.json`. Ejemplo de `script.json`: `assets/humo/script.json` (busca campos con grep).

**Contexto limpio:** tras cada puerta, sugiere seguir en un chat nuevo con `/episodio <slug>` (el estado lo
recuerda todo). De los comandos largos (voice, build, render, compose) quédate con las últimas ~20 líneas.

**Modo de críticos:** `ligero` por defecto (los 5 espectadores en un solo trabajador, en modo panel) o `completo`
(un trabajador por espectador). Apúntalo en el estado. Consumo orientativo en Pro de la fase 1: ligero ~5–6
trabajadores (~⅕ de la ventana de 5 h); completo ~9–10 (~⅓). Dilo antes de lanzarlos.

---

## Capa 1 — Guion (gratis)
1. **Tabla v1** (no prosa): `# · quién · frase · cómo se dice · plano · qué se ve/oye · segundo aprox.`
   Comprueba tú antes de enseñarla:
   - el **fotograma 0** tiene el conflicto **escrito** y legible (pantalla, cartel dentro del mundo), sin contexto;
   - 35–40 s (≈ 2,6 palabras/s + silencios); frases de ≤ 8 palabras;
   - algo en juego, un reloj o una escalera que sube; la frase que se comparte, cerca del final;
   - final que da la vuelta al principio + coda muda de 1–2 s; 2–3 silencios con intención como mucho;
   - el **texto del post**: una frase que abre la historia + una petición sobre el espectador;
   - qué hipótesis prueba (`tests`) y un **gancho B** de otro tipo que solo cambie los 1–2 primeros beats.
   Guarda la tabla en `episodes/<slug>/guion-v1.md`.
2. **`episodes/<slug>/script.json`** con lo que existe en `reels/schema.py` (enums cerrados: no inventes valores).
   Si la idea necesita una pieza nueva, apúntala para la capa 1b. Valida:
   `uv run python -c "import json; from reels.schema import Episode; Episode.model_validate(json.load(open('episodes/<slug>/script.json', encoding='utf-8')))"`
3. `uv run reels lint <slug>`: arregla todos los ERROR; los AVISO, arréglalos o explica por qué no.
4. **Revisores en paralelo** (un solo mensaje): `editor-guion` (modo revisar), `oido`, `cuidado` y los
   espectadores (ligero: un `espectador` en modo panel; completo: uno por persona activa o en prueba de
   `docs/criticos.md`). A los espectadores pásales **solo** la tabla con segundo aproximado, lo que se ve, lo que se
   oye y el texto en pantalla, más el texto del post: nada de intenciones. Guarda sus líneas JSON.
5. **Regla de reescritura ("si Javi se aburre en el segundo 2, se reescribe")**: hay v2 si se cumple una:
   - algún espectador hace `SCROLL` en un beat que empieza antes del segundo 3;
   - dos o más hacen `SCROLL` en el mismo beat;
   - el editor dice `no listo`, o `cuidado` dice `riesgo serio`.
   Entonces lanza `editor-guion` en modo **reescribir** con la tabla v1, las notas de los revisores y las primeras
   líneas de los espectadores. Guarda su tabla en `guion-v2.md`, actualiza `script.json`, pasa otra vez el lint y
   **vuelve a lanzar solo a los espectadores** sobre la v2. Como mucho hasta v3. Si tras v3 sigue igual, díselo tal
   cual: puede que la idea no dé más.
   Si no hace falta v2, aplica tú lo que señalen 2+ revisores o uno con un argumento claro; lo que no apliques,
   con su porqué. Un `riesgo serio` de `cuidado` se arregla siempre, conservando la emoción.
   Las **notas** de los espectadores no deciden nada (hasta que `/calibrar` demuestre que aciertan): sirven por lo
   concreto.
6. Guarda `episodes/<slug>/critica.md`: qué dijo cada revisor (resumido), la tabla de scroll v1 → v2
   (`persona · v1 · v2`) y qué cambiaste.
7. ✋ **Puerta 1 — Guion**: la tabla final, el texto del post, qué prueba, el gancho B y en 4–6 líneas lo que
   dijeron los revisores (p. ej. "Javi hacía scroll en el segundo 2 con la v1; con la v2 se queda"). Si hay piezas
   nuevas: cuáles y cuánto trabajo llevan. Con su OK, marca la puerta en `estado.md`.

## Capa 1b — Piezas nuevas (solo si hacen falta, antes de gastar)
Sigue `docs/anadir-una-pieza.md`. Pantallas: Remotion Studio (`cd remotion && npm run studio`). Un fotograma a la
persona que manda y ✋ **Puerta 1b** (OK al aspecto). Escenario o personaje nuevo: es lo más caro (días): dilo en
la puerta 1 con en cuántos reels más se reutilizaría, y nunca lo empieces sin su OK. Al acabar, apúntalo en
`docs/piezas.md`.

## Capa 2 — Voz (cuesta créditos de ElevenLabs)
1. **Avísame antes de gastar** (obligatorio, aunque ya lo haya dicho otras veces):
   - `uv run python .claude/skills/episodio/estimar_voz.py <slug> [--tomas <beats>]` → créditos como mucho;
   - `uv run reels doctor` → créditos que le quedan (línea de ElevenLabs);
   - si no llega para el episodio + un 30 % de retoques, para y dilo.
   Pregunta con los números: "Esto gasta ~X créditos de los Y que te quedan. ¿Lanzo las voces?". Sin un sí claro,
   no se lanza. Apunta el gasto en `estado.md`.
2. `uv run reels voice <slug>`. Para las 1–2 frases con emoción fuerte (la que se comparte, el final): 
   `uv run reels voice <slug> --takes <beat>` → abre una página con 3 tomas; elige **de oído** quien manda y se fija
   con `--pick <beat>=<toma>`. La elegida no se vuelve a tocar.
3. `uv run reels lint <slug>` otra vez: ahora mide la duración real y cuándo entra la primera voz.
4. `uv run reels animatic <slug> --audio-only` (voz, música y subtítulos sobre negro).
5. ✋ **Puerta 2 — Voz**: que escuche la animática de audio. Pregunta por frases concretas que te preocupen. Los
   arreglos, con `--only <beats>` (y estimación antes: `estimar_voz.py <slug> --solo <beats>`).

## Capa 3 — Animática + ojo (gratis, local)
1. `uv run reels build <slug>` y `uv run reels render <slug> --quality preview --keyframes`.
2. Subagente `ojo` (modo fotogramas) con el slug. Aplica sus arreglos al `script.json`, vuelve a sacar los
   fotogramas de los beats tocados y repite si hace falta (máximo 2 vueltas). Los "fallos de pieza", a
   `docs/backlog-visual.md` (si ya estaban, sube su contador).
3. Mira tú el **fotograma 0** a tamaño de teléfono: ¿pararía el scroll? Es el fotograma más importante.
4. `uv run reels animatic <slug>`.
5. ✋ **Puerta 3 — Animática**: la animática + 3–4 fotogramas clave + lo que corrigió el `ojo`.

## Capa 4 — Preview de lo delicado (gratis, local y lento)
1. `uv run reels preview <slug> --beats a-b --quality draft --no-open` de: **los 3 primeros segundos siempre**, el
   pico emocional y el final.
2. Hojas: `uv run reels sheet episodes/<slug>/preview_<a>-<b>.mp4 --start 0 --end <s> --fps 4` (el arranque, a
   8 fps). `ojo` en modo movimiento con las hojas. Arregla lo que encuentre antes de enseñarlo.
3. ✋ **Puerta 4 — Preview**: la actuación y el ritmo solo los juzga de verdad quien manda (tú no oyes ni ves en
   movimiento como una persona).

## Capa 5 — Final + gancho B
1. **Dónde renderizar**: en local es gratis pero lento; propón **`/turno-de-noche <slug>`** (lo deja todo hecho
   mientras duerme). Si `uv run reels doctor --prueba-render` dijo que en local tarda demasiado, propón `--cloud`
   (GPU alquilada, céntimos; la máquina se destruye al acabar y, si la computadora se apaga a mitad, se destruye sola
   a los 20 min) y **pide el OK con el precio** antes. Antes del turno, deja listo el **gancho B** (paso 6, sin
   render) para que el turno lo cueza también.
2. Si lo haces ahora: `uv run reels render <slug>` → `uv run reels compose <slug>` → `uv run reels check <slug>`.
3. Hojas del final: `uv run reels sheet <slug> --start 0 --end 3 --fps 8` y del último tramo; `ojo` en modo
   movimiento: subtítulos, que nada tape la cara, que lo que engancha esté en el primer segundo, que el final enlace.
4. Portada: `uv run reels cover <slug> --beat <el más fuerte>`.
5. `publicar/<slug>/<slug>.txt`: frase que abre la historia + petición sobre el espectador ("Envíaselo a…") + 3–5
   hashtags + crédito de música + recordatorio de la etiqueta de IA (sigue `post_checklist` de
   `assets/brand/brand.json`). Copia el vídeo a `publicar/<slug>/<slug>.mp4`. `uv run reels lint <slug>` final.
6. **Gancho B (obligatorio)**: `episodes/<slug>-b/script.json` = copia del A con solo los 1–2 primeros beats
   cambiados y **`"slug": "<slug>-b"`** dentro (si no, `reels lint` da error: voces y escena irían a la carpeta del
   A). `uv run reels lint <slug>-b`. Sus voces nuevas cuestan poco, pero cuestan: estimación
   (`estimar_voz.py <slug>-b`) y OK como en la capa 2; lo que no cambia respecto al A suele salir de la caché sin cobrar. Escribe
   `publicar/<slug>/<slug>-b.txt`, que **empieza con otra frase** (las métricas se emparejan por la primera línea).
   - **«Prepara el gancho B para esta noche.»** = todo lo de este paso **sin** `build` ni `render`: guion B, lint,
     voces (con su OK) y texto. Termina diciendo que el B está listo y que el turno lo cocerá; no lances nada más.
   - **El B se cuece entero**, no solo los planos cambiados: es un episodio aparte (su audio dura distinto, así que
     todo lo que viene después se mueve). Render y montaje como el A; `/turno-de-noche <slug>` lo hace solo si existe
     `episodes/<slug>-b/` con voces. En local tarda lo mismo que el A; en la nube cuesta lo mismo que el A.
   - Resultado: `publicar/<slug>/<slug>-b.mp4` junto al A.
7. **Predicción** (antes de publicar, para `/calibrar`): una línea en `metrics/predicciones.jsonl`:
   `{"slug", "fecha", "espectadores": {"<nombre>": <su línea JSON de la última versión>}, "editor": "<veredicto>", "jurado": <puntos del banco>, "salta_3s": <apuesta %>, "compart_pct": <apuesta %>, "apuesta_de": "quien manda"}`.
   Pide a quien manda su propia apuesta de salto < 3 s y compartidos, y apúntala en `estado.md`.
   **Si ya hay una línea de este slug, no la reescribas**: «Enséñame mi apuesta» = léela y enséñasela
   (`salta_3s`, `compart_pct`, fecha), nada más. Solo si quien manda pide cambiarla **antes de publicar**, añade una
   línea nueva (vale la última) y apúntalo en `estado.md`; nunca borres ni edites líneas, y nunca después de publicar
   (la apuesta se hace a ciegas: si no, `/calibrar` no sirve).
8. ✋ **Puerta 5 — Final**: vídeo A y B, portada y texto. Recomendación: subir A y B como **reels de prueba**
   (solo los ve gente que no sigue la cuenta) y a las ~24 h publicar para todos el que menos gente pierda en 3 s;
   uno al día como mucho, siempre en la misma franja. **La fábrica nunca publica nada**: lo sube quien manda.

## Al terminar
- En `ideas/banco.jsonl`, la idea pasa a `hecha` con el slug. `estado.md`: todas las puertas y el gasto total.
- `docs/decisiones.md` al día con cada corrección (`- AAAA-MM-DD · <slug> · qué cambió · por qué`).
- Si es un repositorio git: commit pequeño con `script.json`, `estado.md`, `critica.md`, `guion-v*.md` y documentos
  (nunca audio ni vídeo).
- Recuérdale `/numeros` a las 48 h de publicar.
