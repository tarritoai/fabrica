"""Voices beyond reading a script (ElevenLabs): find one in the public library (free), DESIGN a new one from a
description (3 samples to listen to; costs), keep it in your account and in personajes/<id>/personaje.json (free),
try it with a sentence (costs a few credits), and «act it yourself»: your own recording comes out in a character's
voice (speech to speech; costs).

The key is read from .env and never printed. If the account's plan does not allow something through the API, the
message says how to do it in the ElevenLabs website instead.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import time
from pathlib import Path

import httpx

from reels import characters, system
from reels.assets import ROOT, episode_dir

API = "https://api.elevenlabs.io/v1"
DESIGNS = ROOT / ".cache" / "diseno-voz"
TRIES = ROOT / ".cache" / "pruebas-voz"
DESIGN_MODEL = "eleven_ttv_v3"
STS_MODEL = "eleven_multilingual_sts_v2"
DEFAULT_SAMPLE = ("¿Y si los gatos pudieran votar? Primera ley: siesta obligatoria. Segunda ley: la caja es de quien "
                  "la ocupa. Y el lunes, cerrado por siesta.")


def _key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("falta tu clave de ElevenLabs: pégala en .env (ELEVENLABS_API_KEY=…)")
    return key


def _web(motivo: str) -> RuntimeError:
    return RuntimeError(f"{motivo}. Hazlo en la web de ElevenLabs (elevenlabs.io → Voices) y dile a Claude el voice_id: "
                        "lo guarda en personajes/<id>/personaje.json.")


def _check(r: httpx.Response, what: str) -> None:
    if r.status_code in (401, 402, 403):
        raise _web(f"tu cuenta no deja {what} desde fuera de la web (HTTP {r.status_code}: plan o permisos de la clave)")
    if r.status_code >= 300:
        raise RuntimeError(f"ElevenLabs ha dicho que no al {what} (HTTP {r.status_code}): {r.text[:300]}")


# --- library (free) -------------------------------------------------------------------------------------------------


def search(query: str, accent: str = "", n: int = 12) -> list[dict]:
    params = {"page_size": n, "language": "es", "search": query}
    if accent:
        params["accent"] = accent
    r = httpx.get(f"{API}/shared-voices", params=params, headers={"xi-api-key": _key()}, timeout=30)
    _check(r, "buscar en la biblioteca")
    voices = r.json().get("voices", [])
    cache = ROOT / ".cache" / "voces-biblioteca.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for v in voices:
        old[v["voice_id"]] = {k: v.get(k) for k in ("name", "accent", "gender", "age", "descriptive", "public_owner_id", "preview_url")}
    cache.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    return voices


def use_library(voice_id: str, char_id: str) -> Path:
    """Add a library voice to My Voices (free) and give it to a character."""
    key = _key()
    meta = json.loads((ROOT / ".cache" / "voces-biblioteca.json").read_text(encoding="utf-8")).get(voice_id, {}) \
        if (ROOT / ".cache" / "voces-biblioteca.json").exists() else {}
    mine = httpx.get(f"{API}/voices/{voice_id}", headers={"xi-api-key": key}, timeout=30)
    if mine.status_code == 200:
        meta = {**meta, "name": meta.get("name") or mine.json().get("name")}
    else:
        owner = meta.get("public_owner_id")
        if not owner:
            raise RuntimeError("no sé de quién es esa voz: búscala antes con `reels voice-search`")
        r = httpx.post(f"{API}/voices/add/{owner}/{voice_id}", headers={"xi-api-key": key},
                       json={"new_name": (meta.get("name") or voice_id)[:40]}, timeout=30)
        _check(r, "añadir la voz a tus voces")
    return _give(char_id, {"voice_id": voice_id, "name": meta.get("name") or voice_id, "origin": "biblioteca"})


def _give(char_id: str, voice: dict) -> Path:
    data = characters.load(char_id) or {"id": char_id, "display_name": char_id.capitalize(),
                                        "role": "narrador" if char_id == "narrador" else "personaje", "piece": None, "props": {}}
    data["voice"] = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.2, **(data.get("voice") or {}), **voice}
    return characters.save(char_id, data)


# --- design (costs) -------------------------------------------------------------------------------------------------


def design(description: str, text: str | None = None) -> Path:
    """Three samples of a NEW voice described with words → .cache/diseno-voz/<time>/ + a page to listen to them."""
    sample = text or DEFAULT_SAMPLE
    if len(sample) < 100:
        sample = (sample + " " + DEFAULT_SAMPLE)[:300]
    body = {"voice_description": description, "text": sample, "model_id": DESIGN_MODEL}
    r = httpx.post(f"{API}/text-to-voice/design", headers={"xi-api-key": _key()}, json=body, timeout=240)
    _check(r, "diseño de voz")
    data = r.json()
    folder = DESIGNS / time.strftime("%Y%m%d-%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, p in enumerate(data.get("previews", []), start=1):
        (folder / f"muestra-{i}.mp3").write_bytes(base64.b64decode(p.pop("audio_base_64")))
        rows.append(f'<div class="r"><b>Muestra {i}</b><audio controls src="muestra-{i}.mp3"></audio></div>')
    credits = r.headers.get("character-cost")
    (folder / "diseno.json").write_text(json.dumps({"description": description, "text": sample, "credits": credits, **data},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    page = folder / "muestras.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><title>Muestras</title><style>body{font-family:system-ui;background:#F2E7D5;'
        'color:#1E1712;max-width:720px;margin:40px auto;padding:0 16px}.r{display:flex;gap:14px;align-items:center;margin:12px 0}</style>'
        f"<h1>Voz diseñada</h1><p>{html.escape(description)}</p><p><i>{html.escape(sample)}</i></p>" + "".join(rows) +
        "<p>¿Te gusta una? Dile a Claude el número: <code>uv run reels voice-save N --nombre \"…\"</code></p>", encoding="utf-8")
    return page


def latest_design() -> Path:
    folders = sorted(p for p in DESIGNS.glob("*") if (p / "diseno.json").exists()) if DESIGNS.exists() else []
    if not folders:
        raise RuntimeError("todavía no has diseñado ninguna voz: `uv run reels voice-design \"…\"`")
    return folders[-1]


def save_design(sample: int, name: str, char_id: str = "narrador") -> Path:
    folder = latest_design()
    data = json.loads((folder / "diseno.json").read_text(encoding="utf-8"))
    previews = data.get("previews", [])
    if not 1 <= sample <= len(previews):
        raise ValueError(f"esa muestra no existe: hay {len(previews)}")
    body = {"voice_name": name[:40], "voice_description": data["description"][:500],
            "generated_voice_id": previews[sample - 1]["generated_voice_id"]}
    r = httpx.post(f"{API}/text-to-voice", headers={"xi-api-key": _key()}, json=body, timeout=60)
    _check(r, "guardar la voz diseñada")
    voice_id = r.json()["voice_id"]
    return _give(char_id, {"voice_id": voice_id, "name": name, "origin": "diseñada", "description": data["description"]})


# --- try a voice (a few credits) ------------------------------------------------------------------------------------


def try_voice(char_id: str, sentence: str) -> Path:
    data = characters.load(char_id)
    if not data or not (data.get("voice") or {}).get("voice_id"):
        raise RuntimeError(f"«{char_id}» no tiene voz todavía (personajes/{char_id}/personaje.json)")
    v = data["voice"]
    body = {"text": sentence, "model_id": "eleven_v4", "language_code": "es",
            "voice_settings": {k: v.get(k, d) for k, d in (("stability", 0.5), ("similarity_boost", 0.75), ("style", 0.2))}}
    key = hashlib.sha256(json.dumps([v["voice_id"], body], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    dest = TRIES / f"{char_id}-{key}.mp3"
    if dest.exists():
        return dest
    r = httpx.post(f"{API}/text-to-speech/{v['voice_id']}", headers={"xi-api-key": _key()}, json=body, timeout=120)
    _check(r, "probar la voz")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


# --- act it yourself: speech to speech (costs) ----------------------------------------------------------------------


def act(slug: str, beat_id: int, recording: Path) -> Path:
    """Your recording → the voice of that beat's character. Saved as episodes/<slug>/actuaciones/beat_NN.mp3 and set as
    the beat's `performance` in script.json (`reels voice` then uses it instead of reading the line)."""
    from reels.schema import Episode
    from reels.voice import voice_of

    if not recording.exists():
        raise FileNotFoundError(f"no encuentro {recording}")
    out = episode_dir(slug)
    path = out / "script.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    ep = Episode.model_validate(raw)
    beat = next((b for b in ep.beats if b.id == beat_id), None)
    if beat is None:
        raise ValueError(f"no hay beat {beat_id}")
    voice = voice_of(ep, beat.voice)
    wav = out / "actuaciones" / f"grabacion_{beat_id:02d}.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(recording), "-ac", "1", "-ar", "44100", str(wav)],
                    "ffmpeg (tu grabación)")
    with wav.open("rb") as fh:
        r = httpx.post(f"{API}/speech-to-speech/{voice.voice_id}", headers={"xi-api-key": _key()},
                       params={"output_format": "mp3_44100_128"},
                       data={"model_id": STS_MODEL, "remove_background_noise": "true"},
                       files={"audio": (wav.name, fh, "audio/wav")}, timeout=240)
    _check(r, "cambio de voz")
    dest = out / "actuaciones" / f"beat_{beat_id:02d}.mp3"
    dest.write_bytes(r.content)
    for b in raw["beats"]:
        if b["id"] == beat_id:
            b["performance"] = f"actuaciones/{dest.name}"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest
