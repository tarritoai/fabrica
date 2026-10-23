"""Where things live in the 2D factory (shared by every stage)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
EPISODES = ROOT / "episodes"
PUBLISH = ROOT / "publicar"
PERSONAJES = ROOT / "personajes"
REMOTION = ROOT / "remotion"
SFX = ASSETS / "sfx"


def episode_dir(slug: str) -> Path:
    return EPISODES / slug


def published(slug: str, suffix: str) -> Path:
    """publicar/<episode>/<slug><suffix>: one folder per reel, its B hook (<slug>-b) next to it."""
    found = sorted(PUBLISH.glob(f"*/{slug}{suffix}"))
    return found[0] if found else PUBLISH / slug.removesuffix("-b") / f"{slug}{suffix}"


def personaje(char_id: str) -> dict:
    """A character of yours: personajes/<id>/personaje.json (its voice, its piece, its look)."""
    path = PERSONAJES / char_id / "personaje.json"
    if not path.exists():
        raise FileNotFoundError(f"no existe el personaje «{char_id}» (personajes/{char_id}/personaje.json)")
    return json.loads(path.read_text(encoding="utf-8"))


def known_personajes() -> list[str]:
    return sorted(p.parent.name for p in PERSONAJES.glob("*/personaje.json")) if PERSONAJES.is_dir() else []
