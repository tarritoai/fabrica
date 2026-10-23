---
name: humo
description: Prueba de humo GRATIS de la fábrica 2D - un reel de unos 6 segundos de punta a punta (voz ya grabada, dibujo, montaje, comprobación con whisper) para saber que todo funciona en esta computadora. Usar con "/humo", después de instalar o cuando algo falle.
---

# /humo — ¿funciona tu fábrica 2D?

Gratis: la voz viene grabada y el dibujo se hace en tu computadora (sin gráfica, en menos de un minuto).

1. Dilo en una línea: «Voy a hacer un reel de prueba de unos 6 segundos. No gasta nada. Tarda menos de un minuto.»
2. `uv run reels humo --no-abrir` (tiempo máximo de la herramienta). Si falla, lee las últimas líneas: casi siempre
   es una pieza sin instalar → `uv run reels doctor` y su flecha →; o `/fabrica:tarrito` con el error entero.
3. Abre el vídeo (`episodes/humo/final.mp4`) y la hoja de fotogramas (`episodes/humo/fotogramas/hoja.jpg`).
   Enséñale la hoja con Read y dile qué ha pasado en 4 pasos: guion revisado → voces de la caché (0 créditos) →
   fotogramas clave → vídeo con música y efectos → el «oído» comprueba cada frase.
4. Siguiente paso: el ejemplo completo, también gratis: `uv run reels ejemplo quijote-gafas` (unos 2 minutos).
