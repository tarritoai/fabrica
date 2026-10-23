"""`reels ref`: take apart a reference reel YOU saved (scene cuts, a 1 fps sheet, transcript with timings)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from reels.assets import ROOT
from reels import system

COLS = 6
CELL = (270, 480)  # a quarter of 1080x1920: still readable for faces and big screen text


def _duration(video: Path) -> float:
    out = subprocess.run([system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True, encoding="utf-8", errors="replace")
    return float(out.stdout.strip())


def _tile(video: Path, out: Path, vf_select: str, count: int) -> None:
    rows = max(1, -(-count // COLS))
    vf = f"{vf_select},scale={CELL[0]}:{CELL[1]}:force_original_aspect_ratio=decrease,pad={CELL[0]}:{CELL[1]}:-1:-1," \
         f"tile={COLS}x{rows}:padding=4:color=white"
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-vf", vf, "-frames:v", "1", "-fps_mode", "vfr",
                    str(out)], check=True)


def sheet(video: Path, start: float, end: float, fps: float, out: Path) -> list[float]:
    """Frames every 1/fps seconds between start and end, tiled left to right, top to bottom. Returns their times."""
    end = min(end, _duration(video))
    times = [round(start + i / fps, 2) for i in range(int((end - start) * fps) + 1)]
    _tile(video, out, f"trim=start={start}:end={end + 0.01},setpts=PTS-STARTPTS,fps={fps}", len(times))
    return times




def reference(video: Path) -> Path:
    """Take a reference reel apart into references/<name>/: scene-cut sheet, 1 fps sheet, transcript with timings."""
    name = re.sub(r"[^a-z0-9]+", "-", video.stem.lower()).strip("-")
    out = ROOT / "references" / name
    out.mkdir(parents=True, exist_ok=True)
    dur = _duration(video)
    sheet(video, 0, dur, 1.0, out / "sheet_1fps.png")
    # One frame per shot: the first frame plus every scene change.
    cuts = subprocess.run([system.ffmpeg(), "-i", str(video), "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    times = [0.0] + [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", cuts)]
    _tile(video, out / "sheet_cuts.png", "select='eq(n,0)+gt(scene,0.3)'", len(times))
    wav = out / "audio.16k.wav"
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-ar", "16000", "-ac", "1", str(wav)], check=True)
    try:
        words = system.run_whisper(["-l", "auto", "-np"], wav, "whisper (transcribir la referencia)").stdout
    finally:
        wav.unlink(missing_ok=True)
    (out / "info.json").write_text(json.dumps({"source": video.name, "duration": round(dur, 1), "cuts": times,
                                               "shots": len(times)}, indent=2), encoding="utf-8")
    (out / "transcript.txt").write_text(words.strip(), encoding="utf-8")
    return out
