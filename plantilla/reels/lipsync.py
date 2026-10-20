"""Rhubarb Lip Sync (phonetic recognizer, language-agnostic) -> viseme cues."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from reels import system

# Rhubarb shapes -> our rig's mouth meshes (PLAN.md §6).
RHUBARB_TO_VISEME = {
    "X": "mouth_rest",  # idle / silence
    "A": "mouth_M",  # closed: M, B, P
    "B": "mouth_E",  # slightly open, clenched teeth
    "C": "mouth_E",  # open: E
    "D": "mouth_A",  # wide open: A
    "E": "mouth_O",  # rounded: O
    "F": "mouth_O",  # puckered: U, W
    "G": "mouth_E",  # F, V
    "H": "mouth_A",  # L
}


def rhubarb_bin() -> str:
    return system.rhubarb()


def cues_for(wav: Path, text: str) -> list[dict]:
    """Return [{start, end, viseme}] for one wav file (cached next to it)."""
    out = wav.with_suffix(".visemes.json")
    if out.exists() and out.stat().st_mtime > wav.stat().st_mtime:
        return json.loads(out.read_text(encoding="utf-8"))
    dialog = wav.with_suffix(".txt")
    dialog.write_text(text, encoding="utf-8")
    # Rhubarb skips quiet speech (a whispered "…te quedan tres" got no mouth at all): analyse a copy with the
    # quiet parts lifted (dynamic normalisation). The audio people hear is untouched.
    lifted = wav.with_suffix(".lift.wav")
    result_file = wav.with_suffix(".rhubarb.json")
    # Every tool runs from the clip's folder with bare file names: Rhubarb and ffmpeg never see the project's path,
    # which on Windows may have accents (see reels/system.py, native tools).
    cwd = wav.parent
    system.run_tool([system.ffmpeg(), "-v", "error", "-y", "-i", system.native_path(wav, cwd),
                     "-af", "dynaudnorm=f=75:g=9:m=30", system.native_path(lifted, cwd)],
                    "ffmpeg (preparar el audio para los labios)", cwd=cwd)
    try:
        # -o, never stdout: on Windows, Rhubarb 1.14 with -q writes nothing to stdout and still exits with 0.
        # Its .exe must sit in an ASCII folder (it finds res/ next to itself), its input files need not.
        run = system.run_tool(
            [system.ascii_tool(rhubarb_bin(), extras=("res",)), "-r", "phonetic", "-f", "json", "-q",
             "--dialogFile", system.native_path(dialog, cwd), "-o", system.native_path(result_file, cwd),
             system.native_path(lifted, cwd)],
            f"Rhubarb (los labios) con {wav.name}", cwd=cwd, timeout=600)
        raw = result_file.read_text(encoding="utf-8") if result_file.exists() else ""
    finally:
        lifted.unlink(missing_ok=True)
        result_file.unlink(missing_ok=True)
    cues = [{"start": c["start"], "end": c["end"], "viseme": RHUBARB_TO_VISEME[c["value"]]}
            for c in _mouth_cues(raw, wav, run.stderr)]
    out.write_text(json.dumps(cues), encoding="utf-8")
    return cues


def _mouth_cues(raw: str, wav: Path, stderr: str) -> list[dict]:
    """Rhubarb's mouthCues, or a plain-Spanish error when it gave back nothing usable."""
    why = system.tail(stderr) or "sin mensaje de error"
    if not raw.strip():
        raise RuntimeError(f"Rhubarb (los labios) no ha devuelto nada para {wav.name} ({why}). "
                           "Ejecuta `uv run reels doctor` y, si sigue, copia este mensaje al tutor (/fabrica:tarrito).")
    try:
        return json.loads(raw)["mouthCues"]
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"Rhubarb (los labios) ha devuelto algo que no entiendo para {wav.name}: {e} ({why})")


def cues_for_all(items: list[tuple[Path, str]]) -> list[list[dict]]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda it: cues_for(*it), items))
