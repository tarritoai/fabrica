"""Music library (PLAN.md §5b): assets/music/music.json + clips cut from source files."""

from __future__ import annotations

import json
import subprocess
import zlib
from pathlib import Path

from reels.assets import ASSETS
from reels import system

LIBRARY = ASSETS / "music" / "music.json"


def load() -> list[dict]:
    return json.loads(LIBRARY.read_text(encoding="utf-8")) if LIBRARY.exists() else []


def import_clips(source: Path, mood: str, starts: list[float], length: float, license_note: str) -> list[dict]:
    """Cut `length`-second clips at `starts`, loudness-normalised, and register them."""
    tracks = load()
    out_dir = LIBRARY.parent / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    added = []
    for start in starts:
        name = f"{mood}_{zlib.crc32(source.name.encode()):08x}_{int(start):05d}.mp3"
        dest = out_dir / name
        subprocess.run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{start}", "-t", f"{length}", "-i", str(source),
             "-af", f"loudnorm=I=-20:TP=-2,afade=t=in:d=1.5,afade=t=out:st={length - 2}:d=2",
             "-ar", "44100", "-b:a", "192k", str(dest)],
            check=True,
        )
        entry = {
            "file": f"clips/{name}",
            "mood": mood,
            "duration": length,
            "source": source.name,
            "source_start": start,
            "license": license_note,
            "bpm": None,
            "moment": None,
        }
        tracks = [t for t in tracks if t["file"] != entry["file"]] + [entry]
        added.append(entry)
    LIBRARY.write_text(json.dumps(tracks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def choose(mood: str, slug: str, track: str | None = None) -> dict | None:
    """The clip the episode names (music.track), else a deterministic pick per episode among that mood's clips."""
    if track:
        return next((t for t in load() if t["file"] == track), None)
    options = [t for t in load() if t["mood"] == mood] or load()
    if not options:
        return None
    # Tracks the user marked as preferred ("priority") win over the rest of the mood.
    top = max(t.get("priority", 0) for t in options)
    options = [t for t in options if t.get("priority", 0) == top]
    return options[zlib.crc32(slug.encode()) % len(options)]


MUSIC_CREDITS_PER_MIN = 900  # Eleven Music in subscription credits (ElevenLabs pricing page, oct. 2026)
GENERATED_LICENSE = ("Generada con Eleven Music (ElevenLabs) desde una cuenta de pago: uso comercial permitido por sus "
                     "términos; sin atribución obligatoria")


def generate(prompt: str, seconds: float, mood: str, name: str) -> dict:
    """Compose an instrumental track with Eleven Music (COSTS ~900 credits/min), keep the original in
    assets/music/src/ and register it as one clip of its whole length. Cached by name: the same name is not paid twice."""
    import os

    import httpx

    src_dir = LIBRARY.parent / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    src = src_dir / f"{name}.mp3"
    if not src.exists():
        r = httpx.post("https://api.elevenlabs.io/v1/music", params={"output_format": "mp3_44100_128"},
                       headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, timeout=600,
                       json={"prompt": prompt, "music_length_ms": int(seconds * 1000), "model_id": "music_v1",
                             "force_instrumental": True})
        if r.status_code != 200:
            raise RuntimeError(f"Eleven Music HTTP {r.status_code}: {r.text[:300]}")
        src.write_bytes(r.content)
        (src_dir / f"{name}.txt").write_text(prompt + "\n", encoding="utf-8")
    entry = import_clips(src, mood, [0.0], seconds, GENERATED_LICENSE)[0]
    return entry
