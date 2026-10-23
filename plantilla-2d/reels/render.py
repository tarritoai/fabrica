"""Drawing with Remotion: the reel (render), its key frames (stills), a cover, character sheets; then the sound at
-14 LUFS (two-pass linear loudnorm, like Reels/TikTok/Shorts play it).

Each episode gets its own Remotion entry (remotion/src/generado/<slug>.ts) that loads the generic pieces, your
characters (remotion/src/personajes/) and that episode's own pieces (remotion/src/episodios/<slug>/), so a broken
drawing in one episode never stops another. Remotion is called through node + its local CLI (never npx: on Windows
npx is a .cmd). Everything it needs is in episodes/<slug>/publico/ (voices, sound effects, music).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

from reels import system
from reels.assets import REMOTION, episode_dir

console = Console()
GENERATED = REMOTION / "src" / "generado"


class RenderError(RuntimeError):
    pass


def pieces_folder(slug: str) -> str | None:
    """The episode's own pieces: remotion/src/episodios/<slug>/ (a B hook «<slug>-b» uses those of «<slug>»)."""
    for s in (slug, slug.removesuffix("-b")):
        if (REMOTION / "src" / "episodios" / s / "index.tsx").exists() or (REMOTION / "src" / "episodios" / s / "index.ts").exists():
            return s
    return None


def entry(slug: str) -> str:
    GENERATED.mkdir(parents=True, exist_ok=True)
    folder = pieces_folder(slug)
    lines = ['// Written by `uv run reels …`: do not edit (it is rewritten on every render).',
             'import { registerRoot } from "remotion";', 'import { makeRoot } from "../kit/root";']
    if folder:
        lines += [f'import * as episode from "../episodios/{folder}";', "registerRoot(makeRoot(episode));"]
    else:
        lines += ["registerRoot(makeRoot());"]
    name = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    path = GENERATED / f"{name}.ts"
    text = "\n".join(lines) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return f"src/generado/{name}.ts"


def remotion(*args: str) -> list[str]:
    return [*system.remotion_cmd(REMOTION), *args]


def run(cmd: list[str], log: Path, what: str) -> float:
    t0 = time.time()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as fh:
        r = subprocess.run(cmd, cwd=REMOTION, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        text = log.read_text(encoding="utf-8", errors="replace")
        raise RenderError(f"{what} ha fallado: {system.tail(text, 8) or 'sin mensaje'} (registro completo: {log})")
    return time.time() - t0


def timeline(slug: str) -> dict:
    path = episode_dir(slug) / "timeline.json"
    if not path.exists():
        raise RenderError(f"falta {path}: primero `uv run reels build {slug}`")
    return json.loads(path.read_text(encoding="utf-8"))


def _props(slug: str, name: str, data: dict) -> Path:
    path = episode_dir(slug) / f"{name}.props.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def render_video(slug: str, draft: bool = False) -> Path:
    """The whole reel → episodes/<slug>/final.mp4 (draft: half size, quicker, as borrador.mp4)."""
    out = episode_dir(slug)
    tl = timeline(slug)
    if tl.get("estimated"):
        raise RenderError("estos tiempos son un boceto sin voces: el vídeo necesita las voces (`reels voice`)")
    props = _props(slug, "reel", {"timeline": tl})
    raw = out / ("borrador.raw.mp4" if draft else "final.raw.mp4")
    args = ["render", entry(slug), "Reel", str(raw), f"--props={props}", f"--public-dir={out / 'publico'}", "--log=error"]
    args += ["--scale=0.5", "--crf=24"] if draft else ["--crf=16"]
    with system.keep_awake("reels render"):
        secs = run(remotion(*args), out / "render.log", "el dibujo del vídeo (Remotion)")
    final = out / ("borrador.mp4" if draft else "final.mp4")
    loudness(raw, final)
    raw.unlink(missing_ok=True)
    console.print(f"[dim]  {tl['frames']} fotogramas en {secs:.0f} s[/]")
    return final


def loudness(raw: Path, final: Path) -> None:
    """Two-pass LINEAR loudnorm to -14 LUFS: one gain for the whole reel, so silences never «breathe» noise."""
    probe = subprocess.run([system.ffmpeg(), "-hide_banner", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    try:
        m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    except ValueError:
        raise RenderError(f"ffmpeg no ha podido medir el volumen de {raw.name}: {system.tail(probe) or 'sin mensaje'}")
    norm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw), "-af", norm, "-ar", "48000", "-c:v", "copy",
                     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)], "ffmpeg (volumen)")


def key_frames(tl: dict) -> list[tuple[int, str]]:
    """Frame 0, the start of each shot (+10), the end of each beat (what its events left on screen) and the ending."""
    picks: dict[int, str] = {0: "f0"}
    for s in tl["shots"]:
        picks.setdefault(min(tl["frames"] - 1, s["from"] + 10), f"plano{s['index'] + 1}")
    for b in tl["beats"]:
        # the end of the beat, but inside its own shot (a cut may come right after its last word)
        shot = next((s for s in tl["shots"] if s["from"] <= b["from"] < s["to"]), None)
        last = shot["to"] - 1 if shot else tl["frames"] - 1
        picks.setdefault(max(0, min(tl["frames"] - 1, b["to"] - 2, last)), f"beat{b['id']}")
    picks.setdefault(max(0, (tl["ending_from"] + tl["frames"]) // 2), "remate")
    picks.setdefault(tl["frames"] - 1, "ultimo")
    return sorted(picks.items())


def stills(slug: str, frames: list[int] | None = None, folder_name: str = "fotogramas") -> tuple[Path, list[Path]]:
    """Key frames as images (episodes/<slug>/fotogramas/) + a contact sheet hoja.jpg, in one Remotion run."""
    out = episode_dir(slug)
    tl = timeline(slug)
    picks = [(fr, f"f{fr}") for fr in frames] if frames else key_frames(tl)
    folder = out / folder_name
    if folder.exists():
        shutil.rmtree(folder)
    tmp = out / f"{folder_name}_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    props = _props(slug, "fotogramas", {"timeline": tl, "frames": [fr for fr, _ in picks]})
    run(remotion("render", entry(slug), "Fotogramas", str(tmp), f"--props={props}", f"--public-dir={out / 'publico'}",
                 "--sequence", "--image-format=jpeg", "--jpeg-quality=88", "--log=error"),
        out / "fotogramas.log", "los fotogramas clave (Remotion)")
    images = sorted(tmp.glob("*.jp*g"), key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    if len(images) != len(picks):
        raise RenderError(f"Remotion ha hecho {len(images)} fotogramas de {len(picks)}")
    folder.mkdir()
    result = []
    for (fr, name), img in zip(picks, images):
        dest = folder / f"{fr:04d}_{name}.jpg"
        shutil.move(str(img), dest)
        result.append(dest)
    shutil.rmtree(tmp, ignore_errors=True)
    sheet = folder / "hoja.jpg"
    contact_sheet(result, sheet, [f"{fr / tl['fps']:.1f}s {name}" for fr, name in picks])
    return sheet, result


def contact_sheet(images: list[Path], dest: Path, labels: list[str] | None = None, cols: int = 5, width: int = 324) -> None:
    """Images side by side (left to right, top to bottom), each scaled to `width`."""
    rows = (len(images) + cols - 1) // cols
    ins: list[str] = []
    for img in images:
        ins += ["-i", str(img)]
    chains = []
    for i in range(len(images)):
        label = ""
        if labels:
            text = labels[i].replace(":", "\\:").replace("'", "")
            label = f",drawbox=x=0:y=0:w=iw:h=34:color=black@0.6:t=fill,drawtext=text='{text}':x=8:y=7:fontsize=22:fontcolor=white"
        chains.append(f"[{i}:v]scale={width}:-2{label}[s{i}]")
    pad = cols * rows - len(images)
    graph = ";".join(chains)
    inputs = "".join(f"[s{i}]" for i in range(len(images)))
    if pad:
        graph += f";color=c=black:s={width}x{width * 16 // 9}:d=1[blank];[blank]split={pad}" + "".join(f"[b{k}]" for k in range(pad))
        inputs += "".join(f"[b{k}]" for k in range(pad))
    graph += f";{inputs}xstack=inputs={cols * rows}:layout=" + "|".join(
        f"{(i % cols) * width}_{(i // cols) * (width * 16 // 9)}" for i in range(cols * rows)) + "[o]"
    try:
        system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", *ins, "-filter_complex", graph, "-map", "[o]",
                         "-frames:v", "1", "-q:v", "3", str(dest)], "ffmpeg (hoja de fotogramas)")
    except RuntimeError:
        if labels:  # an ffmpeg without drawtext (no fonts): the sheet without labels is still useful
            contact_sheet(images, dest, None, cols, width)
        else:
            raise


def cover(slug: str, frame: int, dest: Path) -> Path:
    out = episode_dir(slug)
    props = _props(slug, "portada", {"timeline": timeline(slug)})
    run(remotion("still", entry(slug), "Reel", str(dest), f"--props={props}", f"--public-dir={out / 'publico'}",
                 f"--frame={frame}", "--log=error"), out / "portada.log", "la portada (Remotion)")
    return dest


def character_sheet(piece: str, title: str, variants: list[dict], dest: Path, base: dict | None = None, palette: str = "alfar",
                    slug: str | None = None, scale: float = 0.62, cols: int = 4) -> Path:
    """A character sheet: the piece in each variant (expressions, poses) → a PNG."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    props = {"piece": piece, "title": title, "palette": palette, "base": base or {}, "variants": variants, "cols": cols,
             "cell": [300, int(560 * scale / 0.62)], "scale": scale, "ground": int(470 * scale / 0.62)}
    pfile = dest.with_suffix(".props.json")
    pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    try:
        run(remotion("still", entry(slug or "_hojas"), "Hoja", str(dest), f"--props={pfile}", "--log=error"),
            dest.with_suffix(".log"), "la hoja del personaje (Remotion)")
    finally:
        pfile.unlink(missing_ok=True)
    dest.with_suffix(".log").unlink(missing_ok=True)
    return dest


def typecheck() -> str:
    """TypeScript over remotion/src (no drawing): '' if fine, else the errors (file:line)."""
    tsc = REMOTION / "node_modules" / "typescript" / "bin" / "tsc"
    node = system.find_tool("node", "NODE_BIN")
    if not tsc.exists() or not node:
        raise RenderError("falta TypeScript en remotion/node_modules: `cd remotion && npm ci` (o /fabrica:actualizar)")
    r = subprocess.run([node, str(tsc), "--noEmit", "-p", "."], cwd=REMOTION, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    return "" if r.returncode == 0 else (r.stdout + r.stderr).strip()


def video_sheet(video: Path, start: float, end: float, fps: float, dest: Path, cols: int = 6) -> list[float]:
    """Frames of a stretch of a video in one image (to judge movement and rhythm)."""
    n = max(1, int((end - start) * fps))
    times = [round(start + i / fps, 3) for i in range(n)]
    tmp = dest.with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{end - start:.3f}",
                         "-vf", f"fps={fps},scale=270:-2", str(tmp / "%04d.jpg")], "ffmpeg (hoja del vídeo)")
        imgs = sorted(tmp.glob("*.jpg"))
        contact_sheet(imgs, dest, [f"{start + i / fps:.2f}s" for i in range(len(imgs))], cols=cols, width=270)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return times[: len(times)]
