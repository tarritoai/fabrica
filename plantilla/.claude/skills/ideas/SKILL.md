---
name: ideas
description: Ronda de ideas para los próximos reels. Cinco ideadores en paralelo (lentes vida, verdades, formatos, exito y salvaje), un jurado que mata al menos la mitad y guarda TODAS las muertas con su motivo, cinco espectadores y cuidado, y 5 finalistas con una recomendación para que elijas. Modo ligero por defecto (pensado para el plan Pro). Usar con "/ideas", "/ideas completo" o cuando pidas ideas o el siguiente reel.
argument-hint: "[ligero|completo] [tema o pista opcional]"
---

# /ideas — de cero a 5 finalistas (y una recomendación)

Objetivo: que elijas entre 5 ideas **muy buenas y distintas**, sin que salgan todas del molde de lo ya hecho. Solo
gasta suscripción de Claude (trabajadores en paralelo); no toca nada de pago.

Habla en español claro y sin tecnicismos. A la persona que dirige la cuenta háblale de tú.

## 0. Antes de nada (gratis, 1 minuto)
1. Lee `docs/territorio.md` y `docs/publico.md`. Si siguen llenos de huecos `<…>`, dilo: "Tu territorio está sin
   rellenar; las ideas saldrán genéricas. ¿Hacemos antes `/nicho` (15–20 min)?". Si dice que siga, sigue con el
   `tema` de `assets/brand/brand.json` y lo que te cuente.
2. Reúne el contexto (con comandos y búsquedas cortas, no leyendo archivos enteros que crecen):
   - lo ya hecho: `uv run reels review --hecho`;
   - cómo ha ido cada reel, si hay datos: `uv run reels review`;
   - hipótesis abiertas: `docs/hipotesis.md`;
   - del banco (`ideas/banco.jsonl`): las `propuesta` vivas (compiten otra vez) y los **títulos + motivo** de las
     `descartada` (para no repetirlas). Con un script corto de Python, no a ojo;
   - la bandeja `ideas/inbox.md` (**tiene prioridad**) y, si existe `metrics/comments.jsonl`, 10–20 comentarios con
     historias o preguntas (los más recientes y con más "me gusta"; sin nombres de usuario).

## 1. Avisa del consumo y elige el modo (puerta de gasto de suscripción)
Antes de lanzar a nadie, di en 3 líneas qué vas a hacer y cuánto suele gastar. Usa esta tabla:

| Modo | Trabajadores | Qué cambia | Consumo orientativo en Pro |
|---|---|---|---|
| **ligero** (por defecto) | 8: 5 ideadores (6 ideas cada uno) · 1 jurado · 1 panel con los 5 espectadores · 1 cuidado | los espectadores van en un solo trabajador, uno detrás de otro | ~¼–⅓ de la ventana de 5 h |
| **completo** | 12: 5 ideadores (10 ideas) · 1 jurado · 5 espectadores por separado · 1 cuidado | más ideas y espectadores independientes | ~½ de la ventana de 5 h |

Las cifras son orientativas (dependen del modelo, de lo largo que estén tus `docs/` y de lo que lleves usado):
recomienda mirar `/usage` antes. Con Max, el completo no es problema.
Pregunta: "¿Lanzo la ronda en modo ligero?". Si en la orden ya dijo el modo o "sin preguntar", no preguntes.

## 2. Divergir: 5 ideadores en paralelo (un solo mensaje, 5 llamadas a la vez)
Lanza 5 subagentes `ideador`, uno por lente: `vida`, `verdades`, `formatos`, `exito`, `salvaje`.
A cada uno pásale: su lente, cuántas ideas (6 en ligero, 10 en completo), el territorio en 3 líneas, la lista de
hechos, los títulos + motivo de las descartadas, las hipótesis abiertas y las ideas de la bandeja o comentarios que
encajen con su lente. **No les pases guiones ni tus propias ideas**: el objetivo es que no se parezcan a ti.

## 3. Converger
1. **Junta** todas las fichas. Quita duplicados exactos y las que repiten algo hecho o descartado (cuentan como
   muertas con motivo "repite <título>").
2. **Jurado** (subagente `jurado`): pásale todas las nuevas **más las `propuesta` vivas del banco** (compiten de
   nuevo), la lista de hechos y las descartadas. Mata al menos la mitad. Comprueba su recuento: si no mató la mitad,
   devuélveselo una vez.
3. **Espectadores y cuidado en paralelo** (un solo mensaje), con las 8 mejores del jurado (6 en ligero):
   - ligero: un `espectador` en modo **panel** (las 5 personas de `docs/publico.md`, una detrás de otra);
   - completo: un `espectador` por persona activa o en prueba de `docs/criticos.md`;
   - `cuidado` con esas mismas ideas.
   A los espectadores pásales solo título, segundo 0, primera frase y final de cada idea: nada de intenciones.
4. **Elige 5 finalistas** combinando jurado y espectadores (los espectadores sirven por lo concreto: si 2 o más
   no pararían el scroll con el segundo 0, eso pesa; su nota media, no). **Regla de mezcla**: al menos 1 de
   exploración (lente formatos o salvaje, otro tono, o una que pruebe una hipótesis abierta) y como mucho 2 del mismo
   territorio o tipo de historia. Si una casi llega, aplica la mejora que propuso el jurado antes de presentarla.
   Un "riesgo serio" de `cuidado` se arregla en la ficha (con su propuesta) o la idea no llega a finalista.

## 4. Presentar (puerta 0: eliges tú)
Para cada finalista, en 5 líneas y en lenguaje llano:
1. **título** — logline
2. segundo 0 (qué se ve, qué se lee, qué se oye) · primera frase · final
3. a quién se lo mandarían y con qué mensaje · qué comentarían
4. qué hipótesis prueba · coste (piezas que existen / pantalla nueva / escenario nuevo)
5. jurado (puntos/50) y espectadores, en una línea (p. ej. "Javi: SCROLL en el segundo 2")

Y **tu recomendación** con su porqué en 2 líneas. Nada de listas sin opinión. Si eliges otra, perfecto: se apunta.

## 5. Guardar (siempre, aunque no elija ninguna)
Escribe en `ideas/banco.jsonl` con un script de Python (`json.dumps(..., ensure_ascii=False)`, una línea por
idea, en modo añadir para las nuevas; para cambiar estados, reescribe el archivo entero desde Python). Nunca a mano.
- **Todas las muertas** del jurado (y las que quitaste por repetir) como `descartada`, **cada una con su `motivo`**
  en una línea. Todas, sin excepción: así no vuelven a salir.
- Las supervivientes como `propuesta`, con `puntos` y `notas` (lo que dijeron jurado y espectadores, en una línea).
- Las `propuesta` que ya competían y no han llegado a finalista suman 1 a `rondas_perdidas`; con 2, pasan a
  `archivada` (motivo: "perdió 2 rondas"). Si quedan más de ~20 `propuesta`, las de menos puntos pasan a `archivada`.
- El acta de la ronda en `ideas/rondas/AAAA-MM-DD.md`: modo, las fichas, la tabla del jurado, lo de espectadores y
  `cuidado`, las 5 finalistas y la recomendación.
- Quita de `ideas/inbox.md` lo que ya pasó al banco.
- Cuando elija: esa idea pasa a `elegida`. Si descarta otras con un porqué, cámbialas a `descartada` con ese motivo.
  Si da un criterio nuevo ("no me gusta X porque…"), propón añadirlo a `docs/lo-que-funciona.md` (con su OK).

Comprueba al final (y dilo en una línea): `N ideas · M muertas guardadas con motivo · 5 finalistas · 1 elegida`.
Siguiente paso: `/episodio <id de la idea>` (mejor en un chat nuevo: el banco ya lo recuerda todo).
