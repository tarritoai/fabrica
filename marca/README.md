# marca/ — piezas de la serie original (NO se distribuyen con la plantilla)

La plantilla del alumno (`plantilla/`) es neutra: su reparto por defecto es `prota` (una persona) y `taza` (una taza
con cara) y su decorado por defecto es `habitacion` (cuarto-escritorio con ventana a una ciudad). Lo que es identidad
de la marca @tarritoai vive aquí, fuera de lo que copia `/fabrica:instalar`:

| Pieza | Archivo | Qué es |
|---|---|---|
| El tarro de barro | `blender/rigs/ceramic.py`, `assets/characters/claude/` | la mascota (constructor `"shape": "ceramic"`) |
| El prota original | `assets/characters/novato/` | el humano de la serie |
| El asistente de la competencia | `assets/characters/chatgpt/` | caricatura con nombre de marca real |
| El cuarto-isla en la galaxia | `blender/sets_marca.py` (`escritorio_noche`) | isla flotante, ladrillos que se desprenden, guirnalda, planeta con anillos |
| El mundo de dentro | `blender/sets_marca.py` (`mundo`), `blender/mundo.py`, `world_proto.py`, `cuarto_chica.py` | el portal y las islas de luces de la miniserie |

## Cómo se usan (solo para producir la serie original)
Copia el contenido de `marca/` encima de una copia de `plantilla/` (mismas rutas). La plantilla los detecta sola:
`blender/sets.py` registra los sets de `sets_marca.py` (el `escritorio_noche` de la isla sustituye al alias neutro),
`blender/rigs/placeholders.py` registra el constructor `ceramic`, `reels/schema.py` añade el set `mundo` si existe
`blender/mundo.py`, y `reels/cast.py` deja que las carpetas `novato` y `claude` interpreten sus huecos por defecto.

Sin `marca/`, nada de esto existe para el alumno y nada se rompe (tests en `plantilla/tests/test_plantilla_neutral.py`).
