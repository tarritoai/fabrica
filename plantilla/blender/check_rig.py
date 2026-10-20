"""Build characters by code and report their rig interface as JSON (tests/test_personajes.py, `reels personaje`).

Run: blender -b --factory-startup -P blender/check_rig.py -- <out.json> <character id | @form> [...]
"@<form>" builds a bare object of that form (rigs/thing.py) with default colours.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402

import lib  # noqa: E402
from rigs import animate, placeholders  # noqa: E402

PARTS = ["ctrl_body", "ctrl_head", "eye_L", "eye_R", "eyelid_L", "eyelid_R", "brow_L", "brow_R", "mouth_rest", "mouth_M",
         "mouth_E", "mouth_A", "mouth_O", "mouth_smile", "ctrl_arm_L", "ctrl_arm_R", "lamp_bulb",
         "rod_lower_L", "rod_upper_R", "spring_lower", "spring_upper", "knob_elbow"]


def report(char_id: str) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib.set_cast({})
    if char_id.startswith("@"):
        meta = {"placeholder": {"shape": "object"}, "object": {"form": char_id[1:], "arms": {"style": "palito"},
                                                               "accessories": [{"type": "vapor"}, {"type": "gafas"}]}}
        lib.character_meta = animate.character_meta = lambda c: meta  # noqa: E731
        cid = "t"
    else:
        meta, cid = lib.character_meta(char_id), char_id
    root = placeholders.build(cid, meta)
    found = {p: lib.find(root, p) is not None for p in PARTS}
    acting = sorted(o.name.split(".")[0] for o in root.children_recursive if "act_poses" in o.keys())
    # Animate a short made-up beat of every emotion: the rig must accept the whole interface.
    beats = [{"id": i + 1, "speaker": None, "line": None, "reactor": cid, "emotion": e, "listener_emotion": "neutral", "action": "idle",
              "camera": "x", "event": None, "start_frame": i * 10, "end_frame": (i + 1) * 10, "audio": None, "away": False}
             for i, e in enumerate(animate.EMOTIONS)]
    animate.animate(cid, root, {"fps": 30, "total_frames": len(beats) * 10, "beats": beats, "offscreen": []}, {}, None)
    meshes = [o for o in root.children_recursive if o.type == "MESH"]
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices]
    return {"parts": found, "acting": acting, "meshes": len(meshes), "min_z": min(zs), "max_z": max(zs),
            "emissive_lights": sorted(o.name.split(".")[0] for o in root.children_recursive if o.type == "LIGHT")}


def main(out: str, *ids: str) -> None:
    Path(out).write_text(json.dumps({i: report(i) for i in ids}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1:])
