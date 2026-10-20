# Catálogo de piezas

Todo lo que se puede activar en un `episodes/<slug>/script.json`. Una pieza = un campo del JSON; el pipeline hace el resto.
La fuente técnica es `reels/schema.py` (valores exactos y validación). Este archivo explica **qué hace, cuándo usarla y sus trampas**.
El guionista automático (`reels/writer.py`) lo lee entero: si añades o cambias una pieza, actualiza este archivo (ver `docs/anadir-una-pieza.md`).

Los ejemplos ("p. ej.") describen situaciones de muestra, no episodios concretos. Cuando tengas episodios propios, puedes
apuntar al lado de cada pieza el slug donde se ve funcionando (`publicar/<slug>/<slug>.mp4`).

**Reparto por alias** (`reparto.json`): en los guiones el humano se puede escribir `prota` / `humano` / `novato` y la cosa
`taza` / `cosa` / `claude` (o el nombre de tu cosa). Las cámaras admiten alias de papel (`closeup_humano`, `closeup_cosa`, `medium_humano_low`…), y
`humano_fuera` vale por `novato_away`. Abajo se usan los ids internos (`novato`, `claude`, `closeup_ai`…) porque son los
del código; los alias valen igual.

---

## 1. Episodio (nivel superior)

| Campo | Qué es |
|---|---|
| `slug`, `title`, `premise` | id kebab-case, título, resumen de la historia (útil para el siguiente que lo lea) |
| `tone` | `agridulce`, `comedia`, `serie` |
| `characters` | reparto: 1–3 en cámara + como mucho una voz fuera de cámara. El primer humano de la lista hace de **humano** y la primera cosa, de **cosa** (§8). `habitacion` necesita al humano |
| `reparto` | opcional: fuerza quién hace cada papel, p. ej. `{"humano": "estudiante", "cosa": "lucio"}` |
| `set` | `habitacion` (**por defecto**: el cuarto-escritorio con ventana a una ciudad de noche o de día; `set_options`: `window` `noche`/`dia`, `wall`, `floor`, `desk`, `rug`, `chair`, `curtains`, `posters`, `poster_colors`, `corcho`, `shelf`, `plants`, `sofa`, `apuntes`, `city`), `escritorio_noche` (guiones antiguos: el mismo cuarto de noche), y los genéricos: `estudio` (fondo infinito de un color y peana: explicativos, producto), `mostrador` (barra de cafetería u obrador, de día: el humano detrás, la cosa encima) y `exterior` (parque de día, la cosa en un tocón) |
| `set_options` | solo decorados genéricos: colores y opciones. `estudio`: `background`, `floor`, `plinth`, `plinth_on`, `key`. `mostrador`: `variant` (`cafeteria` / `obrador`), `wall`, `counter`, `top`, `accent`, `floor`, `daylight`. `exterior`: `grass`, `sky`, `path`, `trees`, `bench`, `stump` |
| `music` | ver §7 |
| `alt_hooks`, `loop_hint` | dos ganchos alternativos y cómo enlaza el final con el principio |
| `beats` | la lista de planos (§2). **El último beat siempre es mudo.** |

## 2. Beat (un plano)

| Campo | Qué es | Notas |
|---|---|---|
| `id` | entero único | Los audios se guardan como `audio/beat_NN.*`: **renumerar beats obliga a regenerar todas las voces** (≈1.900 créditos). Si insertas un plano, mejor reutiliza ids o asume el coste. |
| `speaker` + `line` | quién habla y qué dice | **Máximo 8 palabras** (`MAX_WORDS_PER_LINE`). Si no cabe, parte la frase en dos beats consecutivos del mismo personaje. Ambos `null` = beat mudo. |
| `delivery` | dirección de voz | ver §6 |
| `reactor` | en beats mudos, de quién es la cara que reacciona | por defecto el prota; nunca un personaje fuera de cámara |
| `emotion` / `listener_emotion` | cara del que habla / de los demás | `neutral, orgulloso, confuso, alarma, juzgando, hundido, panico, aliviado` (`aliviado` = sonrisa) |
| `action` | gesto | `idle, talk_gesture, present_gesture, shrug, facepalm, lean_in, look_phone, phone_ear, recoil, slump`; cada personaje solo admite las de su `character.json` |
| `camera` | plano | ver §3 |
| `event` | pantalla | ver §4 |
| `sfx` | efectos | `ding, ding_alarm, whoosh, error, tension, typing_tiny, click` (pulsar ↻, uno por clic con `sfx_at`), `toc` (aparece una copia, en el corte), `cadena` / `grifo` (la cisterna / el grifo en el cuarto de al lado); nuevos con `reels sfx-gen` |
| `hold` | segundos de silencio tras la frase | 0.1 en frases normales; beats mudos ≥ 0.8 (1.2–3.4 en momentos que pesan) |

## 3. Cámaras (`camera`)

| Valor | Plano | Cuándo |
|---|---|---|
| `two_shot` | los dos personajes | situar, apagones (ver a los dos a oscuras) |
| `closeup_novato` / `closeup_ai` (alias `closeup_humano` / `closeup_cosa`) | primeros planos | lo normal; `closeup_ai` encuadra a la cosa del reparto |
| `medium_novato_low` (alias `medium_humano_low`) | el prota en contrapicado | confianza, chulería |
| `establishing` | llega desde la galaxia hasta la habitación | beat 1 cuando el gancho se oye (no si el gancho es una pantalla) |
| `wide_space` | la isla sola en el espacio, alejándose | silencios que pesan y último plano; máx. 2–3 por vídeo |
| `screen_closeup` | POV del prota sobre el portátil, texto legible | pantallas de portátil (§4) |
| `over_shoulder` | detrás del prota: pantalla + la cosa al lado | |
| `phone_screen` | **de frente a la pantalla del móvil, la llena** | ganchos que se tienen que **leer** (p. ej. un aviso en el beat 1). El pulgar tapa la parte de abajo: lo importante arriba |
| `phone_closeup` | por encima del hombro mirando el móvil | ambiente, llamadas ("Mamá"); el texto pequeño no se lee |
| `closeup_other` / `medium_other` | el compañero de piso (`hugo`) | cuando hay un tercer personaje en el sofá |
| `wide_room` | el cuarto entero de frente: mesa, estantería, caja y suelo | las copias de la cosa (`ai_copies`); el mismo encuadre con más copias = escalada que se lee sin sonido |
| `closeup_mini` | la cosa en mini detrás de la taza, de cerca | solo con `ai_mini` |
| `humano_asomado` | contraplano: el prota asomado a una luz, iluminado por ella | set `mundo` |
| `robot_reveal`, `robot_pov`, `standoff`, `wide_epic` | el futuro con el robot gigante | solo con `ambience: ruinas` |

Repetir la misma `camera` en beats consecutivos = un plano continuo (sin corte). Cortar en las reacciones, no en cada frase.

## 4. Pantallas (`event`)

Las de móvil y portátil se renderizan con Remotion (`remotion/src/screens/`) y se mapean como textura en Blender. **Una pantalla se queda puesta hasta el siguiente beat con evento del mismo dispositivo**: si la batería tiene que cambiar, cada beat lleva su propio evento.

### Portátil (se ven con `screen_closeup`, `over_shoulder` o de fondo)
- **`SystemNotice`** — mensaje de sistema sobrio. Tres modos:
  - aviso: `{"title": "Aviso", "text": "Esta versión se retira el 31 de octubre."}`
  - cuenta atrás real: `"countdown_from": 7` (segundos al empezar el beat; p. ej. llega a 0 justo en un apagón)
  - batería: `"battery": 9` (verde > 10, naranja ≤ 10, rojo ≤ 3; **0 = pantalla negra**). Bajarla frase a frase convierte la batería en el reloj de la historia.
- **`MemorySave`** — la cosa escribe en su memoria. `lines`, `from_char`/`to_char` para repartir una frase entre planos. Si el beat tiene frase, **la escritura sigue a la voz y no hay subtítulo** (una nota "leída" en voz alta). Hace scroll y enseña las 2 últimas notas.
- **`LaptopChat`** — chat con una IA genérica abierto en el portátil (`app_name`, `messages`, `code` opcional debajo de la última respuesta). Se lee en `screen_closeup`; se queda puesta todo el episodio si no hay otra pantalla de portátil. Sin marcas: "Asistente" (p. ej. "¡Tienes toda la razón! 😊"). `theme`: `neutral` (oscuro genérico, por defecto), `tarro` (crema con el barro y el esmalte del tarro y el tarrito de icono: se lee como el chat del tarro) o `tarro_noche` (cálido oscuro). Nunca un logo oficial. `text_scale` (1 por defecto): ~1,35 para un chat corto que tiene que leerse en el móvil en el primer segundo; con mensajes largos o código, 1. Con el tema claro la pantalla emite menos (si no, sale blanca). Con `variant: n` sale el botón ↻ y el contador "n/n" bajo la última respuesta; cada segundo de `regen_at` pulsa el botón, sube el contador y la respuesta vuelve a aparecer (pon un `click` con el mismo `sfx_at`). En cada pulsación la mano derecha del prota va al trackpad y da un toque (`rigs/arms.py`); el botón y el contador son grandes para que se lean en el móvil. Para que el contador siga subiendo, cada beat que pulsa lleva su propio evento con el `variant` donde lo dejó el anterior (p. ej. 1 → 2 → 5 → 12, igual que los tarros). `over_shoulder` con la cosa al lado no funciona bien (la cabeza del prota la tapa).
- **`StreamProfiles`** — selector "¿Quién está viendo?" de una plataforma de streaming inventada ("CINEO") en el portátil: `profiles` (`name`, `color`, `is_new` = recuadro + etiqueta "Nuevo") y `new_at` (segundos en que aparece el nuevo). En `screen_closeup`, cortando justo en la frase que lo revela. La marca real solo se nombra en el diálogo, nunca en pantalla. Ojo: sin emojis (la fuente no los tiene).
- **`DateGlitch`** — pantalla rota en una fecha (`"date": "2049"`, `broken`): salto en el tiempo.

### Móvil
- **`PhoneNotifications`** — avisos que entran en escalada de azul a rojo (el más nuevo arriba). Con `messages: [{app, text}]` son avisos de texto (p. ej. "Apagón general en todo el país"); con `items` + `app_name` son cobros. Va con `phone_screen` si se tienen que leer; pon el aviso más fuerte **el último** (queda arriba). Un `sfx` por aviso. Los emojis en `app`/`text` sí salen: la pantalla usa la fuente de emojis del sistema (se pinta en local, también para `--cloud`); en Linux, `reels doctor` te dice cómo instalarla. Un contacto con emoji (p. ej. «Ex 💔») dice quién es sin nombrarlo antes.
- **`PhoneCall`** — llamada (`contact`, `connect_after`; `null` = nadie contesta). Deja el móvil en la oreja. La voz del otro lado es un personaje fuera de cámara (`mama`, con EQ de teléfono).
- **`PhoneChat`** — chat con un asistente genérico en el móvil de alguien (`owner`, `messages`, `last_at`). No añade tiempo.

### Overlay (encima del vídeo)
- **`CounterReveal`** — tarjeta con un número que sube. Ojo: una tarjeta encima "cambia la escena"; muchas veces queda mejor decir el dato en el diálogo.

## 5. Actuación, luz y ambiente (por beat)

| Campo | Valores | Qué hace | Trampas |
|---|---|---|---|
| `tears` + `tear_at` | `wet` / `tear` | ojos húmedos / además cae una lágrima por la mejilla (solo el prota) | **Hay que repetirlo en cada beat**: sin él los ojos se secan de golpe en el siguiente plano. `tear` solo en 1–2 momentos (una lágrima en la sonrisa final suele sobrar). |
| `ai_power` + `ai_power_at` | `off` / `on` | la cosa se apaga (ojos cerrados, luz interior muerta, se hunde) / arranca con parpadeo | pésalo con `light_snap` y corte de música (§7). Arrancar en `closeup_ai` con `hold` ~2 s. |
| `light` + `light_snap` | `noche` (defecto), `madrugada`, `tibio`, `calido`, `amanecer`, `apagon`, `oscuro`, `ruinas` | luz de la habitación desde ese beat (fundido 3 s; `light_snap` = corte en 2 fotogramas; `light_at` = segundos dentro del beat en que empieza el cambio) | Coherencia: en un apagón no vale `tibio` (enciende la lámpara). `apagon` = solo ilumina la pantalla; `oscuro` = ni eso (la ranura de la tapa del tarro brilla ×2,5: es la única luz); `amanecer` = vuelve todo, dorado; `madrugada` = cuarto en sombra, la pantalla y la lámpara baja llevan la luz (desde el beat 1 con `light_snap: true`). |
| `ambience` | `noche`, `calma`, `ruinas` | sonido de fondo; `ruinas` además **cambia el set al futuro** (escombros, sirena, robot) | |
| `nonverbal` + `nonverbal_at` | `risa`, `suspiro` | sonido sin palabras con la voz del personaje en un beat mudo | se genera con `reels voice <slug> --nonverbal` |
| `memento` / `mementos` | `cv, caja, reloj, taza` / `away`, `keep` | recuerdos que flotan alrededor del prota y se van (o uno vuelve a la cosa) | pueden quedar raros; usar con cuidado. |
| `ai_copies` / `ai_mini` | `1`–`12` / `true`, `false` | cuántas copias iguales de la cosa hay en el cuarto desde ese beat (1 = solo la cosa) y si está el mini detrás de la taza | Aparecen en el corte, sin animación (córtalo con `wide_room` o `two_shot`; nunca cambies el número dentro de un plano continuo). Miran al prota solos; caben 2 en `two_shot`, el resto se ve en `wide_room`. Con copias, la mesa pierde el altavoz, la planta, los libros y la papelera, y cada tarro da su propia luz cálida por la tapa (nada de barro emisivo: aplana el modelado). Sitios en `sets.py` (`copy_spots`). |
| `action: turn_away` | (acción) | la cosa se gira medio de espaldas, barbilla arriba, ofendida; vuelve en el beat siguiente | se lee en `two_shot` (p. ej. "Pues nada. Vuelve con ella."). |
| `action: close_laptop` | (acción, prota) | baja la tapa del portátil con la mano derecha (12 fotogramas) y se queda cerrado; después ya no teclea | la tapa cae en `light_at` si lo hay, si no al acabar su frase. Con `light: oscuro` + `light_snap` + `light_at` justo tras la frase y `hold` ~0,7, el cuarto se apaga al cerrar. |
| `action: phone_down` | (acción, prota) | deja el móvil boca abajo (lo gira al bajarlo); se queda así | con el portátil cerrado lo deja encima, delante de él, y se ve en `closeup_novato`; si no, va a su sitio de la mesa (fuera de cuadro). `hold` ~2 s para que dé tiempo y se vea la sonrisa (buena coda). |
| `action: phone_lower` | (acción, prota) | baja el móvil que está leyendo a la altura de la tripa y lo sigue sujetando (pantalla encendida, cara despejada); no lo suelta hasta otra acción de móvil | para reaccionar con el móvil aún en la mano: con `look_phone` el móvil le tapa la boca en `closeup_novato`. Sirve para una coda en la que sonríe sin soltarlo. |
| luz del móvil (automática) | — | en `oscuro`/`apagon`, el móvil da una luz fría desde que llega un aviso (`PhoneNotifications`/`PhoneCall`) hasta que se deja boca abajo | encima de la mesa se ve desde lejos que se enciende, y en la mano le ilumina la cara desde abajo (`build_scene.phone_glow`). |
| `cut_camera` + `cut_at` | una cámara del enum + segundos | segundo plano dentro del mismo beat, desde `cut_at` | para ver algo que pasa al final de una frase sin partir la voz (p. ej. cara del prota → pantalla en «Otra.» para ver el contador correr). Con `cut_camera: phone_screen` en un beat de aviso, el prota coge el móvil justo para tenerlo quieto en el corte: primero se ve sonar y encenderse sobre la mesa (p. ej. `two_shot` → `phone_screen` en 1,3 s; si no, la pantalla del móvil se abre sin ninguna interacción). Los `regen_at` tienen que caber antes del final del beat: si la siguiente frase tiene voz, el `hold` se recorta. |
| `novato_away` (alias `humano_fuera`) | `true` / `false` (desde ese beat) | el prota se ha ido del cuarto con el portátil: silla vacía, sin portátil ni su luz en la mesa; sus frases suenan desde el baño (espacio de voz `bano`: eco de azulejos tras una puerta, gratis con `reels voice --spaces`) y los demás miran hacia donde viene su voz (`_door`, a la izquierda del cuadro, pasado el sofá). `false` = ha vuelto | vuelve/se va en el corte, sin animación. `closeup_novato` no tiene sentido mientras está fuera. Con `cadena` / `grifo` (sfx) se cuenta lo que hace sin verlo. |
| `ai_move` (+ `_at`, `_instant`) | `laptop`, `front`, `back` | la cosa va al portátil, se pone delante del prota o vuelve | verla caminar a saltitos no queda real; `front` funciona bien. |

Gesto nuevo: `action: stretch` (se despereza con los brazos arriba; una lámpara estira el brazo). Solo lo usan los
personajes que lo tienen en su lista `actions`.

## 6. Voz (`delivery`)

Modelo: **Eleven v4** (`MODEL` en `reels/voice.py`). Comprueba el acento de cada voz en v4 con una frase de prueba antes de usarla (el acento puede cambiar entre modelos). Antes de usar una voz nueva, comprueba en `GET /v1/voices/<id>` → `verified_languages` que tiene `es`/`peninsular` con `eleven_v4`.

**Cómo se escribe una frase para v4** (el ritmo sale de cómo está escrita la frase: **v4 ignora el ajuste de velocidad** y no se acelera nada después; la voz se usa tal cual sale):
- **Puntuación = ritmo.** v4 hace una pausa en cada punto. Comas donde la frase va de corrido, puntos solo donde tiene que respirar. Sin correr por correr: si la frase pide una pausa, va (una misma frase con puntos puede durar 3,1 s y con comas 2,8 s).
- Pausas escritas: `...`, `[short pause]`, `[long pause]`. Énfasis: **una** palabra en mayúsculas ("Que NO.").
- Etiquetas que **describen la voz** (`[flat, bored voice]`, `[low, tired voice]`) mejor que la emoción a secas; en `spoken` valen libres. Ritmo con etiqueta: `[rushed]`, `[fast-talking]`, `[slowly]` (con `pace` se añade sola si no hay `spoken`).
- Trampas de las etiquetas: los adverbios y frases largas dentro de la etiqueta se leen en voz alta (`[deadpan, unimpressed, instantly, a tiny bit amused]` → «Instantly. A tiny bit amused. No.»): 2–3 adjetivos cortos. Un «No.» suelto en toma suelta tiende a salir doble («No. No.»): sacar 3 tomas y comprobar con whisper.
- Interrumpir: la frase cortada acaba en `-` y la siguiente puede empezar con `[jumping in]` / `[interrupting]`. Cambia cómo se dice, pero el montaje sigue poniendo los turnos uno detrás de otro (no se solapan).
- Acento: con v4 no suele hacer falta; si se cuela, `[strong Castilian Spanish accent]` en `spoken` y elegir toma.
- Pronunciación de una palabra rara: IPA entre barras (`/ˈklɔːd/`).
- Las tomas sueltas (`--only`, `--takes`, el coro, las regeneradas) se piden con la frase de antes y la de después (`previous_text` / `next_text`) para que contesten a la escena. Por eso una semilla elegida con `--pick` solo da la misma toma si las frases de alrededor no cambian.
- No sirve: el ajuste `speed` (v4 lo ignora: la misma toma dura igual a 0,7 y a 1,2; solo funciona en multilingual v2, que no lleva etiquetas), el `style`, el SSML `<break>`, ni el voz a voz con grabaciones propias (no dio buen resultado).

| Campo | Qué hace |
|---|---|
| `tags` | 0–2 audio tags: `whispers, sighs, sarcastic, curious, laughs, excited, crying, terrified, nervous, chuckles, softly, emotional, concerned`. Para cualquier otra, `spoken` |
| `pace`, `intensity` | `lento/normal/rapido` (llega a la voz como `[slowly]`/`[rushed]` si no hay `spoken`; con `spoken`, escríbelo dentro), `baja/media/alta` |
| `pause_before` | silencio antes de la frase (se respeta en el montaje). Solo 2–3 por vídeo, en lo que duele. |
| `creative` + `spoken` | emociones fuertes: estabilidad creativa + texto exacto para la voz (`"[voice breaking] Para… Que se te acaba."`); el subtítulo usa `line` limpia |
| `seed` | toma fijada a oído (`reels voice --takes N` → `--pick N=k`); nunca se pisa |
| `max_gap` | acorta pausas internas de la toma (último recurso: mejor arreglar la puntuación) |
| `chorus` | frases de la cosa: N voces. Cada copia es **una toma suelta distinta** (`voice_chorus`, semillas 7000+, se rehace si no dice su frase), alineada con la principal tramo a tramo por sus pausas y colocada en estéreo donde está su tarro (`COPY_SPOTS`, copia de `copy_spots` de `sets.py`: si mueves los tarros, actualízalo). La mezcla es gratis y se rehace con `reels voice --spaces`. Coste: (N−1) × la frase por beat. En Blender todas las copias visibles mueven la boca |
| `mini` | la frase la dice la cosa en mini: la misma toma +4,5 semitonos con `rubberband` (si falta, `reels doctor` te dice cómo instalarlo en tu sistema), que conserva el timbre: la cosa en pequeño, no una ardilla. Solo él mueve la boca (la cosa lo mira) |

Trampas de voz:
- **Acento latino / seseo** (pasaba con v3): con v4 no debería pasar. Si pasa, `[strong Castilian Spanish accent]` en `spoken` y elegir toma.
- Palabras raras ("jajaja") suenan mal: evítalas.
- whisper a veces oye mal ("ha sido" por "has sido"; "Claude" → "Clothes"; "en visto" → "embisto" cuando va rápido): `reels check` puede dar falsos avisos, comprobar de oído.
- Cortes por beat (`whisper_words`): whisper.cpp ≥ 1.8 trae la flash attention activada y con ella DTW devuelve `t_dtw = -1` sin avisar; los `offsets` de los segmentos caen en segundos enteros. Por eso va con `-nfa`, toma los tiempos de `t_dtw` y transcribe a trozos de ≤ 4 s cortados en silencios (con DTW, un audio largo entra en bucle: «¡Otra!» ×18). Si de pronto muchos beats salen "regenerada" en un diálogo que suena bien, sospecha primero de esto.
- **Un sfx generado puede salir casi mudo** (p. ej. −48 dB): mide su volumen (`ffmpeg -af volumedetect`) antes de enseñarlo.
- Coste: voz completa ≈ 1.900 créditos (sin coro); `--only` de 5 frases ≈ 750; `--takes` ≈ 100–150. **Valida el JSON antes de lanzar voces** (si falla la validación y el comando sigue, regenera lo viejo y se tiran créditos).

## 7. Música (`music`)

| Campo | Qué hace |
|---|---|
| `mood` | `epica`, `agridulce`, `chill`, `tension`, `comedia` (elige clip de `assets/music/music.json`) |
| `track` | fija un clip concreto (`"clips/<archivo>.mp3"`, tal como aparece en `music.json`) |
| `start_at_beat` + `fade_in` | dónde entra y en cuántos segundos |
| `cut_at_beat` | corte seco (apagón, giro) |
| `resume_at_beat` | vuelve como si nunca hubiera parado |
| `swell_at_beat` + `swell_level` | sube (0.6 suave … 1.0 a tope) |
| `align_end` | el final de la pista cae en el último fotograma (clímax incorporado) |

Patrón que funciona en los agridulces: entra suave cuando empieza lo emotivo → corte seco en el apagón → vuelve en la frase de la resurrección → swell en la reacción final, con `align_end`.
Pistas nuevas: `reels music-import`; la licencia tiene que estar verificada para publicar (si no, compose avisa).

## 8. Personajes

Los dos papeles son **el humano** y **la cosa**. Quién los interpreta es un dato: cualquier carpeta de
`personajes/<id>/personaje.json` (o de la plantilla, `assets/characters/`) del tipo adecuado. Por defecto (`reparto.json`)
el humano es el prota y la cosa, la taza; un guion elige los suyos poniéndolos en `characters` o en `reparto`. En
`script.json` valen el id del personaje (`lucio`), el papel (`humano` / `cosa`), el nombre de `reparto.json` o el interno
(`novato` / `claude`, que son los huecos del 3D). Cómo crear uno: `docs/personajes.md`. Hoja de expresiones gratis:
`uv run reels personaje <id>`.

Personajes de ejemplo en `personajes/`: `lucio` (lámpara de escritorio: la pantalla es la cabeza, el brazo y la luz
actúan; `ai_power: off` = la apagan), `estudiante` (humana, gafas, media melena), `moka` (cafetera italiana: la tapa
se abre al asustarse y castañea al hablar, echa vapor) y `barista` (humano con delantal).

| id interno | Quién | Notas |
|---|---|---|
| `novato` | hueco del humano (por defecto lo hace `prota`; alias `humano`) | protagonista; tiene móvil; lágrimas |
| `claude` | hueco de la cosa (por defecto lo hace `taza`, una taza con cara; alias `cosa`) | lo que actúe su forma (tapa, brazo, luz…) |
| `hugo` | compañero de piso | en el sofá; `PhoneChat` con `owner: hugo` |
| `chica` | otra humana de reparto | |
| `mama` | voz por teléfono | fuera de cámara; solo durante `PhoneCall` |
| `voz_*` | voces sueltas (con acento) | solo voz |
| `robot` | robot gigante del futuro | silueta del set `ruinas` |

Biblia completa: `style/characters.md`. Voces y aspecto: `assets/characters/<id>/character.json`.
