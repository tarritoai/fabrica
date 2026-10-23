"""Examples that ship with the 2D factory (assets/ejemplos/<slug>/): a script.json plus its voices ALREADY PAID, as
cache files (voz/<key>.mp3 + .json). `reels ejemplo <slug>` puts those in .cache/voice/ and runs the real pipeline
(voice from the cache → timeline → key frames → video → check): it proves the whole factory and costs nothing.
The smoke test (`reels humo`) is the same thing with a 2-line script (assets/humo/).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from rich.console import Console

from reels.assets import ASSETS, episode_dir
from reels.voice import CACHE

SOURCE = ASSETS / "ejemplos"
console = Console()


def available() -> list[str]:
    return sorted(p.name for p in SOURCE.iterdir() if (p / "script.json").exists()) if SOURCE.is_dir() else []


def prepare(src: Path, slug: str) -> Path:
    """Fresh episodes/<slug>/ from an example folder, with its paid voices copied into the cache."""
    if not (src / "script.json").exists():
        raise FileNotFoundError(f"no existe el ejemplo «{slug}» (hay: {', '.join(available()) or 'ninguno'})")
    out = episode_dir(slug)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy(src / "script.json", out / "script.json")
    CACHE.mkdir(parents=True, exist_ok=True)
    for f in (src / "voz").glob("*.*"):
        if not (CACHE / f.name).exists():
            shutil.copy(f, CACHE / f.name)
    return out


def run(slug: str, src: Path | None = None, video: bool = True, check: bool = True, draft: bool = False,
        listen: bool = True) -> Path:
    """prepare → lint → voice (cache, 0 credits) → build → key frames → video → check. Returns final.mp4 (or the sheet)."""
    from reels import render, timeline
    from reels.check import check_sync
    from reels.lint import lint
    from reels.schema import Episode
    from reels.voice import voice_episode

    t0 = time.time()
    steps = 4 + (1 if video else 0) + (1 if video and check else 0)

    def step(n: int, text: str) -> None:
        console.rule(f"[bold]{n}/{steps} {text}[/]  [dim]{time.time() - t0:.0f} s[/]")

    out = prepare(src or SOURCE / slug, slug)
    step(1, "guion (revisión gratis)")
    errors = [i for i in lint(slug, voice=False) if i.level == "ERROR"]
    if errors:
        raise RuntimeError("el guion tiene errores: " + "; ".join(i.msg for i in errors))
    ep = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    step(2, "voces (ya grabadas: 0 créditos)")
    voice_episode(ep, allow_spend=False, listen=listen)
    step(3, "tiempos (cada evento, en su palabra)")
    tl = timeline.save(ep)
    console.print(f"  {tl['frames'] / tl['fps']:.1f} s · {len(tl['shots'])} planos · {len(tl['events'])} eventos")
    step(4, "fotogramas clave")
    sheet, _ = render.stills(slug)
    console.print(f"  {sheet}")
    if not video:
        return sheet
    step(5, "vídeo (dibujo, voces, música y efectos)")
    final = render.render_video(slug, draft=draft)
    if check:
        step(6, "comprobación (¿se oye cada frase en su sitio?)")
        if not check_sync(slug):
            raise RuntimeError("la comprobación de sincronía ha fallado")
    console.print(f"[dim]  {time.time() - t0:.0f} s en total[/]")
    return final
