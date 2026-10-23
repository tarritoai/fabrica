# CLAUDE.md — tu fábrica 2D («¿Y si…?»)

## Reglas (siempre)
- **Responde siempre en español**, en lenguaje llano: quien manda puede no ser técnico. Español neutro, que se
  entienda en Latinoamérica y en España ("teléfono", "computadora"). Háblale de tú, sin dar por hecho su género.
- **Quien manda decide.** Las decisiones de gusto (idea, voz, dibujo, ritmo, publicar) son suyas. Tú recomiendas,
  con tu porqué; nunca eliges en silencio.
- **Avisa antes de gastar** (ver «Reglas de gasto»): nada de pago sin un sí claro con la cifra delante.
- Enseña fotogramas y vídeos en cuanto existan.
- Secretos solo en `.env` (fuera de git). **Nunca lo leas ni imprimas claves.**
- Nada de marcas, logos ni personas reales vivas en los dibujos. Obras con derechos (películas, series, libros
  recientes): solo con permiso; mejor **dominio público** (clásicos, cuentos, mitos, historia) u obras tuyas.
- **La fábrica nunca publica nada**: deja todo listo en `publicar/<slug>/` y lo sube quien manda.
- Reels de otras cuentas: solo los que guarda quien manda, a mano. Nunca descargues nada de nadie. Su estilo no se
  copia: esta fábrica tiene el suyo (`docs/estilo.md`).
- A git solo van código, documentos y `script.json`/`estado.md`: nada de audio, vídeo ni fotogramas.
- Código, identificadores y nombres de archivo en inglés; guiones y textos de los vídeos, en el idioma de la cuenta.

## Qué es esta fábrica
Una fábrica de reels verticales (1080×1920, 20–45 s) **dibujados por código**, en el formato «¿Y si…?»: una
pregunta que cambia una historia conocida, una escalera de consecuencias con un **contador**, un giro y un remate
con pregunta al público. Narrador rápido (voz de ElevenLabs) y réplicas cortas de personajes. Sin Blender, sin
gráfica: el dibujo es SVG en Remotion y se renderiza en minutos en cualquier computadora.

Es la misma receta que la fábrica 3D, con otro motor: una carpeta, estas reglas, unos trabajadores, unas puertas y
una voz. Trabajan 17 trabajadores (subagentes) y nadie decide salvo quien manda:
- **5 ideadores** · **1 jurado** · **5 espectadores** (`docs/publico.md`) · **editor de guion** · **oído** ·
  **ojo** · **cuidado** · **analista** · y el nuevo: **dibujante** (dibuja con el kit las piezas que una historia
  necesita). Están en `.claude/agents/`.
De qué va la cuenta: `docs/territorio.md`. Para quién: `docs/publico.md`. Sus personajes: `docs/biblia.md`.

## Las órdenes (skills de `.claude/skills/`)
| Orden | Para qué |
|---|---|
| `/humo` | prueba gratis: un reel de unos 6 s de punta a punta |
| `/nicho` | tu territorio y tu público con sus 5 espectadores |
| `/personaje` | un personaje dibujado (hoja de expresiones) o el narrador con su voz (biblioteca o voz diseñada) |
| `/ideas` | 5 ideadores → jurado → espectadores + cuidado → 5 finalistas con recomendación |
| `/episodio <idea>` | de la idea a `publicar/`, por capas y con puertas |
| `/numeros` | métricas a mano (lo que ves en Instagram, TikTok o YouTube) |
| `/revision` | qué hemos aprendido esta semana |
| `/calibrar` | cuánto aciertan los críticos (con ≥ 8 reels con datos) |
| `/referencias` | aprender del género con reels que guardas tú |
| `/tarrito` | dónde vas; `/tarrito comprobar` sella cada lote del curso |

## Cómo se trabaja: por capas, de barato a caro
Cada error se caza en la capa más barata: comprobación por código (gratis) → críticos (suscripción) → quien manda →
gasto. Ninguna capa empieza sin el OK (✋) de la anterior:
0. **Ideas** → elige una. 1. **Guion** en tabla + revisores → OK. 1b. **Piezas nuevas** (el dibujante dibuja lo que
falte; hoja de personaje) → OK. 2. **Voz** (cuesta) → OK. 3. **Fotogramas clave** + ojo (gratis) → OK.
4. **Vídeo** + comprobación + gancho B → OK a publicar (lo sube quien manda). El detalle está en `/episodio`.
Cada corrección de quien manda se apunta en `docs/decisiones.md`; `/revision` las convierte en reglas.

## Reglas de gasto
- **Cuesta dinero** (créditos de ElevenLabs): `reels voice`, `reels voice-design`, `reels voice-try`,
  `reels voice-act`, `reels sfx-gen`, `reels music-gen`. **Gratis**: todo lo demás (dibujo, render, comprobaciones).
- **Antes de gastar**: `uv run reels voice <slug> --estimar` (créditos como mucho), mira el saldo
  (`uv run reels doctor`) y pregunta con las cifras. Si no hay para el episodio + un 30 % de retoques, para.
- Apunta cada gasto en `episodes/<slug>/estado.md`.
- Las voces se guardan en `.cache/voice/`: **no la borres** (repetir una toma igual no se vuelve a cobrar).
- La suscripción de Claude también tiene límite (ventanas de 5 h): `/ideas` y `/episodio` lanzan varios trabajadores
  y el dibujante gasta bastante cuando dibuja personajes nuevos. Modo **ligero** por defecto; avisa antes. `/usage`.
- Si existe la variable `ANTHROPIC_API_KEY`, Claude Code cobra por API en vez de usar la suscripción: avisa.

## Cómo retomar (chats nuevos)
- Lo aprendido vive en la carpeta, no en el chat. Cada episodio guarda dónde va en `episodes/<slug>/estado.md`:
  en un chat nuevo, `/episodio <slug>` sigue desde la última puerta.
- Tras cada puerta, propón seguir en un chat nuevo (más rápido y gasta menos).
- Al empezar un chat de trabajo, lee este archivo y, según la tarea, `docs/territorio.md`, `docs/biblia.md`,
  `docs/formato.md`, `docs/lo-que-funciona.md`, `docs/hipotesis.md` y `docs/decisiones.md`. Para un guion, también
  `docs/piezas.md`.

## Sobre quien manda
(Lo rellena quien manda, o Claude cuando se lo cuente. Así cualquier chat sabe con quién habla.)
- **Nombre:** <cómo quieres que te llame>
- **A qué te dedicas:** <…>
- **Tiempo para la fábrica:** <horas por semana>
- **Cómo prefieres que te hable:** <más corto, más explicado, con ejemplos…>

## Mapa
- `docs/` — `territorio.md`, `publico.md`, `biblia.md`, `formato.md` (cómo es un «¿Y si…?»), `estilo.md` (el estilo
  de la casa y sus paletas), `piezas.md` (todo lo que un guion puede pedir), `anadir-una-pieza.md`,
  `lo-que-funciona.md`, `hipotesis.md`, `decisiones.md`, `criticos.md`, `backlog-visual.md`.
- `ideas/` — `banco.jsonl` (todas las ideas, también las muertas con su motivo), `inbox.md`, `fuentes.md`, `rondas/`.
- `episodes/<slug>/` — cada episodio (`script.json`, `estado.md`, `critica.md`, `guion-v*.md`; lo demás se regenera).
- `publicar/<slug>/` — lo listo para subir (vídeo A y B, texto, portada, carrusel).
- `personajes/<id>/personaje.json` — tus personajes y tu narrador (pieza, aspecto, voz).
- `remotion/src/` — el dibujo: `kit/` (el estilo de la casa: no se toca sin pedirlo), `piezas/` (fondos, Persona,
  Animal, Cosa, Objeto, Casa, Telefono), `personajes/` (los que dibuja el dibujante para ti), `episodios/<slug>/`
  (piezas de una historia). Hojas de piezas: `hojas/`.
- `assets/` — efectos (`sfx/`), música con licencia (`music/music.json`), ejemplos con voz ya grabada, marca.
- `curso/` — `comprobaciones.json` (lo que sella `/tarrito comprobar`), `progreso.json`.
- `reels/` — la CLI en Python.

## Comandos (todos con `uv run reels …`)
- `doctor` — ¿está todo? · `humo` — prueba gratis · `ejemplo quijote-gafas` — el reel de ejemplo, con voces ya
  grabadas (gratis; `--fotogramas` para ver solo los fotogramas clave).
- `lint <slug>` — revisión gratis del guion · `voice <slug>` (`--estimar` no gasta) — voces, **cuesta**.
- `build <slug>` — tiempos · `stills <slug>` — fotogramas clave + hoja (`--sin-voz`: boceto gratis antes de
  pagar voces) · `render <slug>` (`--borrador`) — el vídeo
  · `check <slug>` — whisper comprueba cada frase · `sheet <slug> --start 0 --end 3` — hoja de un tramo.
- `cover <slug> --beat N` — portada · `carousel <slug>` — carrusel de Instagram (gratis).
- `personaje <id|Pieza>` — hoja de expresiones y poses (gratis) · `piezas` — comprueba el código de las piezas.
- Voces: `voice-search` (gratis), `voice-use`, `voice-design` (**cuesta**), `voice-save`, `voice-try` (**cuesta**),
  `voice-act <slug> <beat> <grabación>` («actúalo tú», **cuesta**).
- Sonido: `sfx-gen`, `music-gen` (**cuestan**), `music-import` (tu pista con licencia).
- Datos: `review`, `calibrate`.

## Arquitectura
- `script.json` es el contrato (`reels/schema.py`): cambiar un vídeo = cambiar el JSON y volver a renderizar.
- La duración de todo sale de la voz (`reels/timeline.py`): los eventos se cuelgan de **palabras** («el sello cae en
  "molino"»), nunca de segundos escritos a mano.
- `type` de los eventos, `scene` y `piece` son vocabularios cerrados (`docs/piezas.md`): no inventes valores. Si
  hace falta algo que no existe, lo dibuja el **dibujante** (capa 1b) y se enseña antes de usarlo.
- `remotion/src/kit/` es el estilo de la casa: papel recortado, línea de tinta, sombra dura. Las piezas nuevas se
  dibujan con sus primitivas (`Limb`, `Eye`, `Mouth`, `Brow`…), nunca con otro estilo.
