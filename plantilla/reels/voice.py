"""Voices (PLAN.md §5a): ElevenLabs v4 Text to Dialogue, several takes, automatic filter.

The whole conversation is generated in one request so turns sound like a real
exchange. Every request is cached by a hash of its payload (voices cost money).
Takes are filtered with a local whisper.cpp transcription (wrong words, clipping,
implausible duration) and the best one is sliced into per-beat audio using the
provider's voice_segments. Per-line TTS is the fallback if dialogue fails.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import httpx
from rich.console import Console

from reels import cast, cost
from reels.assets import ROOT, character, episode_dir
from reels.schema import Beat, Episode
from reels import system

# v4 over v3 (decided 2026-10-17): the base cast's voices were verified as peninsular Spanish on v4 only (v3 drifted
# Latin American) and v4 speaks tighter. v4 ignores voice_settings.speed (same take at 0.7 and 1.2) and has no style
# slider: pace comes from how the line is written (punctuation, tags), never from post-processing.
MODEL = "eleven_v4"
LANGUAGE = "es"
TAKES = 3
# 0.0 (creative: the only mode where strong emotions land), 0.5 (natural) or 1.0 (robust).
STABILITY = 0.5
MIN_SIMILARITY = 0.6
CACHE = ROOT / ".cache" / "voice"
API = "https://api.elevenlabs.io/v1"

console = Console()


# --- requests + cache -------------------------------------------------------


def _cached_post(client: httpx.Client, path: str, payload: dict) -> tuple[Path, dict, bool]:
    """POST to ElevenLabs once per distinct payload. Returns (mp3, metadata, cache_hit)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps([path, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    mp3, meta_path = CACHE / f"{key}.mp3", CACHE / f"{key}.json"
    if mp3.exists() and meta_path.exists():
        return mp3, json.loads(meta_path.read_text(encoding="utf-8")), True
    r = client.post(
        f"{API}{path}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json=payload,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    mp3.write_bytes(base64.b64decode(data.pop("audio_base64")))
    data.pop("normalized_alignment", None)
    meta_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return mp3, data, False


PACE_TAGS = {"rapido": "rushed", "lento": "slowly"}  # v4 takes pacing as a tag; there is no working speed setting


def tts_text(beat: Beat) -> str:
    if beat.delivery and beat.delivery.spoken:
        return _spell_numbers(beat.delivery.spoken)
    names = [t.value for t in beat.delivery.tags] if beat.delivery else []
    if beat.delivery and beat.delivery.pace in PACE_TAGS:
        names.append(PACE_TAGS[beat.delivery.pace])
    tags = " ".join(f"[{t}]" for t in names)
    # Numbers go to the voice as words ("3.802" would be read as "tres punto ochocientos dos"); subtitles keep digits.
    return f"{tags} {_spell_numbers(beat.line)}".strip()


def dialogue_take(client: httpx.Client, beats: list[Beat], seed: int) -> tuple[Path, dict, bool]:
    payload = {
        "model_id": MODEL,
        "language_code": LANGUAGE,
        "settings": {"stability": STABILITY},
        "seed": seed,
        "inputs": [{"voice_id": character(b.speaker.value)["voice"]["voice_id"], "text": tts_text(b)} for b in beats],
    }
    return _cached_post(client, "/text-to-dialogue/with-timestamps", payload)


def _context(spoken: list[Beat], beat: Beat) -> dict:
    """The lines said just before and after (previous_text / next_text), so a solo take answers the scene instead of
    being said into the void. Always from the same list of spoken beats: a picked seed only reproduces its take with
    the same context."""
    i = next(k for k, b in enumerate(spoken) if b.id == beat.id)
    ctx = {}
    if i > 0:
        ctx["previous_text"] = spoken[i - 1].line
    if i + 1 < len(spoken):
        ctx["next_text"] = spoken[i + 1].line
    return ctx


def line_take(client: httpx.Client, beat: Beat, seed: int, spoken: list[Beat] | None = None) -> tuple[Path, dict, bool]:
    """One solo take of a line. spoken: the episode's spoken beats, to give the take the lines around it."""
    voice = character(beat.speaker.value)["voice"]
    if beat.delivery and beat.delivery.seed is not None:
        seed = beat.delivery.seed  # picked by ear
    payload = {
        "model_id": MODEL,
        "language_code": LANGUAGE,
        "seed": seed,
        "text": tts_text(beat),
        "voice_settings": {**voice["settings"], "stability": 0.0 if beat.delivery and beat.delivery.creative else STABILITY},
        **(_context(spoken, beat) if spoken else {}),
    }
    return _cached_post(client, f"/text-to-speech/{voice['voice_id']}/with-timestamps", payload)


# --- automatic filter -------------------------------------------------------


_UNITS = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete veintiocho veintinueve".split()
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_HUNDREDS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def _spell(n: int) -> str:
    """Spanish number words (0–999 999) so whisper's "23" matches a script's "veintitrés"."""
    if n < 30:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return _TENS[tens * 10] + (f" y {_UNITS[unit]}" if unit else "")
    if n == 100:
        return "cien"
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return _HUNDREDS[hundreds] + (f" {_spell(rest)}" if rest else "")
    if n < 1_000_000:
        thousands, rest = divmod(n, 1000)
        head = "mil" if thousands == 1 else f"{_spell(thousands)} mil"
        return head + (f" {_spell(rest)}" if rest else "")
    return str(n)


_NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})+|\d+")  # "3.802" (Spanish thousands dot) or "23"


# Hundreds agree in gender with the noun: "trescientas veces", "doscientas personas".
_FEMININE = {"veces", "personas", "horas", "semanas", "líneas", "lineas", "llamadas", "tareas", "notificaciones"}


def _spell_numbers(text: str) -> str:
    def one(m: re.Match) -> str:
        words = _spell(int(m.group().replace(".", "")))
        nxt = re.match(r"\s+(\w+)", text[m.end():])
        if nxt and nxt.group(1).lower() in _FEMININE:
            words = re.sub(r"ientos\b", "ientas", words).replace("quinientos", "quinientas")
        return words

    return _NUMBER.sub(one, text)


def _normalize(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = _spell_numbers(text)
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if c.isalnum())


def transcribe(audio: Path) -> str:
    wav = audio.with_suffix(".16k.wav")
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(audio), "-ar", "16000", "-ac", "1", str(wav)], check=True)
    try:
        out = system.run_whisper(["-l", LANGUAGE, "-nt", "-np"], wav, "whisper (el oído)")
    finally:
        wav.unlink(missing_ok=True)
    return out.stdout.strip()


def _duration(audio: Path) -> float:
    out = subprocess.run(
        [system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, check=True,
        encoding="utf-8", errors="replace",
    )
    return float(out.stdout)


def _peak_db(audio: Path) -> float:
    out = subprocess.run(
        [system.ffmpeg(), "-i", str(audio), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True
    , encoding="utf-8", errors="replace").stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else -99.0


def score_take(audio: Path, expected: str) -> dict:
    heard = transcribe(audio)
    similarity = difflib.SequenceMatcher(None, _normalize(expected), _normalize(heard), autojunk=False).ratio()
    duration = _duration(audio)
    chars_per_s = len(_normalize(expected)) / max(duration, 0.1)
    problems = []
    if similarity < MIN_SIMILARITY:
        problems.append(f"no dice el texto ({similarity:.2f})")
    if not 4 <= chars_per_s <= 25:
        problems.append(f"duración rara ({duration:.1f}s)")
    if _peak_db(audio) >= -0.1:
        problems.append("clipping")
    return {"heard": heard, "similarity": round(similarity, 3), "duration": round(duration, 2), "problems": problems}


# --- slicing into beats -----------------------------------------------------
# The provider's voice_segments do NOT match the audio (they drift by whole
# lines), so lines are located with whisper.cpp word timestamps (DTW) and cut
# inside the real silences between them. Every slice is then re-transcribed
# and a line that does not say its text is regenerated on its own.

# A slice must say its line and little else: at 0.5 a short line that swallowed the next one ("Este no. Motivo.")
# or a half-cut one ("bien.") slipped through.
SLICE_MIN_SIMILARITY = 0.75
PRE_ROLL = 0.06  # seconds kept before the first syllable
TAIL = 0.12  # seconds kept after the last syllable


def whisper_words(audio: Path) -> list[tuple[str, float, float]]:
    """Word-level timestamps (DTW-aligned) as (text, start, end) in seconds.

    The segment offsets snap to whole seconds (whisper's timestamp tokens), so times come from each token's t_dtw:
    a word runs from the last t_dtw of the word before to the last t_dtw of its own tokens (its trailing punctuation
    lands in the silence after it). DTW needs flash attention off (-nfa): with it on, whisper.cpp >= 1.8 silently
    returns t_dtw = -1. With DTW on, a long clip loops on repeated words ("¡Otra!" x18) and stops decoding, so it is
    transcribed in pieces of at most CHUNK_MAX seconds cut in the middle of its silences."""
    words = []
    for c0, c1 in _whisper_pieces(audio):
        wav = audio.with_name(audio.stem + ".piece.16k.wav")
        subprocess.run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(audio), "-ss", f"{c0:.3f}", "-to", f"{c1:.3f}",
             "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
        prefix = audio.with_name(audio.stem + ".words")
        result_json = Path(f"{prefix}.json")
        system.run_whisper(["-l", LANGUAGE, "-ml", "1", "-sow", "-dtw", "small", "-nfa", "-ojf",
                            "-of", system.native_path(prefix, system.ROOT), "-np"], wav, "whisper (cortar las frases)")
        data = json.loads(result_json.read_text(encoding="utf-8"))
        wav.unlink()
        result_json.unlink()
        prev = 0.0
        for seg in data["transcription"]:
            times = [t["t_dtw"] / 100 for t in seg.get("tokens", []) if t.get("t_dtw", -1) >= 0 and not t["text"].startswith("[_")]
            text = seg["text"].strip()
            if not times:
                continue
            end = min(max(times[-1], prev), c1 - c0)
            if text and not text.startswith("["):
                words.append((text, c0 + prev, c0 + end))
            prev = end
    return words


CHUNK_MAX = 4.0  # seconds per whisper piece in whisper_words


def _whisper_pieces(audio: Path) -> list[tuple[float, float]]:
    """Split a clip into pieces of at most ~CHUNK_MAX s, cutting in the middle of its longest silences."""
    total = _duration(audio)
    cuts = [(q0 + q1) / 2 for q0, q1 in silences(audio) if 0 < q0 and q1 < total]
    pieces, start = [], 0.0
    while total - start > CHUNK_MAX:
        inside = [c for c in cuts if start + 1.0 < c <= start + CHUNK_MAX]
        end = inside[-1] if inside else start + CHUNK_MAX
        pieces.append((start, end))
        start = end
    pieces.append((start, total))
    return pieces


def silences(audio: Path, noise_db: int = -40, min_len: float = 0.12) -> list[tuple[float, float]]:
    out = subprocess.run(
        [system.ffmpeg(), "-hide_banner", "-i", str(audio), "-af", f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", out)]
    total = _duration(audio)
    return [(max(0.0, a), b) for a, b in zip(starts, ends + [total] * (len(starts) - len(ends)))]


def locate_lines(audio: Path, lines: list[str]) -> list[dict]:
    """Return per line: start, end (cut points), gap_before (natural silence) and words."""
    words = whisper_words(audio)
    expected = [(_normalize(w), i) for i, line in enumerate(lines) for w in line.split() if _normalize(w)]
    heard = [_normalize(w[0]) for w in words]
    owner: dict[int, int] = {}
    matcher = difflib.SequenceMatcher(None, [e[0] for e in expected], heard, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # equal: word for word; replace (misheard, "Lucia" for "Lucía"): spread over the words they stand for.
        if tag in ("equal", "replace"):
            for j in range(j1, j2):
                owner[j] = expected[i1 + (j - j1) * (i2 - i1) // (j2 - j1)][1]
    # Extra heard words inherit the line of their neighbours.
    last = 0
    for j in range(len(words)):
        last = owner.setdefault(j, last)

    n, total = len(lines), _duration(audio)
    spans: list[list[float] | None] = [None] * n
    for j, (_, t0, t1) in enumerate(words):
        i = owner[j]
        spans[i] = [t0, t1] if spans[i] is None else [min(spans[i][0], t0), max(spans[i][1], t1)]
    for i in range(n):  # interpolate lines whisper missed entirely
        if spans[i] is None:
            prev_end = spans[i - 1][1] if i and spans[i - 1] else 0.0
            nxt = next((spans[k][0] for k in range(i + 1, n) if spans[k]), total)
            spans[i] = [prev_end, nxt]

    quiet = silences(audio)
    loose = silences(audio, noise_db=-30, min_len=0.06)  # glued turns ("ese. ¡Lucía!") only dip, never go silent
    result = [{"start": max(0.0, spans[0][0] - PRE_ROLL), "end": None, "gap_before": 0.0} for _ in range(n)]
    for i in range(n - 1):
        end_i, start_next = spans[i][1], spans[i + 1][0]
        # The turn gap: the longest silence around the estimated boundary.
        cands = [q for q in quiet if q[1] >= end_i - 0.3 and q[0] <= start_next + 0.3]
        cands = cands or [q for q in loose if q[1] >= end_i - 0.3 and q[0] <= start_next + 0.3]
        if cands:
            q0, q1 = max(cands, key=lambda q: q[1] - q[0])
            result[i]["end"] = min(q0 + TAIL, q1)
            result[i + 1]["start"] = max(q1 - PRE_ROLL, result[i]["end"])
            result[i + 1]["gap_before"] = q1 - q0
        else:
            mid = (end_i + start_next) / 2
            result[i]["end"], result[i + 1]["start"] = mid, mid
    tail_q = [q for q in quiet if q[0] >= spans[-1][1] - 0.2]
    result[-1]["end"] = min(tail_q[0][0] + TAIL, total) if tail_q else total

    for j, (text, t0, t1) in enumerate(words):
        r = result[owner[j]]
        r.setdefault("words", []).append({"text": text, "start": round(t0 - r["start"], 3), "end": round(t1 - r["start"], 3)})
    return result


def _slice(src: Path, start: float, end: float, stem: Path, audio_filter: str | None = None) -> None:
    """Cut [start, end] into beat_XX.mp3 (+ .wav for Rhubarb). audio_filter: e.g. telephone EQ for off-screen voices."""
    af = ["-af", audio_filter] if audio_filter else []
    subprocess.run(
        [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ss", f"{start:.3f}", "-to", f"{end:.3f}", *af,
         "-c:a", "libmp3lame", "-q:a", "2", str(stem.with_suffix(".mp3"))],
        check=True,
    )
    # Rhubarb needs PCM wav.
    subprocess.run(
        [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(stem.with_suffix(".mp3")), "-ac", "1", "-ar", "22050", str(stem.with_suffix(".wav"))],
        check=True,
    )


def _tighten(stem: Path, max_gap: float) -> None:
    """Shorten every pause inside the clip (mp3 + wav) to at most max_gap seconds."""
    af = f"silenceremove=stop_periods=-1:stop_duration={max_gap}:stop_threshold=-32dB:stop_silence={max_gap}"
    for ext, codec in ((".mp3", ["-c:a", "libmp3lame", "-q:a", "2"]), (".wav", [])):
        f = stem.with_suffix(ext)
        tmp = f.with_name(f.stem + ".tight" + ext)
        subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(f), "-af", af, *codec, str(tmp)], check=True)
        tmp.replace(f)


def _write_beat(src: Path, span: dict, beat: Beat, out: Path) -> dict:
    stem = out / f"beat_{beat.id:02d}"
    _slice(src, span["start"], span["end"], stem, character(beat.speaker.value).get("voice_filter"))
    if beat.delivery and beat.delivery.max_gap:
        _tighten(stem, beat.delivery.max_gap)
    shutil.copy(stem.with_suffix(".mp3"), stem.parent / f"{stem.name}.dry.mp3")  # apply_spaces works from this
    heard = transcribe(stem.with_suffix(".mp3"))
    similarity = difflib.SequenceMatcher(None, _normalize(beat.line), _normalize(heard), autojunk=False).ratio()
    info = {
        "text": beat.line,
        "heard": heard,
        "similarity": round(similarity, 3),
        "gap_before": round(span["gap_before"], 3),
        "words": span.get("words", []),
    }
    stem.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    return info


def _slice_dialogue(client: httpx.Client, mp3: Path, beats: list[Beat], out: Path) -> int:
    """Cut the chosen take into beats, verify each slice, regenerate lines that fail. Returns new credits."""
    spans = locate_lines(mp3, [b.line for b in beats])
    credits = 0
    for beat, span in zip(beats, spans):
        if beat.delivery and beat.delivery.seed is not None:
            # A take picked by ear: use it, never the dialogue slice.
            line_mp3, _, hit = line_take(client, beat, seed=beat.delivery.seed, spoken=beats)
            credits += 0 if hit else len(tts_text(beat))
            solo = locate_lines(line_mp3, [beat.line])[0]
            solo["gap_before"] = span["gap_before"]
            info = _write_beat(line_mp3, solo, beat, out)
            console.print(f"  beat {beat.id:>2} [cyan]elegida[/] {info['similarity']:.2f}  «{beat.line}» → «{info['heard']}»")
            continue
        broken = span["end"] - span["start"] < 0.15  # whisper could not place it (end before start)
        info = {"similarity": 0.0, "heard": ""} if broken else _write_beat(mp3, span, beat, out)
        status = f"[green]✔[/] {info['similarity']:.2f}"
        # Extra words at the end (the next speaker bled in) fail too, even if the line itself is all there.
        # Counted in words too: a short line with the previous one glued in front stays under the character margin.
        n_line, n_heard = len(beat.line.split()), len(info["heard"].split())
        extra = len(_normalize(info["heard"])) > 1.3 * len(_normalize(beat.line)) + 4 or n_heard > n_line + max(1, n_line // 4)
        if info["similarity"] < SLICE_MIN_SIMILARITY or extra:
            # This line is not where it should be: generate it alone and trim its silences.
            line_mp3, _, hit = line_take(client, beat, seed=1000, spoken=beats)
            credits += 0 if hit else len(tts_text(beat))
            solo = locate_lines(line_mp3, [beat.line])[0]
            solo["gap_before"] = span["gap_before"]
            info = _write_beat(line_mp3, solo, beat, out)
            status = f"[yellow]regenerada[/] {info['similarity']:.2f}"
        console.print(f"  beat {beat.id:>2} {status}  «{beat.line}» → «{info['heard']}»")
    return credits


# --- entry point ------------------------------------------------------------


def voice_episode(episode: Episode) -> None:
    out = episode_dir(episode.slug) / "audio"
    if out.exists():
        shutil.rmtree(out)
    takes_dir = out / "takes"
    takes_dir.mkdir(parents=True)
    spoken = [b for b in episode.beats if b.line]
    expected = " ".join(b.line for b in spoken)
    chars = sum(len(tts_text(b)) for b in spoken)
    new_credits = 0

    with httpx.Client(timeout=180) as client:
        try:
            takes = []
            for n in range(TAKES):
                mp3, meta, hit = dialogue_take(client, spoken, seed=1000 + n)
                new_credits += 0 if hit else chars
                dest = takes_dir / f"take_{n + 1}.mp3"
                shutil.copy(mp3, dest)
                takes.append({"take": n + 1, "file": f"takes/{dest.name}", "cached": hit, "meta": meta, "src": dest})
                console.print(f"  toma {n + 1}: {'[dim]caché[/]' if hit else '[cyan]nueva[/]'}")
            for t in takes:
                t.update(score_take(t["src"], expected))
            ok = [t for t in takes if not t["problems"]]
            best = max(ok or takes, key=lambda t: t["similarity"])
            if not ok:
                console.print("[yellow]  ninguna toma pasa el filtro; uso la más fiel al texto[/]")
            shutil.copy(best["src"], out / "dialogue.mp3")
            new_credits += _slice_dialogue(client, out / "dialogue.mp3", spoken, out)
            summary = [
                {k: t[k] for k in ("take", "file", "cached", "heard", "similarity", "duration", "problems")} for t in takes
            ]
            (out / "takes.json").write_text(
                json.dumps({"mode": "dialogue", "chosen": best["take"], "takes": summary}, indent=1, ensure_ascii=False)
            , encoding="utf-8")
            for t in summary:
                mark = "[green]✔ elegida[/]" if t["take"] == best["take"] else ""
                issues = ", ".join(t["problems"]) or "ok"
                console.print(f"  toma {t['take']}: similitud {t['similarity']:.2f}, {t['duration']}s, {issues} {mark}")
        except RuntimeError as e:
            console.print(f"[yellow]  dialogue falló ({e}); paso a frase a frase[/]")
            for beat in spoken:
                mp3, _, hit = line_take(client, beat, seed=1000, spoken=spoken)
                new_credits += 0 if hit else len(tts_text(beat))
                span = locate_lines(mp3, [beat.line])[0]
                _write_beat(mp3, span, beat, out)
            (out / "takes.json").write_text(json.dumps({"mode": "per_line", "chosen": None, "takes": []}), encoding="utf-8")

    cost.log(episode_dir(episode.slug), "voice", new_credits * cost.ELEVENLABS_USD_PER_CREDIT, credits=new_credits, model=MODEL)
    new_credits += voice_nonverbal(episode)
    new_credits += voice_chorus(episode)
    apply_spaces(episode)
    console.print(f"[green]✔[/] voces: {new_credits} créditos nuevos de ElevenLabs")


def voice_lines(episode: Episode, ids: list[int]) -> None:
    """Regenerate only some lines (3 solo takes each, the most faithful wins); the rest of the audio stays as is."""
    out = episode_dir(episode.slug) / "audio"
    out.mkdir(parents=True, exist_ok=True)
    spoken = [b for b in episode.beats if b.line]
    beats = {b.id: b for b in spoken}
    missing = [i for i in ids if i not in beats]
    if missing:
        raise ValueError(f"esos beats no tienen frase: {missing}")
    new_credits = 0
    with httpx.Client(timeout=180) as client:
        for i in ids:
            beat = beats[i]
            old = out / f"beat_{i:02d}.json"
            gap = json.loads(old.read_text(encoding="utf-8")).get("gap_before", 0.0) if old.exists() else 0.0
            best = None
            for n in range(TAKES):
                mp3, _, hit = line_take(client, beat, seed=1000 + n, spoken=spoken)
                new_credits += 0 if hit else len(tts_text(beat))
                score = score_take(mp3, beat.line)
                if best is None or (not score["problems"], score["similarity"]) > (not best[1]["problems"], best[1]["similarity"]):
                    best = (mp3, score)
            span = locate_lines(best[0], [beat.line])[0]
            span["gap_before"] = gap
            info = _write_beat(best[0], span, beat, out)
            console.print(f"  beat {i:>2} [green]✔[/] {info['similarity']:.2f}  «{beat.line}» → «{info['heard']}»")
    cost.log(episode_dir(episode.slug), "voice", new_credits * cost.ELEVENLABS_USD_PER_CREDIT, credits=new_credits, model=MODEL)
    new_credits += voice_chorus(episode, ids)
    apply_spaces(episode)
    console.print(f"[green]✔[/] voces: {new_credits} créditos nuevos de ElevenLabs")


# --- wordless sounds and sound effects ------------------------------------------

# v4 performs the tag; the tiny text gives it something to breathe through.
NONVERBAL_TEXT = {"risa": "[laughs softly] Jm.", "suspiro": "[sighs] Ah."}


def voice_nonverbal(episode: Episode) -> int:
    """One clip per beat with `nonverbal`, in the reactor's voice (seed-fixed, cached). Returns new credits."""
    out = episode_dir(episode.slug) / "audio"
    out.mkdir(parents=True, exist_ok=True)
    new_credits = 0
    with httpx.Client(timeout=180) as client:
        for b in episode.beats:
            if not b.nonverbal:
                continue
            who = (b.speaker or b.reactor or cast.HUMAN)
            who = who.value if hasattr(who, "value") else who
            voice = character(who)["voice"]
            text = NONVERBAL_TEXT[b.nonverbal.value]
            payload = {"model_id": MODEL, "language_code": LANGUAGE, "seed": 1000, "text": text,
                       "voice_settings": {**voice["settings"], "stability": STABILITY}}
            mp3, _, hit = _cached_post(client, f"/text-to-speech/{voice['voice_id']}/with-timestamps", payload)
            new_credits += 0 if hit else len(text)
            dest = out / f"nonverbal_{b.id:02d}.mp3"
            # Trim leading/trailing silence so it lands where the beat asks for it.
            subprocess.run(
                [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp3), "-af",
                 "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                 str(dest)],
                check=True,
            )
            console.print(f"  beat {b.id:>2} {b.nonverbal.value} ({who}) {'[dim]caché[/]' if hit else '[cyan]nueva[/]'}")
    if new_credits:
        cost.log(episode_dir(episode.slug), "voice", new_credits * cost.ELEVENLABS_USD_PER_CREDIT, credits=new_credits, model=MODEL)
    return new_credits


def sound_effect(name: str, prompt: str, seconds: float, influence: float = 0.5) -> Path:
    """Generate a sound effect with ElevenLabs into assets/sfx/<name>.wav (cached by prompt)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    payload = {"text": prompt, "duration_seconds": seconds, "prompt_influence": influence}
    key = hashlib.sha256(json.dumps(["sfx", payload], sort_keys=True).encode()).hexdigest()[:24]
    mp3 = CACHE / f"sfx_{key}.mp3"
    if not mp3.exists():
        r = httpx.post(f"{API}/sound-generation", headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, json=payload, timeout=180)
        if r.status_code != 200:
            raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:300]}")
        mp3.write_bytes(r.content)
    dest = ROOT / "assets" / "sfx" / f"{name}.wav"
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "48000", "-ac", "2", str(dest)], check=True)
    return dest


# --- acoustics -------------------------------------------------------------------

# Where a line is heard: an impulse response (assets/sfx/ir_*.wav), how much of it, and how far the speaker is.
# Dry voices all sound like the same booth; this is what puts them in the room (or in the ruins).
SPACES = {
    "room": {"ir": "ir_room.wav", "wet": 0.05},
    "room_far": {"ir": "ir_room.wav", "wet": 0.08, "far": "lowpass=f=7000,volume=0.8"},  # a few metres away
    "ruins": {"ir": "ir_ruins.wav", "wet": 0.22},
    "hall": {"ir": "ir_hall.wav", "wet": 0.5, "predelay": 60},  # something enormous
    # A person's voice coming from a light out in the open sky: softened, airy, with a long gentle tail.
    "luz": {"ir": "ir_hall.wav", "wet": 0.38, "predelay": 30, "far": "highpass=f=170,lowpass=f=6000,acompressor=threshold=-24dB:ratio=2"},
    "luz_lejos": {"ir": "ir_hall.wav", "wet": 0.55, "predelay": 90, "far": "highpass=f=200,lowpass=f=5000"},  # the lonely one
    # The novato shouting from the bathroom (beat.novato_away): tiled echo, a door and a corridor in between.
    "bano": {"ir": "ir_bano.wav", "wet": 0.4, "predelay": 12, "far": "highpass=f=180,lowpass=f=6000,volume=0.8"},
}
DEFAULT_SPACE = {"noche": "room", "ruinas": "ruins"}
TAIL_PAD = {"room": 0.3, "room_far": 0.4, "ruins": 1.2, "hall": 2.0, "luz": 1.4, "luz_lejos": 2.6, "bano": 0.5}  # let the reverb ring out


# --- chorus (delivery.chorus) and the tiny copy (delivery.mini) ---------------------
# A chorus of copies of the same take sounds like a studio effect; each copy is its own solo take instead,
# stretched word by word onto the lead so they speak together, placed where its jar stands in the room.

CHORUS_SEED = 7000
CHORUS_TRIES = 3
MINI_SEMITONES = 4.5
# Where each copy stands (mirrors blender/sets.py `copy_spots`, which Python here cannot import), heard from
# the wide_room camera at (0.45, -3.2): copy k of the chorus is the jar on spot k-1.
COPY_SPOTS = [(0.64, 0.8), (0.6, 0.33), (0.95, -0.15), (-0.42, -0.2), (1.15, 1.1), (1.6, 1.45), (1.9, 1.45),
              (1.35, 0.4), (0.15, 1.8), (-0.95, 0.05), (1.3, -0.45)]
COPY_EAR = (0.45, -3.2)
COPY_JITTER_MS = [9, 21, 14, 27, 17, 11, 24, 19, 13, 29, 16]  # humans never start on the same millisecond


def _ff(*args) -> None:
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", *map(str, args)], check=True)


def _tempo(ratio: float) -> str:
    """atempo chain for any ratio (one atempo only takes 0.5..2)."""
    parts = []
    while ratio > 2:
        parts.append("atempo=2")
        ratio /= 2
    while ratio < 0.5:
        parts.append("atempo=0.5")
        ratio /= 0.5
    return ",".join([*parts, f"atempo={ratio:.5f}"])


def _cut_line(mp3: Path, line: str, dest: Path) -> list[dict]:
    """Cut a solo take down to its line (48k mono wav), dropping anything that bled in after it. Returns its words."""
    span = locate_lines(mp3, [line])[0]
    words = span.get("words", [])
    n = len(line.split())
    if len(words) > n:
        span["end"] = span["start"] + words[n - 1]["end"] + 0.12
        words = words[:n]
    _ff("-i", mp3, "-ss", f"{span['start']:.3f}", "-to", f"{span['end']:.3f}", "-ar", 48000, "-ac", 1, dest)
    return words


def voice_chorus(episode: Episode, ids: list[int] | None = None) -> int:
    """One solo take per extra copy of every chorus line (cached, distinct seeds). Returns new credits."""
    out = episode_dir(episode.slug) / "audio"
    spoken = [b for b in episode.beats if b.line]
    new_credits = 0
    with httpx.Client(timeout=180) as client:
        for b in episode.beats:
            n = b.delivery.chorus if b.line and b.delivery else 1
            if n <= 1 or (ids is not None and b.id not in ids):
                continue
            free = b.model_copy(deep=True)
            free.delivery.seed = None  # a seed picked by ear is for the lead only
            heard = []
            for k in range(1, n):
                wav = out / f"beat_{b.id:02d}.copy{k}.wav"
                for attempt in range(CHORUS_TRIES):  # a copy that does not say its line is redone, like any slice
                    mp3, _, hit = line_take(client, free, seed=CHORUS_SEED + k + 100 * attempt, spoken=spoken)
                    new_credits += 0 if hit else len(tts_text(free))
                    words = _cut_line(mp3, b.line, wav)
                    said = " ".join(w["text"] for w in words)
                    if difflib.SequenceMatcher(None, _normalize(b.line), _normalize(said), autojunk=False).ratio() >= MIN_SIMILARITY:
                        break
                wav.with_suffix(".json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
                heard.append(said)
            console.print(f"  beat {b.id:>2} coro ×{n} «{b.line}» → " + " | ".join(f"«{h}»" for h in heard))
    if new_credits:
        cost.log(episode_dir(episode.slug), "voice", new_credits * cost.ELEVENLABS_USD_PER_CREDIT, credits=new_credits, model=MODEL)
    return new_credits


def _chunks(audio: Path) -> list[tuple[float, float]]:
    """The voiced stretches of a clip (between the silences), which whisper's word times blur on short lines."""
    total, t, out = _duration(audio), 0.0, []
    for q0, q1 in [*silences(audio), (total, total)]:
        if q0 - t > 0.06:
            out.append((t, q0))
        t = q1
    return out or [(0.0, total)]


def _align(src: Path, words: list[dict], lead: Path, lead_words: list[dict], dest: Path) -> None:
    """Stretch src piece by piece onto the lead so they speak together. Anchors: the edges of each voiced stretch
    when both have as many pauses; otherwise the first onset, the last offset and the words they share."""
    mine, theirs = _chunks(src), _chunks(lead)
    # One take breathes where the other runs on: close the shortest pauses of the one with more until they match.
    while 1 < len(mine) != len(theirs) > 1:
        more = mine if len(mine) > len(theirs) else theirs
        k = min(range(len(more) - 1), key=lambda i: more[i + 1][0] - more[i][1])
        more[k:k + 2] = [(more[k][0], more[k + 1][1])]
    if len(mine) == len(theirs):
        pairs = [p for (s0, s1), (l0, l1) in zip(mine, theirs) for p in ((s0, l0), (s1, l1))]
    else:
        pairs = [(mine[0][0], theirs[0][0]), (mine[-1][1], theirs[-1][1])]
        matcher = difflib.SequenceMatcher(None, [_normalize(w["text"]) for w in words],
                                          [_normalize(w["text"]) for w in lead_words], autojunk=False)
        for i, j, n in matcher.get_matching_blocks():
            pairs += [(words[i + k]["start"], lead_words[j + k]["start"]) for k in range(n)
                      if mine[0][0] < words[i + k]["start"] < mine[-1][1] and theirs[0][0] < lead_words[j + k]["start"] < theirs[-1][1]]
    anchors = []
    for sp, lp in sorted(pairs):
        if not anchors or (sp > anchors[-1][0] + 0.03 and lp > anchors[-1][1] + 0.03):
            anchors.append((sp, lp))
    segs = []
    for k, ((s0, l0), (s1, l1)) in enumerate(zip(anchors, anchors[1:])):
        seg = dest.with_name(f"{dest.stem}.seg{k}.wav")
        # Seek on the input: as output options, -ss/-to would cut the stretched result back to the source length.
        _ff("-ss", f"{s0:.3f}", "-to", f"{s1:.3f}", "-i", src, "-af", _tempo(min(2.0, max(0.5, (s1 - s0) / (l1 - l0)))), seg)
        segs.append(seg)
    release = min(0.12, _duration(src) - anchors[-1][0])  # the breath after the last word, if the take has one
    if release > 0.02:
        seg = dest.with_name(f"{dest.stem}.seg{len(segs)}.wav")
        _ff("-ss", f"{anchors[-1][0]:.3f}", "-t", f"{release:.3f}", "-i", src, seg)
        segs.append(seg)
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.name}'\n" for p in segs), encoding="utf-8")
    _ff("-f", "concat", "-safe", 0, "-i", lst, "-af", f"adelay={int(anchors[0][1] * 1000)}", dest)
    for p in [*segs, lst]:
        p.unlink()


def _copy_place(k: int) -> tuple[float, float, int]:
    """Pan (-1..1), gain and delay (ms) of copy k (1-based) from where its jar stands."""
    x, y = COPY_SPOTS[(k - 1) % len(COPY_SPOTS)]
    dx, dy = x - COPY_EAR[0], y - COPY_EAR[1]
    dist = math.hypot(dx, dy)
    pan = max(-1.0, min(1.0, math.atan2(dx, dy) / 0.45))
    return pan, min(0.85, 0.85 * 4.0 / dist), COPY_JITTER_MS[(k - 1) % len(COPY_JITTER_MS)]


def _treat(dry: Path, beat: Beat) -> Path:
    """The dry lead with its chorus / mini treatment (beat_XX.treated.wav), or the dry file itself if none applies."""
    d = beat.delivery
    if not d or (d.chorus <= 1 and not d.mini):
        return dry
    work = dry.with_name(dry.name.replace(".dry.mp3", ".lead.wav"))
    _ff("-i", dry, "-ar", 48000, "-ac", 1, work)
    treated = dry.with_name(dry.name.replace(".dry.mp3", ".treated.wav"))
    if d.mini:
        # rubberband keeps the formants: Claude, small (a plain pitch shift turns him into a cartoon squirrel).
        subprocess.run([system.require_tool("rubberband", "RUBBERBAND_BIN"), "-q", "-p", str(MINI_SEMITONES), "-F", "-3", str(work), str(treated)], check=True, capture_output=True)
        return treated
    copies = [c for k in range(1, d.chorus) if (c := dry.with_name(dry.name.replace(".dry.mp3", f".copy{k}.wav"))).exists()]
    if not copies:
        return dry
    lead_words = [{"text": w, "start": t0, "end": t1} for w, t0, t1 in whisper_words(work)]
    ins, chains = ["-i", str(work)], ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo[p0]"]
    for k, src in enumerate(copies, start=1):
        aligned = src.with_name(src.stem + ".aligned.wav")
        _align(src, json.loads(src.with_suffix(".json").read_text(encoding="utf-8")), work, lead_words, aligned)
        pan, gain, ms = _copy_place(k)
        left, right = gain * min(1, 1 - pan), gain * min(1, 1 + pan)
        far = "lowpass=f=6500," if gain < 0.7 else ""
        ins += ["-i", str(aligned)]
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,{far}adelay={ms}|{ms},"
                      f"pan=stereo|c0={left:.2f}*c0|c1={right:.2f}*c1[p{k}]")
    n = len(copies) + 1
    graph = ";".join(chains) + ";" + "".join(f"[p{k}]" for k in range(n)) + \
        f"amix=inputs={n}:normalize=0,volume={(1 + 0.45 * (n - 1)) ** -0.5:.3f},alimiter=limit=0.9[o]"
    subprocess.run([system.ffmpeg(), "-y", "-loglevel", "error", *ins, "-filter_complex", graph, "-map", "[o]", str(treated)], check=True)
    return treated


def apply_spaces(episode: Episode) -> None:
    """Rewrite every beat_XX.mp3 from its dry copy with the acoustics of where it is said (free, repeatable).

    The space follows `beat.ambience` (noche / ruinas), the speaker's `space` map in character.json and, for the
    novato, `beat.novato_away` (his lines come from the bathroom).
    The chorus / mini treatment (delivery.chorus / mini, see _treat) goes on before the room.
    """
    out = episode_dir(episode.slug) / "audio"
    ambience, away = "noche", False
    for b in episode.beats:
        if b.ambience:
            ambience = b.ambience
        if b.novato_away is not None:
            away = b.novato_away
        if not b.line:
            continue
        dry = out / f"beat_{b.id:02d}.dry.mp3"
        if not dry.exists():
            continue
        src = _treat(dry, b)
        name = {**DEFAULT_SPACE, **character(b.speaker.value).get("space", {})}.get(ambience, "room")
        if away and b.speaker.value == cast.HUMAN:
            name = "bano"
        sp = SPACES[name]
        ir = ROOT / "assets" / "sfx" / sp["ir"]
        far = sp.get("far", "anull")
        pre = f"adelay={sp['predelay']}|{sp['predelay']}," if sp.get("predelay") else ""
        graph = (
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,{far},apad=pad_dur={TAIL_PAD[name]},asplit=2[d][w];"
            f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo[ir];"
            f"[w]{pre}anull[wp];[wp][ir]afir=dry=1:wet=1:irnorm=2[wet];"  # dry/wet are input/output gains; L2 norm keeps the wet near the dry level
            f"[wet]volume={sp['wet'] * 2.5}[wv];[d]volume={1 - sp['wet'] * 0.5}[dv];"
            f"[dv][wv]amix=inputs=2:normalize=0,asetnsamples=n=1152:p=1[out]"  # even frames: lame chokes on ragged ones
        )
        subprocess.run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-i", str(ir), "-filter_complex", graph, "-map", "[out]",
             "-c:a", "libmp3lame", "-q:a", "2", str(out / f"beat_{b.id:02d}.mp3")],
            check=True,
        )
    console.print("  acústica aplicada")


# --- picking takes by ear ---------------------------------------------------------

TAKE_SEED = 6000


def voice_takes(episode: Episode, beat_id: int, n: int = 3) -> Path:
    """Generate n solo takes of one line into episodes/<slug>/picks/ with a page to listen to them."""
    spoken = [b for b in episode.beats if b.line]
    beat = next(b for b in spoken if b.id == beat_id)
    picks = episode_dir(episode.slug) / "picks"
    picks.mkdir(exist_ok=True)
    free = beat.model_copy(deep=True)
    free.delivery.seed = None
    rows = []
    with httpx.Client(timeout=180) as client:
        for k in range(n):
            mp3, _, hit = line_take(client, free, seed=TAKE_SEED + k, spoken=spoken)
            shutil.copy(mp3, picks / f"b{beat_id}_t{k + 1}.mp3")
            rows.append(f'<div class="r"><span>Toma {k + 1}</span><audio controls src="b{beat_id}_t{k + 1}.mp3"></audio></div>')
    page = picks / f"b{beat_id}.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><title>Tomas</title><style>body{font-family:system-ui;background:#14121a;color:#eee;'
        'max-width:760px;margin:40px auto;padding:0 16px}.r{display:flex;align-items:center;gap:12px;margin:8px 0}.r span{width:90px}</style>'
        f"<h1>Beat {beat_id} · «{beat.line}»</h1>" + "".join(rows)
    , encoding="utf-8")
    return page


def voice_pick(episode: Episode, beat_id: int, take: int | None = None, seed: int | None = None) -> None:
    """Fix a take (by its number from voice_takes, or a raw seed) in script.json and put it in the audio."""
    seed = seed if seed is not None else TAKE_SEED + take - 1
    path = episode_dir(episode.slug) / "script.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    for b in raw["beats"]:
        if b["id"] == beat_id:
            b["delivery"]["seed"] = seed
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    episode = Episode.model_validate(raw)
    beat = next(b for b in episode.beats if b.id == beat_id)
    out = episode_dir(episode.slug) / "audio"
    with httpx.Client(timeout=180) as client:
        mp3, _, _ = line_take(client, beat, seed=seed, spoken=[b for b in episode.beats if b.line])
    span = locate_lines(mp3, [beat.line])[0]
    old = out / f"beat_{beat_id:02d}.json"
    span["gap_before"] = json.loads(old.read_text(encoding="utf-8")).get("gap_before", 0.0) if old.exists() else 0.0
    info = _write_beat(mp3, span, beat, out)
    apply_spaces(episode)
    console.print(f"  beat {beat_id:>2} [cyan]elegida[/] (semilla {seed}) «{beat.line}» → «{info['heard']}»")
