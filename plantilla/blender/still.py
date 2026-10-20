"""One full-quality still of scene.blend (covers). Run: blender -b scene.blend -P blender/still.py -- <out.png> <frame> [samples]"""

from __future__ import annotations

import sys

import bpy


def main(out: str, frame: str, samples: str = "64") -> None:
    scene = bpy.context.scene
    scene.frame_set(int(frame))  # the camera is whichever shot is live at that frame (timeline markers)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = int(samples)
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1 :])
