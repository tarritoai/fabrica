"""Beat timings from the generated audio (never from the LLM)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from reels import lipsync, score as score_mod
from reels.assets import character, episode_dir, style
from reels.schema import OFFSCREEN, Episode
from reels import system

MIN_LEAD_IN = 0.08  # never cut right on the first syllable
TURN_GAP = 0.3  # voice-to-voice silence between replies when the script asks for no pause
MAX_HOLD_BEFORE_LINE = 0.12  # a spoken beat followed by another line keeps talking; pauses go in pause_before


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        [system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8", errors="replace",
    )
    return float(out.stdout.strip())


def speech_edges(path: Path) -> tuple[float, float]:
    """(start, end) of the voiced part of a clip: its leading/trailing silence doesn't count as a pause."""
    out = subprocess.run(
        [system.ffmpeg(), "-i", str(path), "-af", "silencedetect=n=-40dB:d=0.04", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8", errors="replace",
    ).stderr
    dur = audio_duration(path)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    lead = ends[0] if starts and starts[0] < 0.01 and ends else 0.0
    tail_start = starts[-1] if starts and (len(ends) < len(starts) or ends[-1] >= dur - 0.02) else dur
    return lead, max(lead, tail_start)


def words_from_alignment(alignment: dict) -> list[dict]:
    words, current, start = [], "", None
    chars = alignment["characters"]
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if current:
                words.append({"text": current, "start": start, "end": prev_end})
            current, start = "", None
            continue
        if start is None:
            start = s
        current += ch
        prev_end = e
    if current:
        words.append({"text": current, "start": start, "end": prev_end})
    # Audio tags ("[sighs]") are directions, not words.
    return [w for w in words if not (w["text"].startswith("[") and w["text"].endswith("]"))]


def build(episode: Episode) -> dict:
    fps = style()["fps"]
    audio_dir = episode_dir(episode.slug) / "audio"

    speech = [(b, audio_dir / f"beat_{b.id:02d}.wav") for b in episode.beats if b.line]
    visemes = dict(zip([b.id for b, _ in speech], lipsync.cues_for_all([(w, b.line) for b, w in speech])))

    beats, t, prev_hold, away = [], 0.0, 0.0, False
    for i, b in enumerate(episode.beats):
        next_spoken = i + 1 < len(episode.beats) and episode.beats[i + 1].line is not None
        entry = b.model_dump(mode="json")
        if b.novato_away is not None:
            away = b.novato_away
        entry["away"] = away  # resolved: is the novato out of the room during this beat
        if episode.score:
            # Musical episode: the shot lasts its bars; the notes drive everything (score_mod.events).
            entry["audio"] = None
            length = b.bars * 4 * 60 / episode.score.bpm
            prev_hold = 0.0
        elif b.line:
            mp3 = audio_dir / f"beat_{b.id:02d}.mp3"
            dur = audio_duration(mp3)
            meta = json.loads(mp3.with_suffix(".json").read_text(encoding="utf-8"))
            # Turns follow each other tightly (measured voice to voice); only a deliberate pause_before leaves air.
            pause = b.delivery.pause_before if b.delivery else 0.0
            lead, voice_end = speech_edges(mp3)
            offset = max(0.0, MIN_LEAD_IN - lead, (pause or TURN_GAP) - lead - prev_hold)
            entry["audio"] = {
                "file": f"audio/beat_{b.id:02d}.mp3",
                "offset": offset,
                "duration": dur,
                "words": meta.get("words") or (words_from_alignment(meta["alignment"]) if "alignment" in meta else []),
                "visemes": visemes[b.id],
            }
            entry["subtitle_color"] = character(b.speaker.value)["subtitle_color"]
            if b.event and b.event.component == "MemorySave" and b.event.props.typed_count():
                # Read aloud while written: the typing spans the voice (and the line gets no subtitle).
                entry["event"]["props"]["type_start"] = offset + lead
                entry["event"]["props"]["type_speed"] = (voice_end - lead) / b.event.props.typed_count()
            hold = min(b.hold, MAX_HOLD_BEFORE_LINE) if next_spoken else b.hold
            # The clip's trailing silence plays over the next beat; the cut lands when the voice ends.
            length = offset + voice_end + hold
            prev_hold = hold
        else:
            entry["audio"] = None
            # Screen event, or a mute reaction that lasts its hold.
            length = (b.event.duration() if b.event else 0.0) + b.hold
            prev_hold = 0.0
        nv = audio_dir / f"nonverbal_{b.id:02d}.mp3"
        entry["nonverbal_audio"] = {"file": f"audio/{nv.name}", "offset": b.nonverbal_at} if b.nonverbal and nv.exists() else None
        entry["start_frame"] = round(t * fps)
        t += length
        entry["end_frame"] = round(t * fps)
        beats.append(entry)

    return {
        "slug": episode.slug,
        "title": episode.title,
        "tone": episode.tone,
        "hook": episode.hook,
        "series": episode.series.model_dump() if episode.series else None,
        "fps": fps,
        "width": style()["width"],
        "height": style()["height"],
        "characters": [c.value for c in episode.characters],
        # Who plays each role slot (reels/cast.py): Blender builds the player's body in the slot.
        "cast": episode.players(),
        "offscreen": [c.value for c in episode.characters if c in OFFSCREEN],
        "music": episode.music.model_dump(mode="json") if episode.music else None,
        "score": score_mod.events(episode.score) if episode.score else None,
        "set": episode.set.value,
        "set_options": episode.set_options,
        "ai_visits_laptop": any(b.ai_move == "laptop" for b in episode.beats),
        "total_frames": round(t * fps),
        "duration": t,
        "beats": beats,
    }


def save(episode: Episode) -> dict:
    tl = build(episode)
    (episode_dir(episode.slug) / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False), encoding="utf-8")
    return tl
