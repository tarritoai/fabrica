"""Build, render and compose stages (Remotion + Blender + ffmpeg orchestration)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

from reels import cast
from reels import music as music_lib
from reels import system
from reels import score as score_mod
from reels import timeline as timeline_mod
from reels.assets import ROOT, character, episode_dir, published, style
from reels.schema import LAPTOP_COMPONENTS, PHONE_COMPONENTS, Episode

REMOTION = ROOT / "remotion"
console = Console()


def blender_bin() -> str:
    return system.blender()


def remotion(*args: str) -> list[str]:
    """Remotion CLI command (node + the local @remotion/cli, never a bare `npx`, see reels/system.py)."""
    return [*system.remotion_cmd(REMOTION), *args]


def _run(cmd: list[str], cwd: Path | None = None, log: Path | None = None) -> None:
    t0 = time.time()
    if log:
        with log.open("w", encoding="utf-8") as fh:
            result = subprocess.run(cmd, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT)
    else:
        result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        hint = f" (log: {log})" if log else ""
        raise RuntimeError(f"falló: {' '.join(cmd[:3])}…{hint}")
    console.print(f"[dim]  {Path(cmd[0]).name} {cmd[1] if len(cmd) > 1 else ''} … {time.time() - t0:.1f}s[/]")


def render_screens(tl: dict, out: Path) -> None:
    """Every screen event becomes an MP4 that Blender maps onto an in-world screen (phone or laptop)."""
    screens = out / "screens"
    screens.mkdir(exist_ok=True)
    for b in tl["beats"]:
        ev = b["event"]
        # Overlays (CounterReveal) are drawn by the Final composition, not mapped into the 3D world.
        if not ev or ev["component"] not in PHONE_COMPONENTS | LAPTOP_COMPONENTS:
            continue
        dest = screens / f"beat_{b['id']:02d}_{ev['component']}.mp4"
        props = {**ev["props"], "duration": (b["end_frame"] - b["start_frame"]) / tl["fps"]}
        props_file = screens / f"beat_{b['id']:02d}.props.json"
        code = REMOTION / "src/screens" / f"{ev['component']}.tsx"
        fresh = dest.exists() and (not code.exists() or dest.stat().st_mtime > code.stat().st_mtime)
        if fresh and props_file.exists() and json.loads(props_file.read_text(encoding="utf-8")) == props:
            continue
        props_file.write_text(json.dumps(props), encoding="utf-8")
        _run(
            remotion("render", "src/index.ts", ev["component"], str(dest), f"--props={props_file}", "--log=error"),
            cwd=REMOTION,
        )


def build(episode: Episode) -> Path:
    out = episode_dir(episode.slug)
    tl = timeline_mod.save(episode)
    console.print(f"  timeline: {tl['duration']:.1f}s, {tl['total_frames']} fotogramas")
    render_screens(tl, out)
    blend = out / "scene.blend"
    # A rebuilt scene invalidates every rendered frame (render resumes by skipping existing files).
    for old in [*(out / "renders").glob("frames_*"), *(out / "renders").glob("keyframes_*")]:
        shutil.rmtree(old)
    _run(
        [blender_bin(), "--python-exit-code", "1", "-b", "--factory-startup", "-P", str(ROOT / "blender/build_scene.py"), "--", str(out / "timeline.json"), str(blend)],
        log=out / "build.log",
    )
    return blend


def render(slug: str, quality: str = "final", keyframes: bool = False) -> Path:
    out = episode_dir(slug)
    frames_dir = out / "renders" / (f"keyframes_{quality}" if keyframes else f"frames_{quality}")
    # Resuming only makes sense for frames of *this* scene: drop any frame older than scene.blend.
    if frames_dir.exists():
        built = (out / "scene.blend").stat().st_mtime
        stale = [f for f in frames_dir.glob("*.png") if f.stat().st_mtime < built]
        for f in stale:
            f.unlink()
        if stale:
            console.print(f"[dim]  {len(stale)} fotogramas de una escena anterior descartados[/]")
    with system.keep_awake():
        _run(
            [blender_bin(), "--python-exit-code", "1", "-b", str(out / "scene.blend"), "-P", str(ROOT / "blender/render.py"), "--",
             str(frames_dir), quality, "keyframes" if keyframes else "full"],
            log=out / f"render_{quality}.log",
        )
    if keyframes:
        return frames_dir
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    video = out / "renders" / "scene.mp4"
    _run(
        [system.ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(tl["fps"]), "-start_number", "0",
         "-i", str(frames_dir / "%04d.png"), "-vf", f"scale={tl['width']}:{tl['height']}:flags=lanczos",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(video)]
    )
    # Uncompressed frames are ~6 MB each; once encoded they are no longer needed.
    shutil.rmtree(frames_dir)
    return video


VOICE_TARGET_DB = -19.0  # mean volume each line is pulled towards
VOICE_LEVEL_STRENGTH = 0.7  # 1 = all lines equal, 0 = untouched


def _line_gain(clip: Path, speaker: str | None) -> float:
    """Gain that pulls a line towards the common level, plus the speaker's own offset (character.json `level_db`:
    e.g. voices that come from far away stay quieter under the dialogue)."""
    gain_db = max(-8.0, min(8.0, VOICE_LEVEL_STRENGTH * (VOICE_TARGET_DB - _mean_volume(clip))))
    if speaker:
        gain_db += character(speaker).get("level_db", 0.0)
    return round(10 ** (gain_db / 20), 3)


def _mean_volume(path: Path) -> float:
    out = subprocess.run([system.ffmpeg(), "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"mean_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else VOICE_TARGET_DB


def _score_music(slug: str, tl: dict) -> dict | None:
    """Musical episode: its own mix (rendered fresh from the score, a few seconds), played as is from frame 0."""
    if not tl.get("score"):
        return None
    episode = Episode.model_validate_json((episode_dir(slug) / "script.json").read_text(encoding="utf-8"))
    wav = score_mod.render(episode)
    return {"file": str(wav.relative_to(episode_dir(slug))), "score": True, "swell_at_beat": None}


def compose(slug: str) -> Path:
    out = episode_dir(slug)
    return _compose(slug, "renders/scene.mp4", out / "final.mp4")


def _compose(slug: str, video_rel: str, final: Path) -> Path:
    """Remotion composition (voices, music, subtitles, SFX) over `video_rel`, then loudness normalisation."""
    out = episode_dir(slug)
    sfx_dir = out / "sfx"
    sfx_dir.mkdir(exist_ok=True)
    for wav in (ROOT / "assets/sfx").glob("*.wav"):
        shutil.copy(wav, sfx_dir / wav.name)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    music = _score_music(slug, tl)
    if tl.get("music"):
        track = music_lib.choose(tl["music"]["mood"], slug, tl["music"].get("track"))
        if track:
            (out / "music").mkdir(exist_ok=True)
            shutil.copy(ROOT / "assets/music" / track["file"], out / "music" / Path(track["file"]).name)
            music = {"file": f"music/{Path(track['file']).name}", "swell_at_beat": tl["music"].get("swell_at_beat"),
                     "cut_at_beat": tl["music"].get("cut_at_beat"), "start_at_beat": tl["music"].get("start_at_beat"),
                     "start_delay": tl["music"].get("start_delay", 0.0), "restart": tl["music"].get("restart", False),
                     "duck": tl["music"].get("duck"), "duck_db": tl["music"].get("duck_db", -3.0), "cut_fade": tl["music"].get("cut_fade"),
                     "resume_at_beat": tl["music"].get("resume_at_beat"), "fade_in": tl["music"].get("fade_in", 1.5),
                     "align_end": tl["music"].get("align_end", False), "duration": track.get("duration"),
                     "swell_level": tl["music"].get("swell_level", 0.6)}
            if "no publicar" in track["license"].lower():
                console.print(f"[yellow]  ⚠ música con licencia sin verificar ({track['source']}): no publicar este vídeo[/]")
            credits = out / "creditos.txt"
            if track.get("attribution"):
                # Licences that require credit: this text goes in the post description.
                credits.write_text("Música:\n" + track["attribution"] + "\n", encoding="utf-8")
                console.print(f"  ♪ crédito obligatorio en la descripción → {credits.relative_to(ROOT)}")
            elif credits.exists():
                credits.unlink()
        else:
            console.print("[yellow]  sin pistas de música en assets/music/music.json[/]")
    # Even out the lines: pull each clip most of the way to a common level (whispers stay a bit quieter).
    cast.activate(tl.get("cast") or {})
    for b in tl["beats"]:
        if b.get("audio"):
            b["audio"]["gain"] = _line_gain(out / b["audio"]["file"], b.get("speaker"))
    props = out / "compose.props.json"
    props.write_text(json.dumps({"timeline": tl, "video": video_rel, "music": music}, ensure_ascii=False), encoding="utf-8")
    raw = out / "renders" / "composed.mp4"
    _run(
        remotion("render", "src/index.ts", "Final", str(raw), f"--props={props}",
                 f"--public-dir={out}", "--log=error", "--crf=15"),
        cwd=REMOTION,
    )
    # Slight global speed-up (reels pacing; keeps pitch and sync), then ~-14 LUFS as Reels/TikTok/Shorts play.
    # Two-pass *linear* loudnorm: one gain for the whole video, so silences don't "breathe" noise.
    speed = style().get("playback_speed", 1.0)
    video = ["-c:v", "copy"] if speed == 1.0 else ["-vf", f"setpts=PTS/{speed}", "-r", str(tl["fps"]), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p"]
    tempo = f"atempo={speed}," if speed != 1.0 else ""
    probe = subprocess.run(
        [system.ffmpeg(), "-hide_banner", "-i", str(raw), "-af", f"{tempo}loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stderr
    try:
        m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    except ValueError:
        raise RuntimeError(f"ffmpeg no ha podido medir el volumen de {raw.name}: {system.tail(probe) or 'sin mensaje'}")
    norm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    _run(
        [system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw), "-af", f"{tempo}{norm}",
         "-ar", "48000", *video, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)]
    )
    return final


def rebuild_if_outdated(slug: str) -> None:
    """Rebuild scene.blend before any render if the script, voices or code changed since it was built."""
    out = episode_dir(slug)
    if _scene_outdated(out):
        console.print("[dim]  la escena está desactualizada (guion, voces o código): la reconstruyo[/]")
        build(Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8")))


def _scene_outdated(out: Path) -> bool:
    """The scene must be rebuilt when the script, the voices, the Blender code or a character changed after it was built."""
    blend = out / "scene.blend"
    if not blend.exists():
        return True
    built = blend.stat().st_mtime
    sources = [out / "script.json", *(out / "audio").glob("beat_*.json"), *(ROOT / "blender").rglob("*.py"),
               *(ROOT / "assets/characters").glob("*/character.json"), *(ROOT / "personajes").glob("*/personaje.json"),
               ROOT / "reels/timeline.py",
               *(REMOTION / "src/screens").glob("*.tsx")]
    return any(f.stat().st_mtime > built for f in sources if f.exists()) or not (out / "screens").exists()


def preview(slug: str, first_beat: int, last_beat: int, quality: str = "preview") -> Path:
    """Render and compose only some beats (with music and subtitles) for quick iteration.

    Frames go to the same resumable folder as a full render, so they are reused later.
    """
    out = episode_dir(slug)
    if _scene_outdated(out):
        console.print("[dim]  la escena está desactualizada (guion, voces o código): la reconstruyo[/]")
        build(Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8")))
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    # Ids are not always in screen order (beats get inserted later): the range runs from beat `first` to beat `last`
    # as they play.
    ids = [b["id"] for b in tl["beats"]]
    if first_beat not in ids or last_beat not in ids or ids.index(first_beat) > ids.index(last_beat):
        raise ValueError(f"no hay beats entre {first_beat} y {last_beat} (orden en pantalla: {ids})")
    beats = tl["beats"][ids.index(first_beat): ids.index(last_beat) + 1]
    start, end = beats[0]["start_frame"], beats[-1]["end_frame"]  # end is exclusive
    frames_dir = out / "renders" / f"frames_{quality}"
    if frames_dir.exists():
        built = (out / "scene.blend").stat().st_mtime
        for f in frames_dir.glob("*.png"):
            if f.stat().st_mtime < built:
                f.unlink()
    with system.keep_awake("reels preview"):
        _run(
            [blender_bin(), "--python-exit-code", "1", "-b", str(out / "scene.blend"), "-P", str(ROOT / "blender/render.py"), "--",
             str(frames_dir), quality, "range", str(start), str(end - 1)],
            log=out / f"render_{quality}.log",
        )
    part = out / "renders" / "scene_part.mp4"
    _run(
        [system.ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(tl["fps"]), "-start_number", str(start),
         "-i", str(frames_dir / "%04d.png"), "-frames:v", str(end - start),
         "-vf", f"scale={tl['width']}:{tl['height']}:flags=lanczos", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(part)]
    )
    sfx_dir = out / "sfx"
    sfx_dir.mkdir(exist_ok=True)
    for wav in (ROOT / "assets/sfx").glob("*.wav"):
        shutil.copy(wav, sfx_dir / wav.name)
    music = _score_music(slug, tl)
    if tl.get("music"):
        track = music_lib.choose(tl["music"]["mood"], slug, tl["music"].get("track"))
        if track:
            (out / "music").mkdir(exist_ok=True)
            shutil.copy(ROOT / "assets/music" / track["file"], out / "music" / Path(track["file"]).name)
            music = {"file": f"music/{Path(track['file']).name}", "swell_at_beat": tl["music"].get("swell_at_beat"),
                     "cut_at_beat": tl["music"].get("cut_at_beat"), "start_at_beat": tl["music"].get("start_at_beat"),
                     "start_delay": tl["music"].get("start_delay", 0.0), "restart": tl["music"].get("restart", False),
                     "duck": tl["music"].get("duck"), "duck_db": tl["music"].get("duck_db", -3.0), "cut_fade": tl["music"].get("cut_fade"),
                     "resume_at_beat": tl["music"].get("resume_at_beat"), "fade_in": tl["music"].get("fade_in", 1.5),
                     "align_end": tl["music"].get("align_end", False), "duration": track.get("duration"),
                     "swell_level": tl["music"].get("swell_level", 0.6)}
    cast.activate(tl.get("cast") or {})
    for b in tl["beats"]:
        if b.get("audio"):
            b["audio"]["gain"] = _line_gain(out / b["audio"]["file"], b.get("speaker"))
    props = out / "preview.props.json"
    props.write_text(json.dumps({"timeline": tl, "video": "renders/scene_part.mp4", "videoOffset": start, "music": music}, ensure_ascii=False), encoding="utf-8")
    result = out / f"preview_{first_beat}-{last_beat}.mp4"
    _run(
        remotion("render", "src/index.ts", "Final", str(result), f"--props={props}", f"--frames={start}-{end - 1}",
                 f"--public-dir={out}", "--log=error", "--crf=20"),
        cwd=REMOTION,
    )
    return result


def animatic(slug: str, audio_only: bool = False) -> Path:
    """Cheap review before animating: the real mix (voices, music, subtitles) over one still per beat.

    audio_only skips Blender entirely (black frames), to judge the voices before any visual work.
    """
    out = episode_dir(slug)
    episode = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    renders = out / "renders"
    renders.mkdir(exist_ok=True)
    video = renders / ("animatic_black.mp4" if audio_only else "animatic_stills.mp4")
    if audio_only:
        tl = timeline_mod.save(episode)
        _run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             f"color=c=black:s={tl['width']}x{tl['height']}:r={tl['fps']}:d={tl['duration'] + 0.5}",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(video)]
        )
        result = out / "animatic_audio.mp4"
    else:
        if _scene_outdated(out):
            build(episode)
        tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
        # One still per beat, a bit past its middle (memories and screens have had time to appear).
        mids = {b["id"]: b["start_frame"] + int((b["end_frame"] - b["start_frame"]) * 0.6) for b in tl["beats"]}
        stills = renders / "stills_animatic"
        if stills.exists():
            built = (out / "scene.blend").stat().st_mtime
            for f in stills.glob("*.png"):
                if f.stat().st_mtime < built:
                    f.unlink()
        with system.keep_awake("reels animatic"):
            _run(
                [blender_bin(), "--python-exit-code", "1", "-b", str(out / "scene.blend"), "-P", str(ROOT / "blender/render.py"), "--",
                 str(stills), "preview", "frames", ",".join(str(f) for f in mids.values())],
                log=out / "render_animatic.log",
            )
        lines = []
        for b in tl["beats"]:
            still = (stills / f"kf_{mids[b['id']]:04d}.png").as_posix().replace("'", "'\\''")
            lines += [f"file '{still}'", f"duration {(b['end_frame'] - b['start_frame']) / tl['fps']:.4f}"]
        lines.append(lines[-2])  # concat demuxer quirk: the last file must be repeated
        concat = renders / "animatic.txt"
        concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _run(
            [system.ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-vf", f"scale={tl['width']}:{tl['height']}:flags=lanczos,fps={tl['fps']}",
             "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(video)]
        )
        result = out / "animatic.mp4"
    return _compose(slug, str(video.relative_to(out)), result)


def cover(slug: str, beat_id: int, title: str | None = None, mark: str | None = None, at: float = 0.5) -> Path:
    """Profile-grid cover: a full-quality still of one beat (at `at` of its length) with the title -> publicar/."""
    out = episode_dir(slug)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    beat = next(b for b in tl["beats"] if b["id"] == beat_id)
    frame = beat["start_frame"] + round((beat["end_frame"] - beat["start_frame"]) * at)
    still = out / "cover_still.png"
    _run([blender_bin(), "--python-exit-code", "1", "-b", str(out / "scene.blend"), "-P", str(ROOT / "blender/still.py"), "--",
          str(still), str(frame), "64"], log=out / "cover.log")
    series = tl.get("series") or {}
    if mark is None and series.get("of"):
        mark = f"{series['part']}/{series['of']}"
    handle = json.loads((ROOT / "assets/brand/brand.json").read_text(encoding="utf-8")).get("handle", "").lstrip("@")
    props = {"image": still.name, "title": title or tl.get("title") or slug, "mark": mark, "handle": f"@{handle}" if handle else ""}
    dest = published(slug, "_portada.png")
    dest.parent.mkdir(exist_ok=True)
    # Props go in a file, never inline: on Windows a JSON argument would be mangled by quoting rules.
    props_file = out / "cover.props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    _run(remotion("still", "src/index.ts", "Cover", str(dest), f"--props={props_file}", f"--public-dir={out}", "--log=error"),
         cwd=REMOTION)
    return dest
