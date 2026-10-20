# Biblia de personajes

Quién es cada personaje del reparto, cómo es y cómo habla. La lee el guionista (`reels/writer.py`) y el `oido`.
Rellena los huecos `<…>` con tus personajes. Los nombres que usan tus guiones están en `reparto.json`
(por defecto `prota` y `taza`); el aspecto 3D y la voz, en `assets/characters/<id>/character.json`.

## El prota (humano; id interno `novato`)
- **Nombre:** <cómo se llama, si se le nombra en el diálogo>
- **Quién es:** <edad, a qué se dedica, qué le pasa en la vida; por qué el público se identifica con él o ella>
- **Carácter:** <p. ej. simpático, demasiado seguro de sí mismo y un poco desastre>
- **Cómo habla:** <frases cortas, muletillas propias, cómo se justifica ("es que…")>
- **Aspecto (lo que ya existe en 3D):** persona low-poly en su mesa, con portátil y móvil (lo coge para mirar o llamar).
  <ropa, pelo y rasgos si los cambias>

## La cosa (no humano; id interno `claude`; por defecto, una taza con cara)
- **Nombre:** <cómo se llama, si se le nombra>
- **Qué es:** <qué representa en tu cuenta: una IA, una conciencia, una mascota, un objeto que observa…>
- **Carácter:** <p. ej. seco, prudente, un poco cansado, nunca sermonea; en el fondo quiere al prota y le protege>
- **Cómo habla:** <p. ej. preguntas cortas que destapan el problema; ironía mínima>
- **Aspecto (lo que ya existe en 3D):** una taza de cerámica con cara que vive encima de la mesa (o tu propia cosa: `docs/personajes.md`).
  Rasgos de actuación que el guion puede usar: la luz de pensar (pulsa cuando piensa, se aviva si algo le preocupa,
  se apaga cuando está triste), el parpadeo lento (su "suspiro"), la boca que solo aparece al hablar (sus silencios
  pesan), levantar un bracito ("un momento").

## Otros (opcionales)
Personajes que ya existen en `assets/characters/` y puedes usar si encajan: `chatgpt` (el entusiasta servil: dice
que sí a todo y empeora las cosas con alegría), `hugo` (compañero de piso, en el sofá), `mama` (solo voz, por
teléfono). Para darles otro nombre en tus guiones, `otros` en `reparto.json`.
<otros personajes tuyos>

## Tono
<de dónde sale la comedia o la emoción: p. ej. del contraste de personalidades entre el prota y la cosa. Las bromas
sobre empresas o personas reales, nunca: caricatura amable, sin afirmaciones sobre nadie real.>
