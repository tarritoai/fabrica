---
name: nicho
description: Encuentra tu territorio (una relación, no un tema) con las tres pruebas y sus verdades mecánicas, y describe a tu público con sus 5 espectadores. Rellena docs/territorio.md, docs/publico.md, ideas/fuentes.md y el tema de assets/brand/brand.json. Usar al empezar, con "/nicho", o cuando quieras cambiar de qué va tu cuenta.
argument-hint: "[tu nicho o tu idea, si ya la tienes]"
---

# /nicho — tu territorio y tu público

Una conversación de 15–20 minutos. Gratis (sin trabajadores extra). Español claro; a quien manda, de tú, sin dar
por hecho su género. Preguntas **de una en una o de dos en dos**, nunca un cuestionario de diez.

La idea que guía todo: **una relación, no un tema**. Lo que funcionó en la cuenta del curso no fue "la IA", sino la
relación del espectador con algo que usa cada día y que, en el vídeo, *nota cosas* de él. La cosa no explica nada:
se da cuenta.

## 1. Escuchar (5 min)
Si ya escribió su nicho en la orden, empieza por ahí. Pregunta, por este orden y solo lo que falte:
1. ¿De qué sabes mucho o qué vives todos los días? (oficio, afición, etapa de la vida, tu negocio)
2. ¿Quién quieres que te vea? (edad, países, cómo ven reels)
3. ¿Qué te gustaría que sintieran: reír, que les toque, las dos?
4. Si tienes un negocio: ¿qué vendes? (aparecerá como escenario o personaje, nunca como anuncio)

## 2. Proponer 3 territorios (puerta: eliges uno)
Para cada candidato, una ficha corta:
- **En una frase**: "La relación de ___ con ___, contada por ___, que lo nota todo."
- **El que nota cosas** (un objeto, animal o personaje del día a día; nunca un logo ni una marca real).
- **Las tres pruebas**, con sí/no y una línea:
  1. ¿Lo han vivido o lo temen? (sin saber nada técnico)
  2. ¿Hay **verdades mecánicas** que dan drama? (cita 3)
  3. ¿Hay **a quién mandárselo**? (una persona concreta y el mensaje exacto)
- **Riesgo**: p. ej. "humor de gremio: solo lo entiende quien es del oficio" (se comparte de 4 a 7 veces menos).
Ejemplos para inspirar (no para copiar): la olla exprés de la abuela (cocina), las zapatillas (running), la lámpara
del escritorio (estudiar). Un territorio que no pasa la prueba 3 no se propone.
Recomienda uno con su porqué. ✋ **Puerta**: elige (o mezcla). Su elección manda.

## 3. Rellenar el territorio
Con el elegido, rellena **todo** `docs/territorio.md` (sin dejar un solo `<…>`): la frase, el que nota cosas, las
tres pruebas, **al menos 5 verdades mecánicas** y **5 momentos vividos** (pídele que añada o tache), el tono
principal y el de exploración, el idioma y acento, el apartado de negocio si aplica y "lo que NO es tu cuenta".
Borra el comentario de ejemplos del final. Enséñale el resultado en 10 líneas y pregunta si cambia algo.

## 4. Tu público y tus 5 espectadores
Rellena `docs/publico.md`:
- **Quién te ve**: países, edad, cuándo y cómo ven reels, idioma y acento, dónde más se tiene que entender,
  plataformas, qué comparten y a quién, qué les echa para atrás.
- **Tus 5 espectadores**: reescribe las 5 personas provisionales para **su** público, manteniendo **los 5 papeles**
  (núcleo, impaciente, oído fino, experto, de fuera). Personas concretas: nombre, edad, ciudad, a qué se dedica,
  cómo ven reels, a quién mandan cosas, qué les echa para atrás. Variedad de países y edades dentro de su público;
  el "oído fino", de un país distinto al del acento de la cuenta si el público es de varios.
  El impaciente se llama **Javi** salvo que prefiera otro nombre (es el que se aburre en el segundo 2).
  Borra la línea que dice que las personas son provisionales.
- Actualiza los nombres en la tabla de `docs/criticos.md` (papel y estado `activa`; sin datos).
✋ Enséñale las 5 en una línea cada una y pregunta si alguna no se parece a su público.

## 5. Sembrar la materia prima
- `ideas/fuentes.md`: las verdades mecánicas y los momentos vividos del territorio (y 3–5 géneros que le peguen).
- `references/visto.md`: si conoces premisas muy vistas en ese nicho, apúntalas marcadas `(sin comprobar)`; nunca
  inventes cuentas concretas.
- `assets/brand/brand.json`: `tema` = la frase del territorio; `display_name` y `handle` si ya los tiene (si no, se
  quedan vacíos). Edita solo esos campos y comprueba que el JSON sigue siendo válido
  (`uv run python -c "import json; json.load(open('assets/brand/brand.json', encoding='utf-8'))"`).

## 6. Cierre
Comprueba que `docs/territorio.md` y `docs/publico.md` no tienen ningún `<…>` (con grep) y dilo en una línea.
Siguiente paso: `/personaje` (dar cuerpo y voz a quien nota cosas) y después `/ideas`.
Si sigue el curso: `/tarrito comprobar` sella el lote 4·2.
