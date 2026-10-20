"""`reels personaje <id>`: the expression sheet of a character (emotions, mouths, gestures, blink) as one image.

Blender builds the character alone in the plain studio (blender/character_sheet.py, same code as an episode) and
renders one still per cell; ffmpeg tiles them into personajes/<id>/hoja.png (or next to the template's own
characters) and the whole-body cell is kept as personajes/<id>/fotograma.png. It is the check before using a new character in an episode: free and local.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from reels import system
from reels.assets import ROOT, character_path

COLS = 7


def sheet(char_id: str, cell_px: int = 300, out: Path | None = None) -> Path:
    path = character_path(char_id)
    if path is None:
        raise FileNotFoundError(f"no existe el personaje «{char_id}»: crea personajes/{char_id}/personaje.json")
    dest = out or path.parent / "hoja.png"
    with tempfile.TemporaryDirectory(prefix="reels-hoja-") as tmp:
        log = system.run_text([system.blender(), "--python-exit-code", "1", "-b", "--factory-startup", "-P",
                               str(ROOT / "blender" / "character_sheet.py"), "--", char_id, tmp, str(cell_px)], timeout=1800)
        if not (Path(tmp) / "cells.json").exists():
            tail = "\n".join(line for line in log.splitlines() if line.strip())[-1500:]
            raise RuntimeError(f"Blender no ha podido construir «{char_id}». Final del registro:\n{tail}")
        cells = json.loads((Path(tmp) / "cells.json").read_text(encoding="utf-8"))
        rows = -(-len(cells) // COLS)
        system.run_text([system.ffmpeg(), "-v", "error", "-y", "-framerate", "1", "-i", str(Path(tmp) / "cell_%02d.png"),
                         "-vf", f"tile={COLS}x{rows}:padding=4:color=white", "-frames:v", "1", str(dest)], timeout=300)
        if not dest.exists():
            raise RuntimeError("ffmpeg no ha podido montar la hoja")
        # The still to approve (and the one /tarrito checks): the character whole, in its first gesture cell
        # (talk_gesture/idle), or the neutral close-up if it has no gestures.
        whole = next((c for c in cells if c["label"] in ("talk_gesture", "idle", "shrug")), cells[0])
        import shutil

        shutil.copy(Path(tmp) / whole["file"], dest.parent / "fotograma.png")
    return dest
