# Licencias de lo que viene dentro de la plantilla

Regla: aquí solo entra lo que se puede redistribuir con una licencia clara. Lo dudoso se queda fuera y se apunta
abajo. Si añades algo, regístralo en esta tabla (y la música, además, en `music/music.json` con su licencia).

## Incluido

| Qué | Dónde | Origen | Licencia |
|---|---|---|---|
| Muebles low-poly «Furniture Kit 2.0» (140 modelos `.glb`) | `vendor/kenney_furniture/` | Kenney (kenney.nl) | CC0 1.0 (dominio público; atribución opcional). Texto en `vendor/kenney_furniture/License.txt` |
| Efectos de sonido (25 `.wav`: `ding`, `whoosh`, `error`, `click`, `toc`, `tick`, `typing`, `typing_tiny`, `amb_night`, `amb_luces`, `amb_ruinas`, `boom`, `cadena`, `grifo`, `glitch`, `portal_rumble`, `riser`, `sky_burst`, `tension`, `tunnel_whoosh`, `ding_alarm`, y las respuestas de sala `ir_room`, `ir_bano`, `ir_hall`, `ir_ruins`) | `sfx/` | Sintetizados con ffmpeg por `tools/gen_sfx.py` del repo de la fábrica (sin muestras de nadie) | CC0 1.0 (hechos para la fábrica). Son sustitutos sencillos con los mismos nombres, duración y volumen que los originales |
| Voz de la prueba de humo («¡Hola! Soy tu taza. Si me oyes, tu fábrica funciona.») | `humo/audio/` | Generada con ElevenLabs (voz pública «Maria - Warm & Energetic», eleven_v4) desde la cuenta de pago del curso | Uso comercial permitido por los términos de ElevenLabs para planes de pago; se distribuye solo como prueba de la fábrica |
| Reel de ejemplo «La lámpara de las tres · El tema 4» (voces y música) | `ejemplos/lampara-de-las-tres/` | Voces generadas con ElevenLabs (voces públicas «Roberto - Conversational» y «Anita - Conversational», eleven_v4) y música compuesta con Eleven Music, desde la cuenta de pago del curso | Uso comercial permitido por los términos de ElevenLabs para planes de pago; se distribuye como ejemplo de la fábrica |
| Tipografías Inter y JetBrains Mono (woff2, latin + latin-ext) | `../remotion/src/fonts/` | Google Fonts | SIL Open Font License 1.1 (`OFL-*.txt` al lado) |
| Tipografía Patrick Hand (letra de tiza de la pizarra del decorado `mostrador`) | `fonts/` | Google Fonts (Patrick Wagesreiter) | SIL Open Font License 1.1 (`fonts/OFL-PatrickHand.txt`) |
| Personajes (`characters/*/character.json`) | `characters/` | Datos (colores, medidas, voz) del proyecto original; los modelos 3D se construyen por código (`blender/rigs/`) | Parte del código de la fábrica |

## Fuera (y por qué)

| Qué | Motivo | Cómo lo consigue el alumno |
|---|---|---|
| Música del proyecto original (9 clips: 3 «SIN VERIFICAR» sacados de una recopilación de YouTube, 2 de Rexlambo con atribución, 4 de Pixabay) | Lo sin verificar no se puede usar; Rexlambo y Pixabay no permiten reempaquetar sus pistas como biblioteca | Baja pistas con licencia (p. ej. Pixabay Music) y las importa con `uv run reels music-import … --license "…"`. `music/music.json` empieza vacío: sin música, el montaje sale solo con voces, efectos y ambiente |
| Efectos de sonido originales | Origen sin documentar (parte generados con ElevenLabs desde otra cuenta, parte desconocido) | Sustituidos por los sintetizados. Si el autor original confirma su origen y licencia, se pueden volver a meter (mismos nombres) |
| Foto de perfil y marca de la cuenta original (`brand/perfil*.png`, bio) | Identidad de otra cuenta | `brand/brand.json` vacío: lo rellena el alumno (o `/instalar`) |
| Modelo de whisper `ggml-small.bin` (~470 MB) | Tamaño | `uv run reels descargar-modelo` (MIT, de huggingface.co/ggerganov/whisper.cpp) |
| Programas (Blender, ffmpeg, whisper.cpp, Rhubarb, Node) | Se instalan por sistema operativo | `uv run reels doctor` dice el comando exacto |

## Voces de los personajes
Los `voice_id` de `characters/*/character.json` son voces de la biblioteca pública de ElevenLabs (la taza: «Maria -
Warm & Energetic») o vienen del proyecto original. La voz del prota y las de los extras pueden ser voces creadas en otra cuenta y no
estar disponibles en la tuya: elige voces de la biblioteca pública y pega su `voice_id` (pendiente de automatizar en
`/instalar`).
