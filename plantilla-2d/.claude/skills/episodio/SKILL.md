---
name: episodio
description: Produce un reel 2D «¿Y si…?» de principio a fin a partir de una idea elegida, por capas de barato a caro y con una puerta tuya en cada capa - guion en tabla, revisores (lint, editor, oído, cuidado y los 5 espectadores, que fuerzan la reescritura v1 a v2 si alguien hace scroll), piezas nuevas del dibujante, voz (avisa antes de gastar), fotogramas clave con el ojo, vídeo, comprobación y gancho B. Guarda el estado en episodes/<slug>/estado.md para seguir en un chat nuevo. Usar con "/episodio <idea o slug>" o cuando quieras hacer el siguiente reel.
argument-hint: "<id de idea | slug | idea descrita> [ligero|completo]"
---

# /episodio — de la idea elegida a `publicar/<slug>/`

**Principio:** cada error se caza en la capa más barata. Código gratis (`reels lint`) → críticos (suscripción) →
tú → gasto. Nada de pago (voces, música) sin pasar antes las revisiones gratis y tu puerta.
Español claro; a la persona que dirige, de tú. Las decisiones de gusto (dibujo, voz, ritmo) son suyas.

## 0. Arranque y retomar
- `/episodio <slug>` y existe `episodes/<slug>/estado.md` → **retoma**: lee el estado, di en 2 líneas dónde estaba y
  sigue. No rehagas nada aprobado.
- `/episodio <id>` → esa idea de `ideas/banco.jsonl` (búscala con grep). `/episodio <una idea descrita>` → se usa
  tal cual y se apunta en el banco como `elegida` (origen `tuya`). `/episodio` sin más → la `elegida`; si hay
  varias o ninguna, enséñalas y pregunta. Nunca elijas en silencio.
- **Primera vez:** slug corto en minúsculas sin tildes; crea `episodes/<slug>/` y copia
  `.claude/skills/episodio/estado-plantilla.md` a `episodes/<slug>/estado.md`. **Actualiza `estado.md` en cada
  puerta** (`- [x] Puerta N · … · aprobada AAAA-MM-DD · lo que dijo`), cada gasto y cada decisión.
- Lee una vez por sesión: `CLAUDE.md`, `docs/formato.md`, `docs/territorio.md`, `docs/biblia.md`,
  `docs/lo-que-funciona.md`, `style/guide.md`, `docs/hipotesis.md`, `docs/decisiones.md` y `docs/piezas.md`.
  Ejemplo completo de `script.json`: `assets/ejemplos/quijote-gafas/script.json`.
- **Modo de críticos:** `ligero` por defecto (los 5 espectadores en un trabajador, modo panel) o `completo`. Dilo
  antes de lanzarlos (ligero ~5–6 trabajadores, ~⅕ de la ventana de 5 h en Pro; el dibujante suma si hay piezas).
- Tras cada puerta, sugiere seguir en un chat nuevo con `/episodio <slug>`.

---

## Capa 1 — Guion (gratis)
1. **Tabla v1** (`docs/formato.md`): `# · voz · frase · qué se ve · eventos (en qué palabra) · contador · segundo`.
   Antes de enseñarla comprueba: la pregunta en el cartel del fotograma 0; escalera de 3 con contador; un gag visual
   por frase; giro que rompe la escalera (un personaje, corto, en bocadillo); remate con pregunta de una palabra;
   20–45 s (~15 caracteres por segundo); frases ≤ 12 palabras; el **texto del post**; qué hipótesis prueba; un
   **gancho B** (otra pregunta u otro primer peldaño). Guárdala en `episodes/<slug>/guion-v1.md`.
2. **`episodes/<slug>/script.json`** con el vocabulario de `docs/piezas.md` (no inventes piezas, fondos ni tipos de
   evento). Voces: el narrador de la cuenta (`"narrador": "narrador"` = `personajes/narrador/`) y los personajes
   que hablen. Si falta una pieza, apúntala para la capa 1b y usa de momento la más parecida.
3. `uv run reels lint <slug>`: arregla todos los ERROR; los AVISO, arréglalos o di por qué no. El lint dice también
   la duración estimada.
4. **Revisores en paralelo** (un solo mensaje): `editor-guion` (revisar), `oido`, `cuidado` y los espectadores. A
   los espectadores pásales **solo** la tabla (segundo, qué se ve, qué se oye, texto en pantalla) y el texto del post.
5. **Regla de reescritura** («si Javi se aburre en el segundo 2, se reescribe»): hay v2 si algún espectador hace
   `SCROLL` en un beat antes del segundo 3, si dos o más hacen `SCROLL` en el mismo beat, si el editor dice `no
   listo` o si `cuidado` dice `riesgo serio`. Entonces `editor-guion` en modo **reescribir** → `guion-v2.md`, nuevo
   `script.json`, lint, y **solo los espectadores** otra vez. Como mucho hasta v3.
6. `episodes/<slug>/critica.md`: qué dijo cada revisor (resumido), la tabla de scroll v1 → v2 y qué cambiaste.
7. ✋ **Puerta 1 — Guion**: la tabla final, el texto del post, qué prueba, el gancho B, lo que dijeron los revisores
   en 4–6 líneas y las piezas nuevas que harían falta (cuántas y cuánto trabajo).

## Capa 1b — Piezas nuevas (solo si hacen falta; gratis, suscripción)
1. Para cada pieza que falte: ¿la cubre `Persona`/`Cosa`/`Objeto` con props? Si sí, ponlos en el guion.
2. Si no, lanza el `dibujante` (todas las piezas del episodio en un encargo) → `remotion/src/episodios/<slug>/`.
   Pide la hoja de cada una (`uv run reels personaje <Pieza> --episodio <slug> --no-abrir`) y pásalas al `ojo`
   (modo hoja).
3. **Boceto gratis antes de pagar voces**: `uv run reels stills <slug> --sin-voz --no-abrir` (tiempos estimados
   por el texto) → enséñale la hoja y pásala al `ojo`: los problemas de composición (personajes pequeños, algo
   tapado por los subtítulos, un sello encima de una cara) se arreglan aquí, gratis.
4. ✋ **Puerta 1b — Piezas y boceto**: enseña las hojas y el boceto. Lo que pida cambiar, al dibujante. Apúntalas en
   `docs/piezas.md` (sección del episodio).

## Capa 2 — Voz (cuesta créditos de ElevenLabs)
1. **Avisa antes de gastar** (obligatorio, aunque ya lo hayas dicho otras veces):
   `uv run reels voice <slug> --estimar` (créditos como mucho) y `uv run reels doctor` (saldo). Si no llega para el
   episodio + un 30 % de retoques, para. Pregunta: «Esto gasta como mucho X créditos (lo normal, ~Y) de los Z que te
   quedan. ¿Lanzo las voces?». Sin un sí claro, no se lanza.
2. `uv run reels voice <slug>`. Cada toma sale con su nota del «oído» (whisper). Apunta el gasto en `estado.md`
   (el total pagado del episodio queda en `voice.json`, `credits_total`).
   **Cómo se cobra** (explícaselo una vez): las frases seguidas de una misma voz van en **una sola toma** (suena más
   natural). El gancho va siempre en su toma (`pace.hook_alone`): cambiar el gancho o hacer el gancho B solo paga
   el gancho. Pero otra lectura de una frase del medio (`"take": 2`) vuelve a pagar su toma entera; para aislar una
   frase que se quiera poder repetir, `"pause_before": 0.2` en ella la deja en su propia toma.
3. `uv run reels lint <slug>` otra vez (ahora mide la duración real).
4. `uv run reels render <slug> --borrador --no-abrir` (media resolución, un minuto) y que lo escuche.
5. ✋ **Puerta 2 — Voz**: ¿suena bien? Para una toma que no le guste:
   - otra lectura: `"take": 2` en ese beat y `reels voice <slug>` (solo paga la toma nueva; estimación antes);
   - otro ritmo: `pace.tempo` (1.0–1.3), `pace.max_pause` y `pace.gap` son gratis: cambia el guion y vuelve a lanzar
     `reels stills`/`reels render` (rehacen las voces desde la caché solas, 0 créditos);
   - una frase con su ritmo exacto: «actúalo tú» (`reels voice-act`, cuesta poco; ver `/personaje`).
6. **Música** (el formato la lleva siempre): una del catálogo (`assets/music/music.json`; la del ejemplo vale) o una
   nueva con `uv run reels music-gen <nombre> "<cómo es>" --seconds <duración + 2>` (≈ 820 créditos por minuto:
   avisa y pide OK). Volumen 0.15–0.2. Licencia siempre en el catálogo.

## Capa 3 — Fotogramas clave + ojo (gratis)
1. `uv run reels stills <slug> --no-abrir` → `episodes/<slug>/fotogramas/` (uno por plano y por beat) + `hoja.jpg`.
2. Subagente `ojo` (modo fotogramas). Aplica sus arreglos al `script.json` (posiciones, escalas, props, palabra de
   cada evento), vuelve a sacar los fotogramas y repite si hace falta (máximo 2 vueltas). Los «fallos de pieza», al
   dibujante y a `docs/backlog-visual.md`.
3. Mira tú el **fotograma 0** a tamaño de teléfono: ¿pararía el scroll?
4. ✋ **Puerta 3 — Fotogramas**: la hoja + 3–4 fotogramas clave + lo que corrigió el ojo.

## Capa 4 — Vídeo, comprobación y gancho B (gratis salvo voces nuevas del B)
1. `uv run reels render <slug> --no-abrir` (unos minutos; no hace falta dejarlo de noche) → `final.mp4`.
2. `uv run reels check <slug>`: whisper escucha el reel entero y comprueba cada frase en su momento. «no oigo: …»
   es un aviso (a veces es el oído); un ✘ es que la frase no está donde toca.
3. Hojas de movimiento: `uv run reels sheet <slug> --start 0 --end 3 --fps 8` y del remate; `ojo` en modo movimiento.
4. Portada: `uv run reels cover <slug> --beat <el más fuerte>`.
5. `publicar/<slug>/<slug>.txt`: la frase que abre la historia + petición sobre el espectador + 3–5 hashtags +
   crédito de música (si su licencia lo pide) + recordatorio de la etiqueta de contenido hecho con IA. Copia el
   vídeo a `publicar/<slug>/<slug>.mp4`.
6. **Gancho B (obligatorio)**: `episodes/<slug>-b/script.json` = copia del A con solo los 1–2 primeros beats
   cambiados y `"slug": "<slug>-b"` (usa las piezas del A). `reels lint`, voces nuevas con estimación y OK (lo que
   no cambia sale de la caché), `reels render`, `reels check`, y `publicar/<slug>/<slug>-b.mp4` + `<slug>-b.txt`
   (que **empieza con otra frase**).
7. Opcional: `uv run reels carousel <slug>` → un carrusel de Instagram (el fotograma 0 y el final de cada plano;
   o los que elijas con `--frames 0,80,200`, mirando la hoja de `stills`). Gratis.
8. **Predicción** (antes de publicar, para `/calibrar`): una línea JSON en `metrics/predicciones.jsonl`:
   `{"slug", "fecha", "espectadores": {"<nombre>": <su línea JSON de la última versión>}, "editor": "<veredicto>",
   "jurado": <puntos del banco>, "salta_3s": <apuesta %>, "compart_pct": <apuesta %>, "apuesta_de": "quien manda"}`.
   Pide a quien manda su apuesta de salto < 3 s y de compartidos. Nunca se reescribe ni se borra una línea.
9. ✋ **Puerta 4 — Final**: vídeo A y B, portada y texto. Recomendación: subir A y B como reels de prueba y a las
   ~24 h publicar el que menos gente pierda en 3 s. **La fábrica nunca publica nada**: lo sube quien manda.

## Al terminar
- En `ideas/banco.jsonl`, la idea pasa a `hecha` con el slug. `estado.md` con todas las puertas y el gasto total.
- `docs/decisiones.md` con cada corrección (`- AAAA-MM-DD · <slug> · qué cambió · por qué`).
- Si es un repositorio git: commit pequeño con `script.json`, `estado.md`, `critica.md`, `guion-v*.md`, las piezas
  nuevas de `remotion/src/` y los documentos (nunca audio, vídeo ni fotogramas). Si `git log` dice que aún no hay
  ningún commit, el primero es la fábrica entera tal como se instaló (`git add -A` respeta el `.gitignore`).
- Recuérdale `/numeros` a las 48 h de publicar. Si sigue el curso: `/tarrito comprobar A·4`.
