"""script.json + voice.json → timeline.json: everything in frames, ready for Remotion to draw.

- The takes are laid one after the other (pace.lead before the first word, pace.gap — or the beat's pause_before —
  between voices) and the reel lasts until the last word plus ending.seconds.
- A shot starts 3 frames before the first word of the beat that opens it (the cut lands just before the voice).
- Events hang from words: «at» is a word of the beat's line («molino», «molino#2»), «inicio» or «fin», plus «delay».
- Sounds: the cuts, stamps, counts and reveals get their sound unless auto_sfx is off; explicit sfx events too.
"""

from __future__ import annotations

import json
import shutil
import unicodedata
import re
from pathlib import Path

from reels.assets import ASSETS, SFX, episode_dir
from reels.schema import Episode, Event, Shot

FPS = 30
WIDTH, HEIGHT = 1080, 1920
VOICE_TARGET_DB = -19.0


class TimelineError(ValueError):
    pass


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zñ0-9]", "", s)


def f(seconds: float) -> int:
    return int(round(seconds * FPS))


def load_voice(slug: str) -> dict:
    path = episode_dir(slug) / "voice.json"
    if not path.exists():
        raise TimelineError(f"aún no hay voces para «{slug}»: primero `uv run reels voice {slug}` (cuesta) o el ejemplo")
    return json.loads(path.read_text(encoding="utf-8"))


CHARS_PER_SECOND = 15.0  # a «¿Y si…?» narrator after tightening: for the free sketch without voices


def estimated_voice(ep: Episode) -> dict:
    """A voice.json made up from the text (no audio, no cost): to look at the key frames BEFORE paying for voices.
    Times are approximate (~15 characters a second); the real ones come with `reels voice`."""
    from reels.voice import takes

    out = []
    for t in takes(ep):
        words, clock = [], 0.05
        for b in t.beats:
            for w in b.line.split():
                dur = max(0.18, len(w) / CHARS_PER_SECOND * 1.1 / ep.pace.tempo * 1.1)
                words.append({"text": w, "start": round(clock, 3), "end": round(clock + dur * 0.85, 3), "beat": b.id})
                clock += dur
                if w[-1:] in ".!?…:":
                    clock += ep.pace.max_pause
        out.append({"take": t.index, "file": None, "voice": t.voice, "beats": [b.id for b in t.beats], "words": words,
                    "duration": round(clock + 0.05, 3), "mean_db": VOICE_TARGET_DB})
    return {"model": "estimado", "takes": out, "credits": 0}


def place_words(ep: Episode, voice: dict) -> tuple[list[dict], list[dict]]:
    """Absolute word times and where each take starts in the reel."""
    by_beat = {b.id: b for b in ep.beats}
    words: list[dict] = []
    clips: list[dict] = []
    t = ep.pace.lead
    first = True
    for take in voice["takes"]:
        ws = take["words"]
        if not ws:
            continue
        lead = ws[0]["start"]
        if not first:
            b0 = by_beat.get(take["beats"][0])
            gap = b0.pause_before if b0 and b0.pause_before is not None else ep.pace.gap
            t += gap
        start = t - lead
        clips.append({"file": take["file"], "start": start, "voice": take["voice"], "mean_db": take.get("mean_db", VOICE_TARGET_DB)})
        for w in ws:
            words.append({"text": w["text"], "start": round(start + w["start"], 3), "end": round(start + w["end"], 3),
                          "beat": w["beat"], "voice": take["voice"]})
        t = start + ws[-1]["end"]
        first = False
    if not words:
        raise TimelineError("las voces no tienen palabras (¿voice.json vacío?): repite `reels voice`")
    return words, clips


def resolve_anchor(anchor: str, beat_words: list[dict], beat_id: int) -> float:
    if anchor == "inicio":
        return beat_words[0]["start"]
    if anchor == "fin":
        return beat_words[-1]["end"]
    word, _, nth = anchor.partition("#")
    n = int(nth) if nth else 1
    hits = [w for w in beat_words if norm(w["text"]) == norm(word)]
    if len(hits) < n:
        said = " ".join(w["text"] for w in beat_words)
        raise TimelineError(f"beat {beat_id}: no encuentro la palabra «{anchor}» en «{said}»")
    return hits[n - 1]["start"]


def shot_json(shot: Shot, index: int, start: int) -> dict:
    return {
        "index": index, "from": start, "to": start, "scene": shot.scene, "options": shot.options,
        "camera": {"zoom": shot.camera.zoom, "focus": list(shot.camera.focus), "punch": shot.camera.punch, "pan": list(shot.camera.pan)},
        "actors": [{"id": a.id, "piece": a.piece, "x": a.x, "y": a.y, "scale": a.scale, "rot": a.rot, "props": a.props, "voice": a.voice,
                    "z": a.z, "flip": a.flip, "hidden": a.hidden, "shadow": a.shadow} for a in shot.actors],
    }


def event_json(ev: Event, frame: int, shot: int, beat: int | None) -> dict:
    data = ev.model_dump(by_alias=True, exclude_none=True, exclude={"at", "delay", "until", "sound", "volume"})
    data.update({"frame": frame, "shot": shot, "beat": beat})
    return data


SOUNDS = {"cut": ("papel", 0.55), "stamp": ("sello", 0.85), "count": ("ding", 0.35), "reveal": ("destello", 0.45),
          "enter": ("pop", 0.3), "exit": ("papel", 0.35), "count_break": ("boom", 0.4), "question": ("toc", 0.5),
          "sparkle": ("destello", 0.4), "shake": ("boom", 0.3)}


def build(ep: Episode, estimated: bool = False) -> dict:
    voice = estimated_voice(ep) if estimated else load_voice(ep.slug)
    words, clips = place_words(ep, voice)
    wb: dict[int, list[dict]] = {}
    for w in words:
        wb.setdefault(w["beat"], []).append(w)
    missing = [b.id for b in ep.beats if b.id not in wb]
    if missing:
        raise TimelineError(f"los beats {missing} no tienen voz: repite `uv run reels voice {ep.slug}`")
    last_word = max(w["end"] for w in words)
    ending_start = last_word + 0.12
    frames = f(last_word + ep.ending.seconds)

    shots: list[dict] = []
    events: list[dict] = []
    sfx: list[dict] = []
    beats_out: list[dict] = []
    for i, b in enumerate(ep.beats):
        bw = wb[b.id]
        if b.shot is not None:
            # the cut lands 3 frames before the first word, but never before the previous line has finished
            prev_end = f(wb[ep.beats[i - 1].id][-1]["end"]) + 1 if i else 0
            start = 0 if not shots else max(shots[-1]["from"] + 1, min(f(bw[0]["start"]), max(prev_end, f(bw[0]["start"]) - 3)))
            shots.append(shot_json(b.shot, len(shots), start))
            if len(shots) > 1 and ep.auto_sfx:
                sfx.append({"sound": "cut", "frame": start - 4})
        shot_i = len(shots) - 1
        next_start = wb[ep.beats[i + 1].id][0]["start"] if i + 1 < len(ep.beats) else None
        for ev in b.events:
            base = resolve_anchor(ev.at, bw, b.id)
            frame = max(0, f(base + ev.delay))
            data = event_json(ev, frame, shot_i, b.id)
            if ev.until:
                data["until_spec"] = ev.until
                if ev.until not in ("plano", "beat", "final"):
                    data["until"] = f(resolve_anchor(ev.until, bw, b.id))
                elif ev.until == "beat":
                    data["until"] = f((next_start if next_start is not None else bw[-1]["end"] + 0.5) - 0.05)
                elif ev.until == "final":
                    data["until"] = frames
            events.append(data)
            if ev.type == "sfx":
                sfx.append({"file": ev.sound, "frame": frame, "volume": ev.volume if ev.volume is not None else 0.6})
            elif ep.auto_sfx and ev.type in SOUNDS:
                sfx.append({"sound": ev.type, "frame": frame + (4 if ev.type == "stamp" else -6 if ev.type == "reveal" else 0)})
        beats_out.append({
            "id": b.id, "voice": b.voice, "line": b.line, "start": bw[0]["start"], "end": bw[-1]["end"],
            "from": f(bw[0]["start"]), "to": f(bw[-1]["end"]), "highlight": b.highlight, "captions": b.captions,
            "bubble": b.bubble.model_dump() if b.bubble else None,
        })

    ending_frame = f(ending_start)
    if ep.ending.shot is not None:
        shots.append(shot_json(ep.ending.shot, len(shots), ending_frame))
        if ep.auto_sfx:
            sfx.append({"sound": "cut", "frame": ending_frame - 4})
    for ev in ep.ending.events:
        frame = ending_frame + f(ev.delay)
        data = event_json(ev, frame, len(shots) - 1, None)
        if ev.until == "final" or ev.until is None:
            data["until"] = frames
        events.append(data)
        if ev.type == "sfx":
            sfx.append({"file": ev.sound, "frame": frame, "volume": ev.volume if ev.volume is not None else 0.6})
        elif ep.auto_sfx and ev.type in SOUNDS:
            sfx.append({"sound": ev.type, "frame": frame + (4 if ev.type == "stamp" else 0)})
    if ep.ending.question:
        qf = ending_frame + f(ep.ending.question_delay)
        events.append({"type": "question", "text": ep.ending.question, "frame": qf, "shot": len(shots) - 1, "beat": None})
        if ep.auto_sfx:
            sfx.append({"sound": "question", "frame": qf})

    # shot ends; stamps and labels last until the end of their shot unless told otherwise
    for k, s in enumerate(shots):
        s["to"] = shots[k + 1]["from"] if k + 1 < len(shots) else frames
    for e in events:
        if e["type"] in ("stamp", "label") and "until" not in e:
            e["until"] = shots[e["shot"]]["to"] - 1
        e.pop("until_spec", None)

    title = None
    if ep.title_card:
        b1 = ep.beats[0]
        to = f(resolve_anchor(ep.title_card.until, wb[b1.id], b1.id)) if ep.title_card.until != "fin" else f(wb[b1.id][-1]["end"]) - 2
        title = {"lines": ep.title_card.lines, "highlight": ep.title_card.highlight, "from": 0, "to": to}
    tags_from = None
    if ep.tags_from_beat is not None:
        tb = next((b for b in ep.beats if b.id == ep.tags_from_beat), None)
        tags_from = f(wb[tb.id][0]["start"]) - 3 if tb else 0
    counter = None
    if ep.counter:
        cb = next((b for b in ep.beats if b.id == ep.counter.from_beat), ep.beats[0])
        counter = {"label": ep.counter.label, "kind": ep.counter.kind, "start": ep.counter.start, "max": ep.counter.max,
                   "from": max(0, f(wb[cb.id][0]["start"]) - 1), "suffix": ep.counter.suffix}

    audio_voices = [] if estimated else [{"file": c["file"], "frame": f(c["start"]),
                     "volume": round(10 ** (max(-8.0, min(8.0, 0.7 * (VOICE_TARGET_DB - c["mean_db"]))) / 20), 3)} for c in clips]
    audio_sfx = []
    for s in sfx:
        name, vol = (SOUNDS[s["sound"]] if "sound" in s else (s["file"], s["volume"]))
        audio_sfx.append({"file": f"sfx/{name}.wav", "frame": s["frame"], "volume": vol})
    music = None
    if ep.music:
        music = {"file": f"musica/{Path(ep.music.track).name}", "volume": ep.music.volume, "from": 0, "fade_out": 24,
                 "loop": ep.music.loop}

    return {
        "slug": ep.slug, "title": ep.title, "series": ep.series, "work": ep.work, "palette": ep.palette, "fps": FPS,
        "width": WIDTH, "height": HEIGHT, "frames": frames, "words": words, "beats": beats_out, "shots": shots,
        "events": sorted(events, key=lambda e: e["frame"]), "counter": counter, "title_card": title, "tags_from": tags_from,
        "audio": {"voices": audio_voices, "music": music, "sfx": audio_sfx}, "ending_from": ending_frame,
        "captions": {"y": ep.captions_y, "size": ep.captions_size}, "estimated": estimated,
    }


def stage_assets(ep: Episode, tl: dict) -> None:
    """Copy what the render needs next to the voices (episodes/<slug>/publico/): sound effects and music."""
    pub = episode_dir(ep.slug) / "publico"
    (pub / "sfx").mkdir(parents=True, exist_ok=True)
    for s in tl["audio"]["sfx"]:
        src = SFX / Path(s["file"]).name
        if not src.exists():
            raise TimelineError(f"no existe el efecto {src.name} en assets/sfx/ (los que hay: {', '.join(sorted(p.stem for p in SFX.glob('*.wav')))})")
        shutil.copy(src, pub / "sfx" / src.name)
    if ep.music:
        src = ASSETS / "music" / ep.music.track
        if not src.exists():
            raise TimelineError(f"no existe la música {ep.music.track} en assets/music/ (mira assets/music/music.json)")
        (pub / "musica").mkdir(exist_ok=True)
        shutil.copy(src, pub / "musica" / src.name)


def save(ep: Episode, estimated: bool = False) -> dict:
    tl = build(ep, estimated)
    stage_assets(ep, tl)
    out = episode_dir(ep.slug)
    (out / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    return tl
