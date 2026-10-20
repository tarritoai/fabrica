"""Expression sheet of one character: every emotion, the mouth shapes, its gestures and a blink, one still each.

Run: blender -b --factory-startup -P blender/character_sheet.py -- <character id> <out_dir> [cell_px] [only=a,b]

The character stands alone in the plain studio set (blender/sets_generic.py), built exactly as an episode would
build it (placeholders.build) and animated with the same code (rigs/animate.py) over a made-up timeline.
Writes <out_dir>/cell_NN.png and <out_dir>/cells.json (labels in order); `reels personaje` tiles them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import character_meta, empty, find, set_cast  # noqa: E402
from rigs import animate, placeholders  # noqa: E402

EMOTIONS = ["neutral", "orgulloso", "confuso", "alarma", "juzgando", "hundido", "panico", "aliviado"]
VISEMES = ["mouth_M", "mouth_E", "mouth_A", "mouth_O"]
BEAT = 30  # frames per cell beat
SAMPLE = 22  # the frame inside each beat that is rendered (the pose has settled)


def _timeline(char_id: str, actions: list[str], lamp: bool) -> tuple[dict, list[tuple[int, str]]]:
    beats, cells = [], []

    def beat(label: str, **kw) -> dict:
        n = len(beats)
        b = {"id": n + 1, "speaker": None, "line": None, "reactor": char_id, "emotion": "neutral", "listener_emotion": "neutral",
             "action": "idle", "camera": "two_shot", "event": None, "start_frame": n * BEAT, "end_frame": (n + 1) * BEAT,
             "audio": None, "away": False, **kw}
        beats.append(b)
        if label:
            cells.append((b["start_frame"] + SAMPLE, label))
        return b

    for e in EMOTIONS:
        beat(e, emotion=e)
    for v in VISEMES:  # one spoken beat per mouth shape, holding it
        beat(v.replace("mouth_", "boca "), speaker=char_id, line="a", audio={"file": "none.mp3", "offset": 0.0, "duration": 1.0,
                                                                          "visemes": [{"start": 0.0, "end": 1.0, "viseme": v}]})
    for a in actions:
        if a != "idle":
            beat(a, action=a, emotion="neutral")
    blink_at = len(beats) * BEAT + SAMPLE
    beat("parpadeo")
    if lamp:
        beat("", emotion="neutral")
        beat("apagado", ai_power="off", ai_power_at=0.0)
    total = len(beats) * BEAT
    return {"fps": 30, "total_frames": total, "beats": beats, "offscreen": [], "tone": "comedia"}, cells, blink_at


def main(char_id: str, out_dir: str, cell_px: str = "420", only: str = "") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    set_cast({})
    import sets_generic

    anchors = sets_generic.estudio({"set_options": {"plinth_on": False}})
    meta = character_meta(char_id)
    human = (meta.get("placeholder") or {}).get("shape") == "human"
    if human:  # humans act from the human slot (rigs/arms.py solves the arms of the lead)
        set_cast({"novato": char_id})
        char_id = "novato"
    root = placeholders.build(char_id, meta)
    if not human:
        root.scale = (1.0, 1.0, 1.0)
    root.rotation_euler = (0, 0, 0.0)
    lamp = find(root, "lamp_bulb") is not None
    actions = [a for a in meta.get("actions", []) if a in animate.ACTIONS]
    timeline, cells, blink_at = _timeline(char_id, actions, lamp)
    # Blinks only in their own cell (a random blink would land in some expression).
    animate._blink_frames = lambda *a, **k: {blink_at - 2: 0.4, blink_at - 1: 0.12, blink_at: 0.04, blink_at + 1: 0.1}
    bpy.context.view_layer.update()
    if human:
        from rigs import arms

        arms.animate(root, timeline, None, Vector((0, -0.4, 0.75)), None, [], standing=True, typing_ok=False)
    animate.animate(char_id, root, timeline, {}, None)
    # Frame the character: bounds of its meshes at rest.
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == "MESH" and not o.hide_render for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.z - lo.z) * 1.25
    cam_data = bpy.data.cameras.new("SHEET_CAM")
    cam_data.lens = 70
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 36
    cam = bpy.data.objects.new("SHEET_CAM", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    dist = size / 2 / (36 / 2 / 70) + (hi.y - lo.y)
    direction = Vector((0.32, -1.0, 0.18)).normalized()
    cam.location = center + direction * dist
    target = empty("SHEET_TARGET", tuple(center))
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.engine = "BLENDER_EEVEE"
    px = int(cell_px)
    scene.render.resolution_x, scene.render.resolution_y = px, int(px * 1.25)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.3
    scene.render.image_settings.file_format = "PNG"
    # Label in the corner of every cell (Blender's own font: no font files to ship).
    curve = bpy.data.curves.new("SHEET_LABEL", "FONT")
    curve.size = 0.024
    curve.align_x = "LEFT"
    label_obj = bpy.data.objects.new("SHEET_LABEL", curve)
    bpy.context.scene.collection.objects.link(label_obj)
    ink = bpy.data.materials.new("sheet_ink")
    ink.use_nodes = True
    nodes = ink.node_tree.nodes
    nodes.clear()
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.015, 0.012, 1)
    outn = nodes.new("ShaderNodeOutputMaterial")
    ink.node_tree.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    curve.materials.append(ink)
    label_obj.parent = cam
    label_obj.location = (-0.19, -0.245, -1.0)  # bottom-left of the frame, 1 m in front of the lens (70 mm, 4:5)
    wanted = set(filter(None, only.split(",")))
    # Expressions and mouths are framed on the face; gestures show the whole body.
    head = find(root, "ctrl_head")
    face_parts = [o for o in (head.children_recursive if head else []) if o.type == "MESH"
                  and o.name.split(".")[0].startswith(("eye_white", "eye_", "brow_", "mouth_rest"))]
    if face_parts and not human:
        fp = [o.matrix_world @ Vector(c) for o in face_parts for c in o.bound_box]
        fc = sum(fp, Vector()) / len(fp)
        fsize = max(max(p.x for p in fp) - min(p.x for p in fp), max(p.z for p in fp) - min(p.z for p in fp)) * 2.6
    else:
        fc, fsize = center, size
    if human:
        hp = find(root, "eye_L").matrix_world.translation
        fc, fsize = Vector((center.x, hp.y, hp.z - 0.05)), 0.75
    close_loc = fc + direction * (fsize / 2 / (36 / 2 / 70) + 0.3)
    wide_loc = cam.location.copy()
    labels = []
    for n, (frame, label) in enumerate(cells):
        close = n < len(EMOTIONS) + len(VISEMES) or label == "parpadeo"
        cam.location = close_loc if close else wide_loc
        target.location = fc if close else center
        if wanted and label not in wanted:
            continue
        curve.body = label
        scene.frame_set(frame)
        scene.render.filepath = str(out / f"cell_{n:02d}.png")
        bpy.ops.render.render(write_still=True)
        labels.append({"file": f"cell_{n:02d}.png", "label": label})
    (out / "cells.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[character_sheet] {len(labels)} cells -> {out}")


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1:])
