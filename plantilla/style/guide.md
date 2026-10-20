# Guía de estilo del guion

Reglas generales de escritura que lee el guionista (`reels/writer.py`) y los críticos (`editor-guion`, `oido`).
Edítala con lo que aprendas: `/revision` te propondrá cambios aquí (nunca se aplican sin tu OK).

## Básico
1. Gancho en el primer segundo: la primera frase (o la pantalla) plantea el conflicto sin contexto.
2. Frases cortas: lo normal 2–6 palabras, máximo 8 si suena más natural (una idea por beat). Ver «Fluidez» para los cortes de cámara.
3. Máximo 3 personajes, lo normal son 2 (el humano y la cosa). Cómo es y cómo habla cada uno: `style/characters.md`.
4. Una situación real y reconocible para el público de la cuenta (el `tema` de `assets/brand/brand.json`).
5. Remate con escalada visible (números, notificaciones…) y una última frase seca.
6. El final encadena con el principio para fomentar el bucle.
7. Ningún dato real: keys falsas tipo `sk-demo-…`, marcas inventadas en las pantallas.
8. Los personajes se llaman por su nombre en el diálogo cuando sea natural.
9. Propón dos ganchos alternativos (primeras frases) en `alt_hooks`.

## Fluidez (que sea una conversación, no diapositivas)
10. Cada frase la provoca la anterior: reacción, réplica o consecuencia. Nada de preguntas forzadas para que el otro explique ("¿cuántas veces…?", "te lo enseño"). Mejor que el gancho **pase** (alguien hace algo) a que se pregunte.
11. Ritmo: un plano nuevo cada ~1,5 s y ninguno de más de ~4 s sin que pase algo (reacción, corte, pantalla). Los turnos van pegados. `pause_before` es solo para pausas con intención (2 o 3 por vídeo como mucho, en los momentos que duelen) y `hold` en frases habladas, 0.1. El silencio se gana: si todo lleva pausa, ninguna pesa.
12. No cortes de cámara en cada frase: repite `camera` en frases seguidas para un plano continuo (sobre todo en réplicas rápidas y cuando habla alguien fuera de cámara). Corta en las reacciones.
13. Una idea no se parte en dos personajes que dicen lo mismo; una frase larga se puede partir en dos beats consecutivos del mismo personaje y plano ("Ay, cariño… Oye, ya que estás," / "el WhatsApp no me va.").
14. Las pantallas (llamada, contador) no son pausas: en cuanto conectan o aparece el dato, alguien reacciona.

## Formato agridulce con giro
15. Gancho que es una pregunta que duele ("¿te acuerdas de mí?"), no un desastre. La premisa sale de una verdad sobre el tema de la cuenta.
16. Detalles concretos y cotidianos en vez de explicar ("te pasé el CV catorce veces"). Humor pequeño dentro de la pena.
17. La cosa no consuela con sermones: valora lo que oye ("por cómo lo cuentas… parece que fue bonito").
18. Giro final: en el pico emocional (música al máximo) puede entrar un remate seco y la música se corta en seco.
19. Tras el giro, no acabar en el chiste: una coda sin palabras (sonrisa, risita, solo ambiente) devuelve el cariño. Así el vídeo es agridulce y no solo un gag.

## Cómo habla la gente (sacado de habla real: podcasts y sketches españoles)
20. Lo natural no es la jerga, es la **estructura**. En habla real casi no salen "mazo", "flipar" o "me renta"; lo que sale todo el rato es: "es que…" (justificarse), "o sea", "en plan", "claro", "bueno", "pues", "a ver", "no sé", "¿sabes?", "igual", "de repente", "todo el rato", "menos mal que…", "como que…", "me da (pena/cosa/miedo)". Una muletilla por frase como mucho, al principio, y solo donde ayude a actuar.
21. Hablado, no escrito: futuro con "ir a" ("te vas a quedar sin mí", no "te quedarás"); presente en vez de infinitivo de diccionario ("le estoy dejando una nota", no "dejarle una nota"); "todos los días" y no "a diario"; "la verdad" y no "honestamente"; "fijo"/"seguro" y no "seguramente". Nada de calcos del inglés: "ha sido un honor ayudarte" → "me lo he pasado muy bien contigo".
22. Repetir y corregirse suena vivo: "¿Todo, todo?", "No, no, no.", "Sí, sí.", "…Bueno. Tú.". Frases que se quedan a medias cuando duele.
23. Coletillas de pregunta para que no suene a guion: "¿no?", "¿eh?", "¿vale?", "¿sabes?".
24. Si la cuenta es en español de España, que se entienda y no ofenda en México, Colombia y Argentina: nada de coger, pillar, concha, chaqueta, pija, polla, bicho, cajeta, correrse ("lo contrataron", "agarra", "se lleva"). "Tío", "vale", "móvil", "portátil", "mola" sí se entienden.

## Escribir para la voz (ElevenLabs v4)
25. **La puntuación es el ritmo.** v4 hace una pausa en cada punto y no tiene ajuste de velocidad (y no se acelera nada después). Comas donde la frase va de corrido ("No, tío, te dejó en visto"), puntos donde tiene que respirar o pegar ("En marzo."). Ni correr por correr ni pausas que no pide la frase.
26. Énfasis con **una** palabra en mayúsculas en `spoken` ("Que NO."), no con etiquetas. Pausas con intención: `...`, `[short pause]`, `[long pause]`.
27. En `spoken`, etiquetas que **describen la voz** (`[flat, bored voice]`, `[low, tired voice]`) mejor que la emoción a secas. Ritmo: `[rushed]`, `[fast-talking]`, `[slowly]`.
28. Interrupciones: la frase cortada acaba en `-` y la que entra lleva `[jumping in]` o `[interrupting]`.

## Que no suene a guion
29. **Nada de frases redondas.** Si una frase podría ir en una taza o en un tráiler, es de guionista: «Te va a esperar» → «Esto no se va a ningún lado.». El ingenio está en la situación, no en cada réplica.
30. **Reaccionar antes que contestar bien.** La gente primero reacciona y luego (a veces) dice algo: «¿Cómo que al baño?», «Tío. ¿Eso ha sido la cadena?». No todos tienen la frase perfecta en el momento justo.
31. **Frases a medias y gente que se pisa.** Que alguien no acabe porque le cortan («¡Tú sigue, que te pego-» / «Ni se te ocurra.»). El que está pillado repite («Nada, nada», «Que sí, que sí, pesado»).
32. **Detalles de verdad de quien vive el tema**, dichos de pasada, sin explicarlos.
33. **Las muletillas solas no arreglan nada.** Meter «tío» o «te lo juro» en frases redondas sigue sonando a guion. Lo que cambia es la estructura (29–32). Y lo seco que ya funciona se deja como está.
