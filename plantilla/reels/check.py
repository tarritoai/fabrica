"""End-to-end sync check: does final.mp4 say each line while its shot is on screen?"""

from __future__ import annotations

import difflib
import json
import subprocess

from rich.console import Console

from reels.assets import episode_dir, style
from reels.voice import _normalize, transcribe
from reels import system

console = Console()
MIN_SIMILARITY = 0.6


def check_sync(slug: str) -> bool:
    out = episode_dir(slug)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    fps = tl["fps"]
    tmp = out / "renders" / "_check.wav"
    ok = True
    for b in tl["beats"]:
        if not b["line"]:
            continue
        speed = style().get("playback_speed", 1.0)  # final.mp4 is sped up after composing
        start, end = b["start_frame"] / fps / speed, b["end_frame"] / fps / speed
        subprocess.run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(out / "final.mp4"),
             "-vn", "-ac", "1", "-ar", "16000", str(tmp)],
            check=True,
        )
        heard = transcribe(tmp)
        sim = difflib.SequenceMatcher(None, _normalize(b["line"]), _normalize(heard)).ratio()
        good = sim >= MIN_SIMILARITY
        ok &= good
        mark = "[green]✔[/]" if good else "[red]✘[/]"
        console.print(f"  {mark} beat {b['id']:>2} {start:5.1f}s  {sim:.2f}  «{b['line']}» → «{heard}»")
    tmp.unlink(missing_ok=True)
    console.print("[green bold]✔ audio sincronizado con los planos[/]" if ok else "[red bold]✘ hay beats desincronizados[/]")
    return ok
