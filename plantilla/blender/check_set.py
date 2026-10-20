"""Build a set by code and report what is in it as JSON (tests/test_plantilla_neutral.py).

Run: blender -b --factory-startup -P blender/check_set.py -- <out.json> <set> ['<set_options json>']
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402

import lib  # noqa: E402
from sets import SETS  # noqa: E402


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, name = Path(argv[0]), argv[1]
    opts = json.loads(argv[2]) if len(argv) > 2 else {}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib.set_cast({})
    anchors = SETS[name]({"fps": 30, "total_frames": 30, "beats": [], "characters": [], "set_options": opts})
    world = bpy.context.scene.world
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None) if world and world.use_nodes else None
    out.write_text(json.dumps({
        "objects": sorted(o.name for o in bpy.data.objects),
        "lights": sorted(o.name for o in bpy.data.objects if o.type == "LIGHT"),
        "anchors": sorted(k for k in anchors),
        "slots": sorted(anchors.get("slots", {})),
        "world_color": list(bg.inputs["Color"].default_value)[:3] if bg else None,
    }), encoding="utf-8")


main()
