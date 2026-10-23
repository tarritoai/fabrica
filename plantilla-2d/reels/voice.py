"""Voices of the 2D factory (ElevenLabs v4, text-to-speech WITH TIMESTAMPS): script.json → audio/*.wav + voice.json.

How a reel is voiced:
- consecutive beats of the same voice are ONE take (one request): the narrator says its lines in one breath and the
  prosody flows; a character's reply is its own take, with the text said before it as `previous_text` so it answers
  the scene instead of talking into the void;
- every request is cached by a hash of its payload in .cache/voice/ (voices cost money: the same take is never paid
  twice; never delete that folder);
- ElevenLabs returns the time of every character: that gives the time of every WORD, which is what captions, mouths,
  speech bubbles and events hang from;
- the take is tightened for the «¿Y si…?» rhythm (v4 has no speed setting): pauses longer than pace.max_pause are
  shortened to it and the whole take is sped up by pace.tempo without changing the pitch (ffmpeg rubberband, or
  atempo when this ffmpeg has no rubberband). The word times go through the same transformation;
- whisper (the «ear») listens to each processed take and says how faithful it is.

Placing the takes in the reel (gaps, lead-in) is reels/timeline.py's job, so changing them is free.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import httpx
from rich.console import Console

from reels import cost, system
from reels.assets import ROOT, episode_dir, personaje
from reels.schema import Beat, Episode, Voice

MODEL = "eleven_v4"
LANGUAGE = "es"
SEED = 1000
CACHE = ROOT / ".cache" / "voice"
API = "https://api.elevenlabs.io/v1"
OUTPUT_FORMAT = "mp3_44100_128"
CREDITS_PER_CHAR = 0.45  # measured in the course with eleven_v4 (0.33–0.46); the estimate uses 1 per character
MIN_SIMILARITY = 0.6

console = Console()


class SpendError(RuntimeError):
    """A take is not in the cache and spending was not allowed."""


# --- numbers as words -----------------------------------------------------------------------------------------------

_UNITS = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete "
          "dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete "
          "veintiocho veintinueve").split()
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos",
             7: "setecientos", 8: "ochocientos", 9: "novecientos"}
_NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})+|\d+")
_FEMININE = {"veces", "personas", "horas", "semanas", "páginas", "paginas", "locuras", "vidas", "cosas", "ideas", "veces."}


def spell(n: int) -> str:
    """Spanish number words (0–999 999)."""
    if n < 30:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return _TENS[tens * 10] + (f" y {_UNITS[unit]}" if unit else "")
    if n == 100:
        return "cien"
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return _HUNDREDS[hundreds] + (f" {spell(rest)}" if rest else "")
    if n < 1_000_000:
        thousands, rest = divmod(n, 1000)
        return ("mil" if thousands == 1 else f"{spell(thousands)} mil") + (f" {spell(rest)}" if rest else "")
    return str(n)


def spell_numbers(text: str) -> str:
    def one(m: re.Match) -> str:
        words = spell(int(m.group().replace(".", "")))
        nxt = re.match(r"\s+(\w+)", text[m.end():])
        prv = re.search(r"(\w+)\W*\s*$", text[:m.start()])
        if (nxt and nxt.group(1).lower() in _FEMININE) or (prv and prv.group(1).lower() in _FEMININE):
            words = re.sub(r"ientos\b", "ientas", words).replace("quinientos", "quinientas")
            words = re.sub(r"uno$", "una", words)
        return words
    return _NUMBER.sub(one, text)


def normalize(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = unicodedata.normalize("NFKD", spell_numbers(text).lower())
    return "".join(c for c in text if c.isalnum())


# --- takes ----------------------------------------------------------------------------------------------------------


def tts_text(beat: Beat) -> str:
    tags = " ".join(f"[{t.strip('[] ')}]" for t in beat.tags)
    return f"{tags} {spell_numbers(beat.line)}".strip()


@dataclass
class Take:
    index: int
    voice: str
    beats: list[Beat]
    seed: int
    previous: str | None
    text: str = ""
    spans: list[tuple[int, int, int]] = field(default_factory=list)  # (beat id, first char, end char) in text

    def __post_init__(self) -> None:
        pos, parts = 0, []
        for b in self.beats:
            t = tts_text(b)
            self.spans.append((b.id, pos, pos + len(t)))
            parts.append(t)
            pos += len(t) + 1
        self.text = " ".join(parts)


def takes(ep: Episode) -> list[Take]:
    """Consecutive beats of the same voice = one take (one request, one flowing reading). A new take starts when the
    voice changes, at a `pause_before`, at a line you acted yourself and, with pace.hook_alone, right after the hook.
    A take answers the previous one (`previous_text`) only when it is another voice replying: so changing the hook
    (a B hook) never changes — nor pays again — the narrator's takes after it."""
    groups: list[list[Beat]] = []
    for i, b in enumerate(ep.beats):
        joinable = groups and groups[-1][0].voice == b.voice and b.pause_before is None
        after_hook = ep.pace.hook_alone and i == 1
        if joinable and not after_hook and not b.performance and not groups[-1][-1].performance:
            groups[-1].append(b)
        else:
            groups.append([b])
    out: list[Take] = []
    for i, g in enumerate(groups):
        prev = out[-1] if out else None
        previous = prev.text if prev and prev.voice != g[0].voice else None
        out.append(Take(i + 1, g[0].voice, g, SEED + max(b.take for b in g) - 1, previous))
    return out


def signature(ep: Episode) -> dict:
    """What the processed voices depend on: if it changes, voice.json is out of date (re-made from the cache, free)."""
    return {"pace": ep.pace.model_dump(), "takes": [[t.voice, t.text, t.seed, t.previous, bool(t.beats[0].performance)]
                                                    for t in takes(ep)]}


def ensure_voice(ep: Episode) -> None:
    """Before drawing: voice.json must match the script. If only the rhythm or the grouping changed, it is re-made
    from the cache for free; if a take is new, say what to do (it costs)."""
    path = episode_dir(ep.slug) / "voice.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("signature") == signature(ep):
        return
    try:
        voice_episode(ep, allow_spend=False, listen=False)
    except SpendError as e:
        est = estimate(ep)
        raise SpendError(f"{e}. Primero `uv run reels voice {ep.slug}` (como mucho {est['credits_max']} créditos, "
                         f"lo normal ~{est['credits_likely']}): avisa antes de gastar.") from None


def voice_of(ep: Episode, key: str) -> Voice:
    v = ep.voices[key]
    if isinstance(v, Voice):
        return v
    data = personaje(v).get("voice") or {}
    if not data.get("voice_id"):
        raise ValueError(f"el personaje «{v}» no tiene voz todavía (voice.voice_id en personajes/{v}/personaje.json)")
    return Voice(**{k: data[k] for k in ("voice_id", "name", "stability", "similarity_boost", "style") if k in data})


def payload(take: Take, voice: Voice) -> dict:
    data = {
        "text": take.text,
        "model_id": MODEL,
        "language_code": LANGUAGE,
        "voice_settings": {"stability": voice.stability, "similarity_boost": voice.similarity_boost, "style": voice.style},
        "seed": take.seed,
    }
    if take.previous:
        data["previous_text"] = take.previous
    return data


def cache_key(voice_id: str, data: dict) -> str:
    return hashlib.sha256(json.dumps({"v": voice_id, **data}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def cached(voice_id: str, data: dict) -> tuple[Path, dict] | None:
    k = cache_key(voice_id, data)
    mp3, meta = CACHE / f"{k}.mp3", CACHE / f"{k}.json"
    if mp3.exists() and meta.exists():
        return mp3, json.loads(meta.read_text(encoding="utf-8"))
    return None


def request(client: httpx.Client, voice_id: str, data: dict) -> tuple[Path, dict, int]:
    """One paid request (text-to-speech with timestamps). Returns (mp3, metadata, credits charged)."""
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("falta tu clave de ElevenLabs: pégala en .env (ELEVENLABS_API_KEY=…) y vuelve a probar")
    r = client.post(f"{API}/text-to-speech/{voice_id}/with-timestamps", params={"output_format": OUTPUT_FORMAT},
                    headers={"xi-api-key": key}, json=data)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs ha dicho que no (HTTP {r.status_code}): {r.text[:300]}")
    body = r.json()
    CACHE.mkdir(parents=True, exist_ok=True)
    k = cache_key(voice_id, data)
    mp3 = CACHE / f"{k}.mp3"
    mp3.write_bytes(base64.b64decode(body.pop("audio_base64")))
    body.pop("normalized_alignment", None)
    credits = int(r.headers.get("character-cost") or len(data["text"]))
    meta = {"alignment": body.get("alignment"), "credits": credits, "voice_id": voice_id, "payload": data}
    (CACHE / f"{k}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return mp3, meta, credits


def estimate(ep: Episode) -> dict:
    """Characters that would be paid now (takes not in the cache yet) and the credits, at most (1 per character)."""
    new = cached_n = 0
    for t in takes(ep):
        if t.beats[0].performance:
            continue
        v = voice_of(ep, t.voice)
        if cached(v.voice_id, payload(t, v)):
            cached_n += len(t.text)
        else:
            new += len(t.text)
    return {"characters_new": new, "characters_cached": cached_n, "credits_max": new,
            "credits_likely": round(new * CREDITS_PER_CHAR)}


# --- word times -----------------------------------------------------------------------------------------------------


def words_from_alignment(al: dict) -> list[dict]:
    """Characters → words with start/end. Text inside [tags] is not a word. Punctuation stays glued to its word."""
    chars, t0, t1 = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, start, first, depth = [], "", None, 0, 0
    for i, c in enumerate(chars):
        if c == "[":
            depth += 1
        if depth or c.isspace():
            if cur:
                words.append({"text": cur, "start": start, "end": t1[i - 1], "char": first})
            cur, start = "", None
            if c == "]":
                depth = max(0, depth - 1)
            continue
        if not cur:
            start, first = t0[i], i
        cur += c
    if cur:
        words.append({"text": cur, "start": start, "end": t1[-1], "char": first})
    return words


def line_words(take: Take, spoken: list[dict]) -> list[dict]:
    """Spoken words (numbers spelled out) → the words of each beat's LINE as written, with their times."""
    out: list[dict] = []
    for beat, (bid, a, b) in zip(take.beats, take.spans):
        mine = [w for w in spoken if a <= w["char"] < b]
        tokens = beat.line.split()
        counts = [max(1, len(spell_numbers(tok).split())) for tok in tokens]
        if mine and sum(counts) == len(mine):
            k = 0
            for tok, n in zip(tokens, counts):
                group = mine[k:k + n]
                k += n
                out.append({"text": tok, "start": group[0]["start"], "end": group[-1]["end"], "beat": bid})
        elif mine:  # the voice said something slightly different: spread its words over the written ones
            for i, tok in enumerate(tokens):
                j0 = int(i * len(mine) / len(tokens))
                j1 = max(j0, int((i + 1) * len(mine) / len(tokens)) - 1)
                out.append({"text": tok, "start": mine[j0]["start"], "end": mine[j1]["end"], "beat": bid})
    return out


# --- audio processing -----------------------------------------------------------------------------------------------


def duration(path: Path) -> float:
    out = subprocess.run([system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return float(out.stdout.strip())


def silences(path: Path, min_len: float, noise_db: int = -40) -> list[tuple[float, float]]:
    out = subprocess.run([system.ffmpeg(), "-hide_banner", "-i", str(path), "-af", f"silencedetect=n={noise_db}dB:d={min_len}",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", out)]
    return list(zip(starts, ends))


@cache
def has_rubberband() -> bool:
    out = subprocess.run([system.ffmpeg(), "-hide_banner", "-filters"], capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout
    return re.search(r"\srubberband\s", out) is not None


def tempo_filter(tempo: float) -> str:
    if abs(tempo - 1.0) < 1e-3:
        return "anull"
    return f"rubberband=tempo={tempo}" if has_rubberband() else f"atempo={tempo}"


def tighten(src: Path, dst: Path, max_pause: float, tempo: float):
    """Shorten long pauses inside the take and speed it up. Returns the old→new time map for the word times."""
    total = duration(src)
    cuts = []
    for s0, s1 in silences(src, max_pause + 0.02):
        if s0 <= 0.01 or s1 >= total - 0.01:
            continue
        mid = (s0 + s1) / 2
        half = (s1 - s0 - max_pause) / 2
        cuts.append((mid - half, mid + half))
    keep, prev = [], 0.0
    for a, b in cuts:
        keep.append((prev, a))
        prev = b
    keep.append((prev, total))
    parts = "".join(f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS[k{i}];" for i, (a, b) in enumerate(keep))
    graph = (parts + "".join(f"[k{i}]" for i in range(len(keep))) +
             f"concat=n={len(keep)}:v=0:a=1,{tempo_filter(tempo)},aresample=48000[o]")
    dst.parent.mkdir(parents=True, exist_ok=True)
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", graph, "-map", "[o]",
                     "-ac", "1", "-ar", "48000", str(dst)], "ffmpeg (apretar la voz)")

    def remap(t: float) -> float:
        removed = 0.0
        for a, b in cuts:
            if t >= b:
                removed += b - a
            elif t > a:
                removed += t - a
        return (t - removed) / tempo

    return remap


def mean_volume(path: Path) -> float:
    out = subprocess.run([system.ffmpeg(), "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"mean_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else -19.0


def transcribe(audio: Path, pad: bool = True) -> str | None:
    """What whisper hears (None if whisper or its model is not installed yet)."""
    if not system.find_whisper() or not system.whisper_model().exists():
        return None
    wav = audio.with_name(audio.stem + ".16k.wav")
    # Half a second of silence on each side: on short clips whisper otherwise drops the last words.
    filters = ["-af", "adelay=delays=500:all=1,apad=pad_dur=0.5"] if pad else []
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(audio), *filters, "-ar", "16000", "-ac", "1", str(wav)],
                    "ffmpeg")
    try:
        out = system.run_whisper(["-l", LANGUAGE, "-nt", "-np"], wav, "whisper (el oído)")
    finally:
        wav.unlink(missing_ok=True)
    return out.stdout.strip()


def similarity(expected: str, heard: str) -> float:
    return round(difflib.SequenceMatcher(None, normalize(expected), normalize(heard), autojunk=False).ratio(), 3)


# --- entry point ----------------------------------------------------------------------------------------------------


def voice_episode(ep: Episode, allow_spend: bool = True, listen: bool = True) -> dict:
    """Generate (or take from the cache) every take, process it and write episodes/<slug>/voice.json."""
    out = episode_dir(ep.slug)
    audio = out / "publico" / "audio"
    if audio.exists():
        shutil.rmtree(audio)
    audio.mkdir(parents=True)
    work = out / ".voz"
    work.mkdir(exist_ok=True)
    old = out / "voice.json"
    before = json.loads(old.read_text(encoding="utf-8")).get("credits_total", 0) if old.exists() else 0
    result = {"model": MODEL, "takes": [], "credits": 0, "signature": signature(ep)}
    missing = []
    plan = takes(ep)
    for t in plan:
        v = voice_of(ep, t.voice)
        if not t.beats[0].performance and not cached(v.voice_id, payload(t, v)):
            missing.append(t)
    if missing and not allow_spend:
        chars = sum(len(t.text) for t in missing)
        raise SpendError(f"faltan {len(missing)} tomas que no están en la caché ({chars} caracteres): esto gastaría créditos")
    with httpx.Client(timeout=180) as client:
        for t in plan:
            v = voice_of(ep, t.voice)
            if t.beats[0].performance:
                result["takes"].append(_performance_take(ep, t, v, audio, work, listen))
                console.print(f"  toma {t.index} · {t.voice} · beat {t.beats[0].id} · [cyan]tu actuación[/]")
                continue
            data = payload(t, v)
            hit = cached(v.voice_id, data)
            if hit:
                mp3, meta = hit
                credits = 0
            else:
                mp3, meta, credits = request(client, v.voice_id, data)
            result["credits"] += credits
            raw = work / f"toma_{t.index:02d}.wav"
            system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "48000", str(raw)], "ffmpeg")
            dst = audio / f"toma_{t.index:02d}.wav"
            remap = tighten(raw, dst, ep.pace.max_pause, ep.pace.tempo)
            spoken = words_from_alignment(meta["alignment"])
            words = line_words(t, spoken)
            for w in words:
                w["start"], w["end"] = round(remap(w["start"]), 3), round(remap(w["end"]), 3)
            heard = transcribe(dst) if listen else None
            sim = similarity(" ".join(b.line for b in t.beats), heard) if heard is not None else None
            info = {"take": t.index, "file": f"audio/{dst.name}", "voice": t.voice, "voice_id": v.voice_id,
                    "beats": [b.id for b in t.beats], "seed": t.seed, "cached": bool(hit), "credits": credits,
                    "duration": round(duration(dst), 3), "mean_db": round(mean_volume(dst), 1), "words": words,
                    "heard": heard, "similarity": sim}
            result["takes"].append(info)
            mark = "[dim]caché[/]" if hit else f"[cyan]nueva · {credits} créditos[/]"
            ear = "" if sim is None else (f"  oído {sim:.2f}" if sim >= MIN_SIMILARITY else f"  [yellow]oído {sim:.2f}: escúchala[/]")
            console.print(f"  toma {t.index} · {t.voice} · beats {', '.join(map(str, info['beats']))} · {mark}{ear}")
    shutil.rmtree(work, ignore_errors=True)
    result["credits_total"] = before + result["credits"]  # everything paid for this episode's voices, ever
    (out / "voice.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    if result["credits"]:
        cost.log(out, "voice", result["credits"] * cost.ELEVENLABS_USD_PER_CREDIT, credits=result["credits"], model=MODEL)
    return result


def _performance_take(ep: Episode, t: Take, v: Voice, audio: Path, work: Path, listen: bool) -> dict:
    """A line acted by you (reels voice-act): its audio as it is, and its words spread over the voiced stretch by length
    (there are no character times for a recording)."""
    beat = t.beats[0]
    src = episode_dir(ep.slug) / beat.performance
    if not src.exists():
        raise FileNotFoundError(f"beat {beat.id}: no encuentro tu actuación {src} (vuelve a hacer `reels voice-act`)")
    dst = audio / f"toma_{t.index:02d}.wav"
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "48000", str(dst)], "ffmpeg")
    total = duration(dst)
    quiet = silences(dst, 0.08)
    start = quiet[0][1] if quiet and quiet[0][0] <= 0.02 else 0.0
    end = quiet[-1][0] if quiet and quiet[-1][1] >= total - 0.05 else total
    tokens = beat.line.split()
    weights = [max(1, len(normalize(tok))) for tok in tokens]
    span, acc, words = max(0.2, end - start), 0.0, []
    for tok, w in zip(tokens, weights):
        a = start + span * acc / sum(weights)
        acc += w
        b = start + span * acc / sum(weights)
        words.append({"text": tok, "start": round(a, 3), "end": round(b - 0.03, 3), "beat": beat.id})
    heard = transcribe(dst) if listen else None
    return {"take": t.index, "file": f"audio/{dst.name}", "voice": t.voice, "voice_id": v.voice_id, "beats": [beat.id],
            "seed": None, "cached": True, "credits": 0, "duration": round(total, 3), "mean_db": round(mean_volume(dst), 1),
            "words": words, "heard": heard, "similarity": similarity(beat.line, heard) if heard is not None else None,
            "performance": beat.performance}
