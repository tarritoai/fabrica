# Licencias de lo que viene dentro de la fábrica 2D

Aquí solo entra lo que se puede redistribuir con una licencia clara. Si añades algo, regístralo en esta tabla (y la
música, además, en `music/music.json`).

| Qué | Dónde | Origen | Licencia |
|---|---|---|---|
| Efectos `whoosh`, `ding`, `toc`, `boom`, `riser`, `click`, `tick`, `error` | `sfx/` | Sintetizados con ffmpeg para la fábrica (`tools/gen_sfx.py` del repo) | CC0 1.0 |
| Efectos `sello`, `destello`, `papel` y `pop` | `sfx/` | Generados con ElevenLabs (efectos de sonido) desde la cuenta de pago del curso | Uso comercial permitido por los términos de ElevenLabs para planes de pago |
| Música «quijote-guitarra» (22 s) | `music/clips/` | Compuesta con Eleven Music desde la cuenta de pago del curso | Uso comercial permitido por los términos de ElevenLabs; sin atribución |
| Voces del ejemplo «¿Y si Don Quijote llevara gafas?» | `ejemplos/quijote-gafas/voz/` | ElevenLabs (eleven_v4), voces públicas «Enzo - Viral Videos, Reels and Shorts», «Johnny The Rogue» y «Rafael (luces)», desde la cuenta de pago del curso | Uso comercial permitido para planes de pago; se distribuye como ejemplo de la fábrica |
| Voz de la prueba de humo | `humo/voz/` | ElevenLabs (eleven_v4), voz pública «Enzo - Viral Videos, Reels and Shorts» | Ídem; solo como prueba |
| Historia del ejemplo | `ejemplos/quijote-gafas/` | *Don Quijote de la Mancha*, Miguel de Cervantes (1605) | Dominio público |
| Tipografías Big Shoulders, Big Shoulders Stencil y Archivo (woff2) | `../remotion/src/fonts/` | Google Fonts | SIL Open Font License 1.1 (`OFL-*.txt` al lado) |
| Textura de papel | `../remotion/src/kit/papel.png` | Generada por código (`tools/gen_papel.py` del repo) | CC0 1.0 |
| Dibujos (kit, piezas, episodio de ejemplo) | `../remotion/src/` | Código de la fábrica | Parte del código de la fábrica |

## Fuera (y por qué)
| Qué | Motivo | Cómo lo consigue el alumno |
|---|---|---|
| Reels de referencia del formato | Son de otras cuentas | Los guarda a mano en `references/inbox/` para estudiarlos; nunca se redistribuyen |
| Modelo de whisper `ggml-small.bin` (~470 MB) | Tamaño | El instalador (o `uv run reels descargar-modelo`) |
| Programas (ffmpeg, whisper.cpp, Node) | Se instalan por sistema operativo | El instalador; `uv run reels doctor` dice qué falta |
