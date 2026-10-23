# Piezas: todo lo que un guion puede pedir

Un `script.json` 2D pide **fondos** (`shot.scene`), **actores** (`shot.actors[].piece` con sus `props`) y **eventos**
colgados de palabras. Aquí está lo que existe. Si una historia necesita otra cosa, la dibuja el **dibujante**
(`docs/anadir-una-pieza.md`) y se enseña con `uv run reels personaje <Pieza>` antes de usarla. El linter avisa si
algo no existe. Coordenadas: el cuadro mide 1080×1920; los pies de un personaje van en y ≈ 1400–1460; la cara del
que habla, por encima de y ≈ 1300 (debajo van los subtítulos); la zona segura del teléfono es x 120–960, y 300–1560.

## Fondos (`shot.scene` + `shot.options`)
| Fondo | Qué es | Opciones |
|---|---|---|
| `Campo` | cielo, sol o luna, nubes, dos lomas, suelo y camino | `hora` (dia, tarde, noche), `cielo`, `loma`, `loma_cerca`, `suelo`, `sol`, `nubes`, `camino`, `horizonte` |
| `Interior` | habitación: pared, zócalo, suelo de madera | `patron` (rayas, liso, ladrillo, azulejo), `pared`, `raya`, `suelo`, `ventana`, `ventana_x`, `vista` (dia, tarde, noche), `puerta`, `puerta_x`, `cuadro` |
| `Ciudad` | calle con edificios y ventanas | `hora`, `cielo`, `suelo`, `horizonte` |
| `Mar` | mar con olas que se mueven | `hora`, `cielo`, `agua`, `horizonte` |
| `Noche` | cielo con estrellas, luna y una loma | `cielo`, `suelo` |
| `Bosque` | el Campo más verde con pinos lejos y dos grandes a los lados | las del Campo + `pinos` (color), `arboles` |
| `Trama` | color plano con trama de puntos (títulos, primeros planos, gritos) | `color`, `puntos`, `cx`, `cy` |
| `Papel` | papel liso o un color | `color` |

## Actores genéricos (`piece` + `props`)
**`Persona`** — el muñeco de la casa, por parámetros (unos 470 px de alto a escala 1):
- cuerpo: `cuerpo` (normal, alto, ancho, peque), `piel` (`pieles.0`…`pieles.4` o #hex);
- ropa: `ropa` (camisa, vestido, tunica, traje, armadura, sudadera), `color`, `color2`, `zapatos`, `medias`;
- cabeza: `pelo` (corto, flequillo, punta, rizos, largo, moño, coleta, calvo), `pelo_color` (`pelos.0`…`pelos.5`),
  `barba` (no, barba, bigote, perilla, tres_dias), `sombrero` (gorro, sombrero, corona, pañuelo, gorra, casco),
  `sombrero_color`, `gafas` (0–1: si cambia, caen o suben);
- cara: `expresion` (neutral, alegre, risa, triste, enfado, sorpresa, miedo, picaro, aburrido, ilusion, decepcion,
  loco, orgullo, dormido), `mira` (−1 izquierda … 1 derecha);
- cuentos: `capa` y `capucha` (true) con `capa_color` (Caperucita, un monje, un mago);
- cuerpo en acción: `pose` (quieto, saluda, señala, brazos_arriba, jarras, cruzado, piensa, encoge, alcanza, sujeta,
  carga), `hacia` (1 / −1: a qué lado señala), `objetivo` [x, y] (con `alcanza`: la mano va a ese punto del cuadro),
  `sostiene` (gafas, libro, carta, telefono, taza, flor, lanza, saco, llave, cesta, hacha, espada, vela, varita,
  paraguas, bolsa);
- `gag` alrededor de la cabeza: moscas, olor, corazones, sudor, zzz, idea, rabia, estrellas.

**`Cosa`** — un objeto con cara: `forma` (taza, bote, caja, bola, botella, libro, telefono, maceta), `tamano`,
`color`, `color2`, `expresion` (las mismas), `pose` (quieto, saluda, brazos_arriba, señala, jarras, encoge),
`hacia`, `brazos`, `piernas`, `mira`, `sostiene`.

**`Animal`** — un animal que actúa como una persona (fábulas, cuentos, el gato de casa): `especie` (lobo, zorro,
gato, perro, oso, cerdo, conejo, raton), `color`, `color2` (barriga), `ropa` (nada, camisa, pantalon, traje,
vestido, pañuelo), `ropa_color`, `expresion` (las de Persona), `pose` (quieto, saluda, señala, brazos_arriba, jarras,
cruzado, encoge, sujeta), `hacia`, `mira`, `sostiene`, `gag`.

**`Objeto`** — una cosa suelta: `que` (reloj, calendario, cartel, corazon y todo lo de `sostiene`), `color`,
`texto` (calendario, cartel), `mes`.

**`Casa`** — casita vista desde fuera (~560 px) con chimenea que echa humo: `pared`, `tejado`, `luz` (ventanas
encendidas), `humo`, `cartel` (texto).

**`Telefono`** — un teléfono gigante (~780 px de alto: escala 0.6–0.9) con pantalla: `pantalla` (mapa, chat,
notificacion, llamada, texto), `titulo`; mapa: `ruta` (0–1: un `act` que la sube la dibuja), `minutos`; chat:
`mensajes` ([{"de": "yo" | "otro", "texto": "…"}], van saliendo); notificacion: `hora`, `texto`; llamada:
`contacto`; texto: `texto` (con `\n` para otra línea), `fondo`.

Campos de todo actor: `id`, `x`, `y`, `scale`, `rot` (inclinación; un `act` con `"rot": 90` lo tumba, animado),
`z` (delante/detrás), `flip` (espejo: ojo, también da la vuelta a los textos que lleve la pieza), `hidden` (empieza
oculto), `voice` (de qué voz mueve la boca), `shadow`.

## Eventos (`events`, cada uno en una palabra de su frase: `"at": "molino"`, `"delay": 0.2`)
| `type` | Qué hace | Campos |
|---|---|---|
| `act` | cambia props de un actor (expresión, pose, gafas…); los cambios numéricos se animan | `actor`, `props` |
| `reveal` | fantasía → realidad: el actor brilla y tiembla hasta la palabra; ¡puf! y es otra pieza | `actor`, `piece`, `scale`, `props` |
| `enter` / `exit` | entra o sale (al entrar, su animación empieza de cero) | `actor`, `from` / `to` (left, right, top, bottom, pop) |
| `move` | se desplaza (con líneas de velocidad) | `actor`, `x`, `y`, `seconds` |
| `cue` | un momento con nombre para una pieza propia | `actor`, `name` |
| `stamp` | sello de goma | `text`, `x`, `y`, `rot`, `size` (≥ 110: letra de plantilla), `until` (plano, beat, final o una palabra) |
| `label` | etiqueta pequeña en el mundo («6:00», un nombre) | `text`, `x`, `y`, `until` |
| `count` | el contador pasa a `value` | `value` |
| `count_break` | el contador se tacha (el giro) | — |
| `shake` / `flash` / `sparkle` | sacudida de cámara / destello / estrellitas | `strength` / — / `x`, `y` |
| `sfx` | un efecto concreto de `assets/sfx/` | `sound`, `volume` |
| `question` | la pregunta final (mejor `ending.question`) | `text` |

Sonidos automáticos (con `auto_sfx`): corte de plano (`papel`), sello (`sello`), contador (`ding`), revelado
(`destello`), entrada (`pop`), salida (`papel`), contador tachado (`boom`), pregunta (`toc`). Efectos que hay:
`papel`, `pop`, `sello`, `destello`, `whoosh`, `ding`, `toc`, `boom`, `riser`, `click`, `tick`, `error` (y los que
generes con `reels sfx-gen`).

## Rótulos
- Subtítulos de la voz (tiras de papel) en los beats con `captions: true` (por defecto).
- `bubble`: la frase va en un bocadillo que apunta a la cabeza de `actor`; `shout: true` para un grito.
- `title_card`: el cartel del fotograma 0 (`lines`, `highlight`, `until`).
- `series` y `work`: las etiquetas de arriba (desde `tags_from_beat`).
- `counter`: `label`, `kind` (rodillo, barra), `start`, `max`, `from_beat`, `suffix`.
- `music`: `track` (de `assets/music/music.json`), `volume` (0.15–0.2), `loop` (true: si el reel dura más que la
  pista, vuelve a empezar).
- `ending`: `seconds` de cola, su `shot`, sus `events` (con `delay` desde que empieza), `question`.

## Del episodio de ejemplo (`remotion/src/episodios/quijote-gafas/`)
`Quijote` (expresion serio/ilusion/decepcion/loco, gafas, brazo, lanza), `Gigante`, `Molino`, `Castillo`, `Venta`,
`Libro` (tachado 0–1), fondo `LaMancha` (el Campo con molinos lejos). Solo existen en ese episodio y en su gancho B.
