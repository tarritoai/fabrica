"""Characters of the 2D factory: personajes/<id>/personaje.json (who it is, which piece draws it, with which props,
and its voice) and their character sheets (`reels personaje <id>`): every expression and pose in one image, free.

A character on screen is a PIECE (remotion/src/…): the generic Persona or Cosa with props, or a piece drawn for it by
the «dibujante» worker. The narrator has a voice and no piece (it never appears).
"""

from __future__ import annotations

import json
from pathlib import Path

from reels.assets import PERSONAJES, ROOT
from reels import render

SHEETS = ROOT / "hojas"


def load(char_id: str) -> dict | None:
    path = PERSONAJES / char_id / "personaje.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(char_id: str, data: dict) -> Path:
    path = PERSONAJES / char_id / "personaje.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def sheet(name: str, episode: str | None = None, scale: float | None = None) -> Path:
    """Sheet of a character of yours (personajes/<id>/hoja.png) or of any piece (hojas/<Pieza>.png)."""
    data = load(name)
    if data is not None:
        piece = data.get("piece")
        if not piece:
            raise ValueError(f"«{name}» no sale en pantalla (no tiene pieza: es una voz). Su prueba es `reels voice-try {name}`.")
        variants = data.get("sheet") or []
        dest = PERSONAJES / name / "hoja.png"
        title = (data.get("display_name") or name).upper()
        return render.character_sheet(piece, title, variants, dest, base=data.get("props") or {}, slug=episode,
                                      scale=scale or 0.62)
    if not name[:1].isupper():
        raise ValueError(f"no existe personajes/{name}/personaje.json (y las piezas empiezan por mayúscula: Persona, Cosa…)")
    dest = SHEETS / f"{name}.png"
    return render.character_sheet(name, name.upper(), [], dest, slug=episode, scale=scale or 0.62)
