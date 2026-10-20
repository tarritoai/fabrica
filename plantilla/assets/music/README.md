# Música

Empieza vacía a propósito: solo se versiona el catálogo `music.json`, nunca los audios.

Para añadir una pista con licencia (por ejemplo de Pixabay Music, guarda el enlace de la licencia):

    uv run reels music-import "ruta/a/la/pista.mp3" --mood agridulce --starts 0,45 --license "Pixabay Content License: https://…"

Si la licencia pide atribución, añade `attribution` a su entrada en `music.json`: `reels compose` la copia a
`episodes/<slug>/creditos.txt` para pegarla en la descripción del post.

O compón una tuya con Eleven Music (cuesta ~900 créditos de ElevenLabs por minuto; con plan de pago el uso
comercial está permitido): instrumental, del largo del reel, y queda en el catálogo con su licencia:

    uv run reels music-gen piano-madrugada "Soft solo felt piano, slow 70 bpm, bittersweet, sparse notes, warm room tone, gentle swell near the end" --seconds 45 --mood agridulce
