# CLAUDE.md — tu fábrica de reels

## Reglas (siempre)
- **Responde siempre en español**, en lenguaje llano: quien manda puede no ser técnico. Español neutro, que se
  entienda en Latinoamérica y en España ("teléfono", "computadora"). Háblale de tú, sin dar por hecho su género.
- **Quien manda decide.** Las decisiones de gusto (idea, voz, actuación, ritmo, publicar) son suyas. Tú recomiendas,
  con tu porqué; nunca eliges en silencio.
- **Avisa antes de gastar** (ver «Reglas de gasto»): nada de pago sin un sí claro con la cifra delante.
- Enseña fotogramas y vídeos en cuanto existan.
- Secretos solo en `.env` (fuera de git). **Nunca lo leas ni imprimas claves.**
- Nada de marcas, logos ni personas reales en las pantallas (apps inventadas, datos falsos tipo `sk-demo-…`).
- **La fábrica nunca publica nada**: deja todo listo en `publicar/<slug>/` y lo sube quien manda.
- Reels de otras cuentas: solo los que guarda quien manda, a mano. Nunca descargues nada de nadie.
- A git solo van código, documentos y `script.json`/`estado.md`: nada de audio, vídeo, renders ni reels ajenos.
- Código, identificadores y nombres de archivo en inglés; guiones y textos de los vídeos, en el idioma de la cuenta.

## Qué es tu fábrica
Una fábrica de reels verticales (1080×1920, 35–40 s) con animación 3D. De una idea sale un guion (`script.json`) y
del guion, un vídeo listo para subir: voces con ElevenLabs, escena en Blender, pantallas y montaje con Remotion.
Trabajan 16 trabajadores (subagentes) y nadie decide salvo quien manda:
- **5 ideadores** (lentes vida, verdades, formatos, éxito, salvaje) · **1 jurado** (rúbrica, mata la mitad) ·
  **5 espectadores** (personas de tu público, en `docs/publico.md`) · **editor de guion** · **oído** · **ojo** ·
  **cuidado** · **analista**. Están en `.claude/agents/`.
De qué va la cuenta: `docs/territorio.md`. Para quién: `docs/publico.md`. Sus personajes: `docs/biblia.md`.

## Las órdenes (skills de `.claude/skills/`)
| Orden | Para qué |
|---|---|
| `/humo` | prueba gratis: un vídeo de unos 6 s de punta a punta |
| `/nicho` | tu territorio (3 pruebas, verdades mecánicas) y tu público con sus 5 espectadores |
| `/personaje` | tu personaje en datos, en un fotograma y con voz (casting de 6 frases) |
| `/ideas` | 5 ideadores → jurado → espectadores + cuidado → 5 finalistas con recomendación |
| `/episodio <idea>` | de la idea a `publicar/`, por capas y con puertas |
| `/turno-de-noche <slug>` | render + montaje + comprobación mientras duermes; parte en `publicar/<slug>/PARTE.md` |
| `/numeros` | métricas a mano (lo que ves en Instagram, TikTok o YouTube) |
| `/revision` | qué hemos aprendido esta semana |
| `/calibrar` | cuánto aciertan los críticos (con ≥ 8 reels con datos) |
| `/referencias` | aprender del género con reels que guardas tú |
| `/tarrito` | dónde vas, `/tarrito comprobar` sella cada lote del curso |

## Cómo se trabaja: por capas, de barato a caro
Cada error se caza en la capa más barata: comprobación por código (gratis) → críticos (suscripción) → quien manda →
gasto. Ninguna capa empieza sin el OK (✋) de la anterior:
0. **Ideas** → elige una. 1. **Guion** en tabla + revisores (si un espectador hace scroll en el segundo 2, se
reescribe) → OK. 2. **Voz** (cuesta) → OK. 3. **Animática** + ojo → OK. 4. **Preview** de lo delicado → OK.
5. **Final** + gancho B → OK a publicar (lo sube quien manda). El detalle está en `/episodio`.
Cada corrección de quien manda se apunta en `docs/decisiones.md`; `/revision` las convierte en reglas.

## Reglas de gasto
- **Cuesta dinero**: `reels voice`, `reels sfx-gen` y `reels music-gen` (créditos de ElevenLabs), `reels render --cloud` (Vast.ai),
  `reels script` y `reels make` (API de Anthropic: la fábrica no los necesita, no los uses).
- **Antes de gastar**: estima (`uv run python .claude/skills/episodio/estimar_voz.py <slug>` para la voz), mira el
  saldo (`uv run reels doctor`) y pregunta con las cifras. Si no hay para el episodio + un 30 % de retoques, para.
- Apunta cada gasto en `episodes/<slug>/estado.md`.
- Las voces se guardan en `.cache/voice/`: **no la borres** (repetir una voz igual no se vuelve a cobrar).
- La suscripción de Claude también tiene límite (ventanas de 5 h): `/ideas` y `/episodio` lanzan varios trabajadores;
  usa el modo **ligero** por defecto y avisa del consumo antes de lanzarlos. `/usage` enseña lo gastado.
- Si existe la variable `ANTHROPIC_API_KEY`, Claude Code cobra por API en vez de usar la suscripción: avisa.

## Cómo retomar (chats nuevos)
- Lo aprendido vive en la carpeta, no en el chat. Cada episodio guarda dónde va en `episodes/<slug>/estado.md`:
  en un chat nuevo, `/episodio <slug>` sigue desde la última puerta.
- Tras cada puerta, propón seguir en un chat nuevo (más rápido y gasta menos).
- Si se corta por el límite: espera al reinicio y escribe "sigue con /episodio <slug>".
- Al empezar un chat de trabajo, lee este archivo y, según la tarea, `docs/territorio.md`, `docs/biblia.md`,
  `docs/lo-que-funciona.md`, `docs/hipotesis.md` y `docs/decisiones.md`. Para un guion, también `docs/piezas.md`.

## Sobre quien manda
(Lo rellena quien manda, o Claude cuando se lo cuente. Así cualquier chat sabe con quién habla.)
- **Nombre:** <cómo quieres que te llame>
- **A qué te dedicas:** <…>
- **Tiempo para la fábrica:** <horas por semana>
- **Cómo prefieres que te hable:** <más corto, más explicado, con ejemplos…>

## Mapa
- `docs/` — `territorio.md`, `publico.md`, `biblia.md`, `lo-que-funciona.md`, `hipotesis.md`, `decisiones.md`,
  `criticos.md`, `backlog-visual.md`, `piezas.md` (todo lo que un guion puede activar y sus trampas),
  `anadir-una-pieza.md`.
- `ideas/` — `banco.jsonl` (todas las ideas, también las muertas con su motivo), `inbox.md`, `fuentes.md`, `rondas/`.
- `episodes/<slug>/` — cada episodio (`script.json`, `estado.md`, `critica.md`, `guion-v*.md`).
- `publicar/<slug>/` — lo listo para subir (vídeo A y B, texto, portada, `PARTE.md`).
- `metrics/` — números de tus reels; `reviews/` — informes de `/revision`; `references/` — lo que guardas del género.
- `personajes/<id>/personaje.json` — tus personajes como datos (guía: `docs/personajes.md`); `assets/` — reparto base, música, efectos, marca
  (`assets/brand/brand.json`); `reparto.json` — cómo se llaman tus personajes en los guiones.
- `style/guide.md` — cómo se escribe; `style/characters.md` — lo que el 3D sabe hacer con cada personaje.
- `curso/` — `comprobaciones.json` (lo que sella `/tarrito comprobar`), `progreso.json`, tus ejercicios.
- `reels/` (la CLI en Python), `blender/` (la escena 3D por código), `remotion/` (pantallas y montaje).

## Comandos (todos con `uv run reels …`)
- `doctor` — ¿está todo instalado? Da el comando exacto para tu sistema; `--prueba-render` mide la velocidad.
- `humo` — prueba gratis de punta a punta (vídeo de unos 6 s en `episodes/humo/`). `descargar-modelo` — el modelo de whisper (el "oído" que comprueba).
- `personaje <id>` — hoja de expresiones gratis (emociones, bocas, gestos, parpadeo). Enséñala antes de usar uno nuevo.
- `ejemplo <slug>` — episodios de ejemplo con voz ya grabada (`lampara-de-las-tres`, `cafeteria-moka`), gratis.
- `lint <slug>` — revisión gratis del guion; antes de cada gasto.
- `voice <slug>` — voces (`--only 3,7`, `--takes N` + `--pick N=k`, `--spaces` gratis). **Cuesta.**
- `build <slug>` — escena, pantallas y labios. `render <slug>` — Blender (`--quality preview --keyframes` = un
  fotograma por beat; `--cloud` = GPU alquilada, **cuesta**). Evita que la computadora se duerma.
- `preview <slug> --beats 2-4 --quality draft` · `animatic <slug>` (`--audio-only`) · `compose <slug>` ·
  `check <slug>` · `cover <slug> --beat N` · `sheet <slug> --start 0 --end 3`.
- Datos: `stats`, `comments` (API de Instagram, opcional), `review`, `calibrate`, `ref <video>`.

## Reparto
El 3D pone en escena dos papeles: el **humano** (hueco interno `novato`) y la **cosa** (hueco interno `claude`). Quién
los interpreta es un dato: cualquier `personajes/<id>/personaje.json` (o `assets/characters/<id>/character.json`) del
tipo adecuado (`role`: `humano` / `cosa`). Por defecto (`reparto.json`) son `prota` (una persona) y `taza` (una taza con cara); un guion elige los suyos
listándolos en `characters` (el primer humano y la primera cosa) o con `"reparto": {"humano": …, "cosa": …}`. En los
guiones valen el id del personaje, el papel, el nombre de `reparto.json` o el id interno. Cámaras con alias:
`closeup_humano`, `closeup_cosa`, `medium_humano_low`, `humano_asomado`.
Personajes nuevos: "objeto con cara" (`"placeholder": {"shape": "object"}` + bloque `object`: 10 formas, colores,
acabados, cara, brazos, accesorios) o humano (`"shape": "human"` + bloque `human`). Guía para el usuario y opciones:
`docs/personajes.md`. Comprueba siempre con `reels personaje <id>` y enseña la hoja. No copies el tarro de barro del curso (es la mascota de su marca).
Decorados: `habitacion` (por defecto: cuarto-escritorio, ventana a la ciudad de noche o de día) y los genéricos `estudio`, `mostrador` (cafetería / obrador), `exterior`, con
`set_options` (colores, variante; en `mostrador`, `pizarra`: lo que dice su pizarra, ver `docs/piezas.md`).
Con quien manda, habla de sus personajes por su nombre (`docs/biblia.md`).

## Arquitectura
- `script.json` es el contrato: cambiar un vídeo = cambiar el JSON y volver a renderizar.
- `emotion`, `action`, `camera`, `component` son enums cerrados de `reels/schema.py`: no inventes valores.
- La duración de cada beat sale del audio (`reels/timeline.py`), nunca del guion.
- `blender/` usa solo stdlib + `bpy` y nunca importa `reels/`.
