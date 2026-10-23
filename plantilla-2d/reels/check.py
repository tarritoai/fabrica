"""`reels check <slug>`: does final.mp4 say each line at its moment?

whisper listens to the WHOLE reel once (with all its context it hears much better than on short cuts, where music,
stamps and the end of a clip make it drop words) with a time for every word, and each beat gets the words heard
during its stretch of the timeline. A line that is not there, or that sounds somewhere else, fails.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rich.console import Console
from rich.markup import escape

from reels import system
from reels.assets import episode_dir
from reels.voice import normalize, similarity

console = Console()
MIN_SIMILARITY = 0.75  # neighbours' words bleed in at the edges and whisper mishears a word now and then
MARGIN = 0.35  # seconds around a beat where its words may be heard
_LINE = re.compile(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)")


def heard_words(video: Path) -> list[tuple[float, float, str]]:
    """(start, end, text) of every piece of word whisper hears in the video (None-safe: raises if whisper is missing)."""
    if not system.find_whisper() or not system.whisper_model().exists():
        raise RuntimeError("falta whisper o su modelo: `uv run reels doctor` te dice cómo ponerlos")
    wav = video.with_name("_check.16k.wav")
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                    "ffmpeg")
    try:
        out = system.run_whisper(["-l", "es", "-ml", "1", "-np"], wav, "whisper (el oído)").stdout
    finally:
        wav.unlink(missing_ok=True)
    words = []
    for ln in out.splitlines():
        m = _LINE.match(ln.strip())
        if m and m.group(7).strip():
            t0 = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            t1 = int(m.group(4)) * 3600 + int(m.group(5)) * 60 + float(m.group(6))
            words.append((t0, t1, m.group(7).strip()))
    return words


def missing_words(line: str, heard: str) -> list[str]:
    """Words of the line (longer than 3 letters) that are not anywhere in what was heard."""
    got = normalize(heard)
    return [w.strip(".,:;¿?¡!…«»") for w in line.split() if len(normalize(w)) > 3 and normalize(w) not in got]


def check_sync(slug: str, video: str = "final.mp4") -> bool:
    out = episode_dir(slug)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    src = out / video
    if not src.exists():
        raise FileNotFoundError(f"no existe {src}: primero `uv run reels render {slug}`")
    words = heard_words(src)
    ok = True
    for b in tl["beats"]:
        heard = " ".join(w for t0, t1, w in words if b["start"] - MARGIN <= (t0 + t1) / 2 <= b["end"] + MARGIN)
        sim = similarity(b["line"], heard)
        good = sim >= MIN_SIMILARITY
        ok &= good
        mark = "[green]✔[/]" if good else "[red]✘[/]"
        shown = re.sub(r"\s+([,.;:?!])", r"\1", heard)
        console.print(f"  {mark} beat {b['id']:>2} {b['start']:5.1f}s  {sim:.2f}  «{escape(b['line'])}» → «{escape(shown)}»")
        lost = missing_words(b["line"], heard)
        if lost:
            console.print(f"       [yellow]no oigo: {escape(', '.join(lost))}[/] (escúchalo: puede ser el oído o la voz)")
    console.print("[green bold]✔ cada frase suena en su sitio[/]" if ok else "[red bold]✘ hay frases que no se oyen donde tocan[/]")
    return ok
