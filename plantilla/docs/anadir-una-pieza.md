# Cómo añadir una pieza nueva

Una pieza es algo que un guion puede activar con un campo de `script.json` (una pantalla, un gesto, una luz, un plano…).
Se añade **para un episodio concreto**, pero queda para todos. Pasos según el tipo:

## Siempre
1. **`reels/schema.py`**: el campo nuevo (o el valor nuevo de un enum) con una `description` clara: llega al guionista automático.
2. **Validar** un guion que la use: `uv run python -c "import json; from reels.schema import Episode; Episode.model_validate(json.load(open('episodes/<slug>/script.json')))"`.
3. **Probarla barato**: `reels animatic <slug>` (fotograma fijo por beat) y luego `reels preview <slug> --beats a-b --quality draft` solo de los beats que la usan. Mirar fotogramas con ffmpeg y **enseñárselos al usuario** antes del render final.
4. **Documentarla en `docs/piezas.md`** (qué hace, JSON, cuándo usarla, trampas, episodio de ejemplo) y una línea en `CLAUDE.md` si cambia el flujo.
5. Commit pequeño.

`timeline.py` copia cada beat entero (`model_dump`) al `timeline.json`: cualquier campo nuevo de `Beat` llega solo a Blender y a Remotion.

## Según el tipo
| Tipo | Dónde va el código | Ejemplo a imitar |
|---|---|---|
| Pantalla de portátil o móvil | `remotion/src/screens/<Nombre>.tsx` + registrarla en `remotion/src/Root.tsx` + `XxxEvent` en `schema.py` (añadirla a `Event`, y a `PHONE_COMPONENTS` / `LAPTOP_COMPONENTS` aquí **y** en `blender/build_scene.py`, que no importa `reels/`) | `SystemNotice.tsx` |
| Overlay sobre el vídeo | `remotion/src/compose/` (lo dibuja la composición final) | `CounterReveal` |
| Prop de pantalla existente | solo el `.tsx` y el `Props` de `schema.py` (opcional, con valor por defecto, para no romper episodios viejos) | `battery` en `SystemNotice`, `messages` en `PhoneNotifications` |
| Gesto, cara, emoción | `blender/rigs/animate.py` (tablas y funciones por beat) / `human.py`, `ceramic.py` | `_tears`, `_power` |
| Luz | `blender/moods.py` (`MOODS`: multiplicadores por luz) + enum `Light` | `apagon`, `oscuro` |
| Cámara | `blender/cameras.py` (`presets`) + enum `Camera` | `phone_screen` (cámara hija del móvil) |
| Efecto de sonido | `reels sfx-gen <nombre> "<prompt>"` + enum `Sfx` | |
| Música | `reels music-import` (+ `music.track` para fijarla) | |
| Nombre propio para un personaje | solo `reparto.json`: `nombre` del prota (`humano`) o de la cosa, o una entrada en `otros` (`"nombre": "<id de assets/characters/>"`); el código sigue usando los ids internos (`novato`, `claude`…) | `"humano": {"nombre": "prota"}` |
| Set entero nuevo | `blender/sets.py` / módulo propio + enum `Set` + su regla de reparto en `SET_CAST` (`schema.py`: a quién necesitan sus cámaras y cuántos caben; puede no llevar al prota) | `future.py`, `world_proto.py` (prototipo del mundo de la miniserie) |

## Reglas
- Blender corre con su propio Python: `blender/` solo usa stdlib + `bpy`, nunca importa `reels/`.
- Campos nuevos **opcionales con valor por defecto**: los episodios publicados tienen que seguir validando y renderizando igual.
- Las cachés se invalidan solas si cambia el código de `remotion/src/screens/*.tsx` o la escena; si algo no se actualiza, borrar `episodes/<slug>/screens/` o `scene.blend`.
- Nada de marcas reales en las pantallas (apps inventadas, keys `sk-demo-…`).
