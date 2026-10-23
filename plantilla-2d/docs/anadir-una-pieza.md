# Añadir una pieza (lo hace el dibujante)

Una pieza es un componente de React que dibuja SVG con el kit de la casa. Lo escribe el trabajador `dibujante`;
quien manda solo ve la hoja y dice sí o no.

## Dónde va
- **De un episodio** (solo sale en esa historia): `remotion/src/episodios/<slug>/index.tsx`, exportada con nombre en
  mayúscula (`export const Molino: Piece = …`). La usa también su gancho B (`<slug>-b`).
- **Un personaje tuyo** (sale en muchos episodios): `remotion/src/personajes/<id>.tsx` y una línea en
  `remotion/src/personajes/index.ts` (`export { Lola } from "./lola";`), más `personajes/<id>/personaje.json` con
  `"piece": "Lola"`. Si basta con `Persona` o `Cosa` con parámetros, **no se dibuja nada**: solo el JSON.

## Cómo es una pieza
- Recibe `PieceProps`: `frame`, `t` (fotogramas desde que empezó el plano), `props` (las del guion, ya cambiadas
  por los `act`), `prev` y `since` (fotogramas desde el último `act` o desde que entró con `enter`: para animar un
  cambio con `transition`), `talk` (0–1: su voz suena), `cues` (momentos con nombre), `seed`, `place` (dónde está
  en el cuadro). En la hoja se dibuja con `frame` 40 y `since` 99: lo que enseña es la animación ya terminada.
- Para dibujar **encima de una `Persona`** (una capucha, una corona de flores, algo al hombro) sin copiar sus
  números: `personaAnchors(props)` (de `piezas/persona.tsx`) da la cabeza, el cuello, los hombros y la cadera.
  Antes de dibujar un animal, mira si `Animal` con su `especie` ya sirve.
- Origen (0, 0) = entre los pies (o la base del objeto); hacia arriba, y negativa. Altura de referencia: 350–600 px.
- Se dibuja **solo** con el kit: colores de `usePalette()`, línea `LINE`, `Limb`, `Hand`, `Eye`, `Mouth`, `Brow`,
  `Cheeks`, `blink`, `breathe`, `talkMouth`, `transition`. La sombra dura la pone el motor: no la dibujes.
- Metadatos: `Pieza.kind` ("actor" | "objeto" | "fondo"), `Pieza.about` (una línea para `docs/piezas.md`),
  `Pieza.head` (dónde apuntan los bocadillos), `Pieza.sheet` (las variantes de su hoja).

## Pasos
1. Escribir la pieza (el `dibujante`).
2. `uv run reels piezas` → comprueba el código (TypeScript) en segundos, con el archivo y la línea de cada error.
3. `uv run reels personaje <Pieza> --episodio <slug> --no-abrir` → hoja con sus variantes en `hojas/<Pieza>.png`
   (las de tus personajes, en `personajes/<id>/hoja.png`). Un fondo sale como miniatura del cuadro entero; para una
   pieza muy alta, `--escala 0.4`. Mirarla (el `ojo`).
4. ✋ Enseñarla: OK de quien manda. Corregir lo que pida.
5. Apuntarla en `docs/piezas.md` (y en `docs/biblia.md` si es un personaje fijo).
6. `uv run reels lint <slug>` ya la reconoce; `uv run reels stills <slug> --sin-voz` la enseña en su plano antes de
   pagar ninguna voz.
