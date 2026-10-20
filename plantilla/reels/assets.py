"""Load asset metadata (characters, style) shared by every stage."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
EPISODES = ROOT / "episodes"


@cache
def style() -> dict:
    return json.loads((ASSETS / "style.json").read_text(encoding="utf-8"))


# Where characters live: the student's own (personajes/<id>/personaje.json) first, then the template's.
PERSONAJES = ROOT / "personajes"
CHARACTER_DIRS = ((PERSONAJES, "personaje.json"), (ASSETS / "characters", "character.json"))


def character_path(char_id: str) -> Path | None:
    for folder, name in CHARACTER_DIRS:
        path = folder / char_id / name
        if path.exists():
            return path
    return None


def known_characters() -> set[str]:
    return {p.parent.name for folder, name in CHARACTER_DIRS if folder.is_dir() for p in folder.glob(f"*/{name}")}


@cache
def character_file(char_id: str) -> dict:
    """A character's own file, by folder id (no cast resolution)."""
    path = character_path(char_id)
    if path is None:
        raise FileNotFoundError(f"no existe el personaje «{char_id}» (personajes/{char_id}/personaje.json)")
    return json.loads(path.read_text(encoding="utf-8"))


def character(char_id: str) -> dict:
    """Metadata of whoever plays this id in the episode being processed (a role slot -> its player; reels/cast.py)."""
    from reels import cast

    return character_file(cast.player(char_id))


def episode_dir(slug: str) -> Path:
    return EPISODES / slug


PUBLISH = ROOT / "publicar"


def published(slug: str, suffix: str) -> Path:
    """publicar/<episode>/<slug><suffix>: one folder per reel, its B hook (<slug>-b) next to it.
    An existing file wins wherever it is (e.g. tres-tokens-cara lives in tres-tokens/)."""
    found = sorted(PUBLISH.glob(f"*/{slug}{suffix}"))
    return found[0] if found else PUBLISH / slug.removesuffix("-b") / f"{slug}{suffix}"
