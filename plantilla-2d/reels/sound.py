"""Sound beyond the voices (ElevenLabs): sound effects made to order (assets/sfx/<name>.wav, ~10 credits each) and
original music with Eleven Music (assets/music/clips/<name>.mp3, ~820 credits a minute), plus your own licensed
tracks. Everything paid is cached by its request: asking twice for the same thing never pays twice.

The music catalogue is assets/music/music.json: every track with its licence. A track whose licence says
«no publicar» can be used to rehearse, never to publish.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx

from reels import system
from reels.assets import ASSETS, ROOT, SFX

API = "https://api.elevenlabs.io/v1"
CACHE = ROOT / ".cache" / "sonido"
LIBRARY = ASSETS / "music" / "music.json"
MUSIC_CREDITS_PER_MIN = 820  # measured in the course (22 s ≈ 302 credits)
ELEVEN_LICENCE = "Generada con Eleven Music (ElevenLabs) desde tu cuenta de pago: uso comercial permitido por sus términos; sin atribución obligatoria"


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("falta tu clave de ElevenLabs: pégala en .env (ELEVENLABS_API_KEY=…)")
    return key


def _cached_post(path: str, body: dict, params: dict | None = None, timeout: float = 600) -> Path:
    h = hashlib.sha256(json.dumps([path, body], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    f = CACHE / f"{h}.mp3"
    if f.exists():
        return f
    r = httpx.post(f"{API}{path}", params=params or {}, headers={"xi-api-key": _key()}, json=body, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs ha dicho que no (HTTP {r.status_code}): {r.text[:300]}")
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(r.content)
    return f


def sound_effect(name: str, prompt: str, seconds: float = 1.0, influence: float = 0.6) -> Path:
    src = _cached_post("/sound-generation", {"text": prompt, "duration_seconds": seconds, "prompt_influence": influence})
    dest = SFX / f"{name}.wav"
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ar", "48000", "-ac", "2", str(dest)], "ffmpeg")
    return dest


def load() -> list[dict]:
    return json.loads(LIBRARY.read_text(encoding="utf-8")) if LIBRARY.exists() else []


def _register(entry: dict) -> dict:
    tracks = [t for t in load() if t["file"] != entry["file"]] + [entry]
    LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY.write_text(json.dumps(tracks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return entry


def compose(name: str, prompt: str, seconds: float, mood: str) -> dict:
    body = {"model_id": "music_v1", "music_length_ms": int(seconds * 1000),
            "prompt": prompt if "no vocals" in prompt.lower() else f"Instrumental only, no vocals. {prompt}"}
    src = _cached_post("/music", body, {"output_format": "mp3_44100_128"})
    dest = ASSETS / "music" / "clips" / f"{name}.mp3"
    dest.parent.mkdir(parents=True, exist_ok=True)
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "192k", str(dest)], "ffmpeg")
    return _register({"file": f"clips/{name}.mp3", "mood": mood, "duration": seconds, "license": ELEVEN_LICENCE,
                      "source": "Eleven Music", "prompt": body["prompt"]})


def import_track(source: Path, name: str, licence: str, mood: str) -> dict:
    if not source.exists():
        raise FileNotFoundError(f"no encuentro {source}")
    dest = ASSETS / "music" / "clips" / f"{name}.mp3"
    dest.parent.mkdir(parents=True, exist_ok=True)
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(source), "-af", "loudnorm=I=-20:TP=-2",
                     "-c:a", "libmp3lame", "-b:a", "192k", str(dest)], "ffmpeg")
    return _register({"file": f"clips/{name}.mp3", "mood": mood, "license": licence, "source": source.name})
