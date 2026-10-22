"""The smoke test (`reels humo`): a 7-second reel made end to end on this computer, for free.

The voice is already recorded (assets/humo/audio), so it needs no account and no API key: it proves the free
half of the factory (timeline, lip sync, 3D scene, render, montage, check) and leaves episodes/humo/final.mp4.
Non-interactive on purpose, so CI can run it on Windows, macOS and Linux runners.

Also the render benchmark of `reels doctor --prueba-render`: how long would a 30 s reel take on this machine?
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from rich.console import Console

from reels import system
from reels.assets import ASSETS, ROOT, episode_dir

SLUG = "humo"
SOURCE = ASSETS / "humo"
console = Console()


def prepare() -> Path:
    """Fresh episodes/humo/ from the template copy (script + pre-recorded voices). Old outputs are removed."""
    out = episode_dir(SLUG)
    if out.exists():
        shutil.rmtree(out)
    (out / "audio").mkdir(parents=True)
    shutil.copy(SOURCE / "script.json", out / "script.json")
    for f in (SOURCE / "audio").iterdir():
        shutil.copy(f, out / "audio" / f.name)
    return out


def run(quality: str = "humo", engine: str | None = None, check: bool = True) -> Path:
    """prepare → lint → build → render → compose → check. Returns final.mp4. Raises on any failure."""
    from reels import build as build_mod
    from reels.lint import lint
    from reels.schema import Episode

    if engine:
        os.environ["REELS_RENDER_ENGINE"] = engine
    t0 = time.time()
    steps = 5 if check else 4

    def step(n: int, text: str) -> None:
        console.rule(f"[bold]{n}/{steps} {text}[/]  [dim]{time.time() - t0:.0f} s[/]")

    out = prepare()
    step(1, "guion (revisión gratis)")
    errors = [i for i in lint(SLUG) if i.level == "ERROR"]
    if errors:
        raise RuntimeError("el guion de humo tiene errores: " + "; ".join(i.msg for i in errors))
    episode = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    step(2, "escena 3D (tiempos, labios, Blender)")
    build_mod.build(episode)
    step(3, f"render ({quality}{', ' + engine if engine else ''})")
    build_mod.render(SLUG, quality)
    step(4, "montaje (voces, subtítulos, sonido)")
    final = build_mod.compose(SLUG)
    if check:
        step(5, "comprobación (¿se oye cada frase en su plano?)")
        from reels.check import check_sync

        if not check_sync(SLUG):
            raise RuntimeError("la comprobación de sincronía ha fallado")
    console.print(f"[dim]  {time.time() - t0:.0f} s en total[/]")
    return final


# --- render benchmark --------------------------------------------------------------------------------------------

REEL_SECONDS = 30
FPS = 30


def _render_frames(blend: Path, first: int, last: int, quality: str) -> float:
    with tempfile.TemporaryDirectory(prefix="reels-bench-") as tmp:
        t0 = time.time()
        system.run_text([system.blender(), "--python-exit-code", "1", "-b", str(blend), "-P",
                         str(ROOT / "blender" / "render.py"), "--", tmp, quality, "range", str(first), str(last)],
                        timeout=3600)
        elapsed = time.time() - t0
        made = len(list(Path(tmp).glob("*.png")))
    if made < last - first + 1:
        raise RuntimeError("Blender no ha podido renderizar los fotogramas de prueba (mira `uv run reels doctor`)")
    return elapsed


def render_benchmark(quality: str = "final") -> dict:
    """Seconds per frame at final quality, from the smoke scene. Loading the scene is measured apart:
    time(1 frame) and time(4 frames) → (t4 - t1) / 3 is the cost of one more frame."""
    from reels import build as build_mod
    from reels.schema import Episode

    out = episode_dir(SLUG)
    if not (out / "scene.blend").exists():
        console.print("[dim]  preparo la escena de humo (una vez)…[/]")
        prepare()
        build_mod.build(Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8")))
    blend = out / "scene.blend"
    with system.keep_awake("reels doctor --prueba-render"):
        t1 = _render_frames(blend, 30, 30, quality)
        t4 = _render_frames(blend, 30, 33, quality)
    per_frame = max(0.05, (t4 - t1) / 3)
    total_min = per_frame * REEL_SECONDS * FPS / 60
    if total_min <= 45:
        verdict, advice = "local", "tu computadora sirve de horno: renderiza en local (gratis)."
    elif total_min <= 180:
        verdict, advice = "local de noche", ("en local tarda: déjalo renderizando de noche, o alquila una GPU "
                                             "(céntimos por reel) si tienes prisa.")
    else:
        verdict, advice = "nube", "en local tardaría demasiado: alquila una GPU para el render final (céntimos por reel)."
    result = {"quality": quality, "seconds_per_frame": round(per_frame, 2), "scene_load_seconds": round(max(0.0, t1 - per_frame), 1),
              "minutes_for_30s_reel": round(total_min, 1), "verdict": verdict, "advice": advice}
    (out / "benchmark.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result
