"""Render scene.blend. Run: blender -b scene.blend -P blender/render.py -- <out_dir> <quality> [keyframes]

quality: humo (20 %, 1 sample: the free smoke test, CI) | draft (33 %, 6 samples) | preview (50 % res, 16 samples) | final (100 %, 32 samples, motion blur)
| ultra (150 % scaled down, 64 samples, motion blur)
mode: full | keyframes | range <first> <last> (frames, inclusive) | frames <f1,f2,...> (stills, e.g. one per beat)
The dressed room (area lights, soft shadows, DOF) shows grain below ~16 samples; 32 is clean.
keyframes: only the middle frame of each beat plus first/last (for quick review / the visual critic).
Full renders are resumable: frames already on disk are skipped.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

QUALITY = {
    "humo": dict(percent=20, samples=1, motion_blur=False),
    "draft": dict(percent=33, samples=6, motion_blur=False),
    "preview": dict(percent=50, samples=16, motion_blur=False),
    "final": dict(percent=100, samples=32, motion_blur=True),
    # Supersampled: rendered at 1.5x and scaled down to 1080x1920 (lanczos) on the cloud box: crisper
    # edges and less grain. ~4x the GPU time of final (still cents on a rented GPU).
    "ultra": dict(percent=150, samples=64, motion_blur=True),
}


def main(out_dir: str, quality: str, mode: str = "full", first: str = "", last: str = "") -> None:  # noqa: C901
    scene = bpy.context.scene
    q = QUALITY[quality]
    scene.render.resolution_percentage = q["percent"]
    scene.eevee.taa_render_samples = q["samples"]
    scene.render.use_motion_blur = q["motion_blur"]
    engine = os.environ.get("REELS_RENDER_ENGINE", "").strip().upper()
    if engine == "CYCLES":
        # Machines without a usable GPU/OpenGL (CI runners, some VMs): EEVEE cannot start there, Cycles on CPU can.
        # It looks different (no EEVEE bloom tricks) but proves the whole pipeline end to end.
        try:
            scene.render.engine = "CYCLES"
        except TypeError as e:
            print(f"[render] no Cycles here: {e}")
        else:
            scene.cycles.device = "CPU"
            scene.cycles.samples = q["samples"]
            scene.cycles.use_denoising = False
    # Keep the scene in memory between frames and skip PNG compression (intermediate frames).
    scene.render.use_persistent_data = True
    scene.render.image_settings.compression = 0
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if mode == "frames":
        for f in sorted({int(x) for x in first.split(",")}):
            path = out / f"kf_{f:04d}.png"
            if path.exists():
                continue
            scene.frame_set(f)
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
        return

    if mode == "keyframes":
        markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
        frames = {scene.frame_start, scene.frame_end}
        bounds = [m.frame for m in markers] + [scene.frame_end + 1]
        for m, nxt in zip(markers, bounds[1:]):
            frames.add((m.frame + nxt) // 2)
        for f in sorted(frames):
            scene.frame_set(f)
            scene.render.filepath = str(out / f"kf_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
        return

    # Drop zero-byte placeholders left by an interrupted run, then let Blender skip the rest.
    for p in out.glob("*.png"):
        if p.stat().st_size == 0:
            p.unlink()
    if mode == "range":  # only some shots (quick previews); frames keep their absolute numbers
        scene.frame_start, scene.frame_end = int(first), int(last)
    scene.render.filepath = str(out / "####")
    scene.render.use_overwrite = False
    scene.render.use_placeholder = True
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1 :])
