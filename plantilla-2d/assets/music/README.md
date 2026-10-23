# Música

El formato «¿Y si…?» lleva música de fondo todo el rato. Aquí está tu catálogo (`music.json`): cada pista con su
licencia. Viene una, la del ejemplo (guitarra y pizzicato, 22 s, compuesta con Eleven Music): vale para tus reels.

- Componer una tuya (cuesta ~820 créditos por minuto; con plan de pago, uso comercial permitido):
  `uv run reels music-gen mi-pista "Playful pizzicato and woodblocks, 120 bpm, ends on a button hit" --seconds 35`
- Importar una con licencia que hayas descargado tú (guarda el enlace de la licencia):
  `uv run reels music-import ruta/a/la/pista.mp3 --name mi-pista --license "Pixabay Content License: https://…"`

En el guion: `"music": {"track": "clips/mi-pista.mp3", "volume": 0.18}`. Si la pista es más corta que el reel, se
corta al acabar: compón un poco más larga que el reel. Una pista con «no publicar» en su licencia solo sirve para ensayar.
