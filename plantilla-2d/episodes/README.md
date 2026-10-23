# episodes/

Un episodio por carpeta: `episodes/<slug>/`. A git solo van `script.json` (el contrato), `estado.md` (dónde va),
`critica.md` y `guion-v*.md`. Lo demás se regenera gratis: `voice.json` y `publico/` (las voces, desde la caché),
`timeline.json` (`reels build`), `fotogramas/` (`reels stills`), `final.mp4` (`reels render`).
`humo/` y `quijote-gafas/` se rehacen desde `assets/` cada vez (`reels humo`, `reels ejemplo quijote-gafas`).
