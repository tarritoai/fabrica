# Tus personajes

Tu fábrica sabe poner en escena a **dos papeles**:

- **el humano**: una persona (en su mesa, detrás de una barra, en un estudio, en un parque);
- **la cosa**: lo que la observa y le habla. Un tarro, una lámpara, una cafetera, una zapatilla, una taza...

Quién hace cada papel lo decides tú. No hace falta saber 3D ni programar: cada personaje es una carpeta con un
archivo de texto, `personajes/<nombre>/personaje.json`, y Claude lo escribe por ti.

## 1. Cómo pedirle a Claude un personaje

Descríbelo como se lo contarías a un amigo. Por ejemplo:

> «Quiero que mi cosa sea una tetera de hierro, negra mate, bajita y ancha, con la tapa que se le levanta cuando se
> enfada. Se llama Doña Hierro. Que tenga cejas gruesas y mofletes rojos.»

> «Mi humana es una corredora de unos 30 años: coleta, sudadera naranja, mallas negras. Se llama Vera.»

Claude creará `personajes/dona_hierro/personaje.json` (o `personajes/vera/...`) y después te enseñará su **hoja de
expresiones**:

```
uv run reels personaje dona_hierro
```

Es gratis y tarda un par de minutos: una sola imagen con sus 8 caras (neutral, orgulloso, confuso, alarma,
juzgando, hundido, pánico, aliviado), las bocas con las que habla, sus gestos y un parpadeo. Si algo no te gusta
(«los ojos más juntos», «más naranja», «que la tapa salte más»), díselo y vuelve a pedir la hoja. Cuando te guste,
ya puedes usarlo en un guion.

Para verlo en una escena de verdad, prueba los ejemplos (gratis, voz ya grabada):

```
uv run reels ejemplo lampara-de-las-tres
uv run reels ejemplo cafeteria-moka
```

## 2. Qué se puede cambiar de una «cosa»

Las cosas se construyen a partir de una **forma base** y se visten con datos:

| Forma (`form`) | Qué es | Su parte que actúa |
|---|---|---|
| `lampara` | lámpara de escritorio con brazo | el brazo se encoge o se estira, la pantalla se inclina; **su luz** se aviva, baja o se apaga |
| `cafetera` | cafetera italiana de 8 caras | la tapa se abre al asustarse y castañea al hablar |
| `taza` | taza con asa | — (prueba el accesorio `vapor`) |
| `olla` | olla con dos asas | la tapa salta |
| `cajita` | caja con tapa con bisagra | la tapa se abre |
| `zapatilla` | zapatilla deportiva | los cordones se ponen de punta o se caen |
| `bloque` | bloque redondeado (un libro, un tofu, un teléfono fijo, un ladrillo) | — |
| `cilindro` | bote, vaso, vela, lata | — |
| `bola` | esfera achatada (un pan, una fruta, una concha, una bola de arroz) | — |
| `cono` | cono (un cucurucho, una maceta con `"inverted": true`, un cono de tráfico) | — |

Y sobre la forma:

- **Tamaño y proporciones**: `size` (alto en metros), `width` y `depth` (más ancha, más fina).
- **Colores** (`colors`): `body` (el cuerpo), `accent` (bandas, tapas, suela), `detail` (asas, mangos, cordones),
  `inside` (lo de dentro: el café, el forro). En formato `#rrggbb`.
- **Acabado** (`finish`): `mate`, `esmalte` (brillante), `metal`, `tela`, `plastico`, `madera`.
- **Cara** (`face`): `height` (a qué altura), `size`, `spacing` (ojos más juntos o separados), `eyes` (`ojos` con
  párpados o `botones`), `brows` (`barra`, `arco` o `no`), `cheeks` (mofletes, un color), `mouth_size`.
- **Brazos** (`arms`): `{"style": "palito"}` le pone bracitos que se encogen de hombros y se alarman.
- **Pies** (`feet: true`): dos piececitos debajo.
- **Accesorios** (`accessories`): `vapor`, `lazo`, `hoja`, `gorro` (de cocinero), `gafas`, `pajarita`, `etiqueta`.
- **Luz** (solo `lampara`): `light.color` y `light.power`.

Un ejemplo completo es `personajes/moka/personaje.json`. Lo demás del archivo: `display_name` (cómo se llama),
`role` (`cosa`), `subtitle_color` (color de sus subtítulos), `voice` (su voz de ElevenLabs, ver más abajo),
`emotions` y `actions` (las caras y gestos que puede usar el guionista).

**Regla de casa**: tu cosa no debe parecerse al tarro de barro del curso (nada de terracota con tapa turquesa).
Es tu cuenta: dale tu propia paleta.

## 3. Qué se puede cambiar de un humano

Los humanos usan el mismo cuerpo low-poly con distintas ropas (`"placeholder": {"shape": "human"}`), en el bloque
`human`:

- `skin`, `skin_dark` (piel y su sombra), `hair` (color de pelo), `hair_style` (`curly`, `long`, `bob`, `bun`, o sin
  poner: pelo corto de punta);
- `hoodie`, `hoodie_dark` (la sudadera), `jeans` (pantalón);
- `glasses` (un color = gafas redondas), `apron` y `apron_dark` (delantal), `stubble` (barba de tres días),
  `lashes` (pestañas), `blush` (rubor), `thin_brows` (cejas finas).

Ejemplos: `personajes/estudiante/personaje.json` (gafas, media melena) y `personajes/barista/personaje.json`
(delantal, rizos).

Gestos del humano (`actions`): `talk_gesture`, `present_gesture`, `shrug` (encogerse de hombros), `facepalm`,
`lean_in`, `slump` (hundirse), `stretch` (desperezarse), `recoil` (respingo), `look_phone`, `phone_ear`...
Ver `docs/piezas.md` §5.

## 4. Elegir el reparto de un episodio

Tienes tres maneras, de la más sencilla a la más explícita:

1. **Ponerlos en la lista** del guion: `"characters": ["estudiante", "lucio"]`. El primer humano hace de humano y la
   primera cosa, de cosa.
2. **Decirlo en el guion**: `"reparto": {"humano": "estudiante", "cosa": "lucio"}`.
3. **Cambiar el reparto por defecto** de toda tu fábrica en `reparto.json`:
   `"cosa": {"personaje": "lucio", "nombre": "flexo"}` (y en tus guiones podrás escribir `lucio`, `flexo` o `cosa`).

En los guiones, para decir quién habla (`speaker`) o quién reacciona (`reactor`), vale el nombre del personaje
(`lucio`), el papel (`humano` / `cosa`) o el nombre que pusiste en `reparto.json`.

## 5. Dónde ocurre (decorados)

| `set` | Para qué | Opciones (`set_options`) |
|---|---|---|
| `habitacion` (por defecto) | el cuarto-escritorio: el humano en su mesa con portátil, ventana a la ciudad | `window` (`noche` / `dia`), `wall`, `floor`, `desk`, `rug`, `chair`, `curtains` (color o `null`), `posters`, `poster_colors`, `corcho`, `shelf`, `plants`, `sofa`, `apuntes`, `city` |
| `estudio` | fondo infinito de un color: explicativos, producto | `background`, `floor`, `plinth`, `plinth_on` |
| `mostrador` | barra de cafetería u obrador, de día | `variant` (`cafeteria` / `obrador`), `wall`, `counter`, `top`, `accent`, `floor` |
| `exterior` | parque de día (correr, pasear) | `grass`, `sky`, `path`, `trees`, `bench`, `stump` |

Los decorados genéricos funcionan con el humano y la cosa juntos, o con la cosa sola.

## 6. La voz

Un personaje nuevo nace **sin voz** (`voice_id` vacío): `uv run reels lint` te avisa. Elige una voz en la biblioteca
pública de ElevenLabs, copia su id y pídele a Claude que la ponga en su `personaje.json`. Hasta entonces puedes
probarlo gratis con la hoja de expresiones y con los ejemplos.

## 7. Si algo sale raro

- «No existe el personaje»: el nombre de la carpeta y el de `characters` tienen que coincidir (minúsculas, sin
  tildes ni espacios: `dona_hierro`, no `Doña Hierro`).
- «no puede hacer de humano»: has puesto una cosa en el papel de humano (o al revés). Mira su `role`.
- «set habitacion is built around…»: la habitación necesita un humano. Para una cosa sola, usa
  `estudio`, `mostrador` o `exterior`.
- La cara queda torcida o se sale: pide otra `face.height` o `face.size` y vuelve a sacar la hoja.
