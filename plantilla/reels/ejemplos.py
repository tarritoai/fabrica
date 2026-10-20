"""Example episodes that ship with the template (assets/ejemplos/<slug>/): open them, build them, render them.

Each example is a script.json plus its voices, already recorded, so trying an example costs nothing: either its own
`audio/` folder (beat_NN.json/.mp3/.wav, as `reels voice` leaves them) or voces.json, which says which line of
assets/humo/audio each spoken beat reuses. An example may bring its own music in `musica/` (with `musica.json`, its
catalogue entry and licence): it is added to assets/music/ the first time. `reels ejemplo <slug>` copies it to episodes/<slug>/ and
builds the 3D scene; `--fotogramas` renders one still per shot (quick look), without it the whole reel is made like
`reels humo` does.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from reels.assets import ASSETS, episode_dir

SOURCE = ASSETS / "ejemplos"
VOICES = ASSETS / "humo" / "audio"


def available() -> list[str]:
    return sorted(p.name for p in SOURCE.iterdir() if (p / "script.json").exists()) if SOURCE.is_dir() else []


def prepare(slug: str) -> Path:
    """Fresh episodes/<slug>/ from the example (script + reused voices). Old outputs are removed."""
    src = SOURCE / slug
    if not (src / "script.json").exists():
        raise FileNotFoundError(f"no existe el ejemplo «{slug}» (hay: {', '.join(available())})")
    out = episode_dir(slug)
    if out.exists():
        shutil.rmtree(out)
    (out / "audio").mkdir(parents=True)
    shutil.copy(src / "script.json", out / "script.json")
    if (src / "audio").is_dir():
        for f in (src / "audio").iterdir():
            shutil.copy(f, out / "audio" / f.name)
    _music(src)
    voices = json.loads((src / "voces.json").read_text(encoding="utf-8")) if (src / "voces.json").exists() else {}
    for beat, stem in voices.items():
        if beat.startswith("_"):
            continue
        for f in VOICES.glob(f"{stem}.*"):
            shutil.copy(f, out / "audio" / f"beat_{int(beat):02d}{f.suffix}")
    return out


def _music(src: Path) -> None:
    """Register the example's own music clip (musica/<file> + musica.json) in assets/music/ if it is not there yet."""
    entry_file = src / "musica.json"
    if not entry_file.exists():
        return
    from reels import music

    entry = json.loads(entry_file.read_text(encoding="utf-8"))
    dest = music.LIBRARY.parent / entry["file"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy(src / "musica" / Path(entry["file"]).name, dest)
    tracks = music.load()
    if not any(t["file"] == entry["file"] for t in tracks):
        music.LIBRARY.write_text(json.dumps(tracks + [entry], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(slug: str, quality: str = "draft", stills: bool = True) -> Path:
    """prepare -> build -> render (one still per shot, or the whole reel + montage). Returns the folder/video."""
    from reels import build as build_mod
    from reels.schema import Episode

    out = prepare(slug)
    episode = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    build_mod.build(episode)
    if stills:
        return build_mod.render(slug, quality, keyframes=True)
    build_mod.render(slug, quality)
    return build_mod.compose(slug)
