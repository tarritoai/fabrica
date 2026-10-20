"""The same room in the future (beats with ambience "ruinas"): rubble, a red siren, dusty air,
and a giant robot floating in front of the island whose spotlight picks out one human at a time.

Everything here exists only while the ruins last (hide_render keys), so the present stays untouched.
Spotlight targets come from the script: the robot's lines light whoever reacts to them (beat.reactor),
and when the AI steps in front ("Este no.") the light stays on the AI.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from lib import bake, empty, material, primitive, rad, srgb

ROBOT_HEAD = Vector((0.15, -6.6, 5.4))  # eyes' centre, world
ROBOT_SCALE = 1.8  # colossal next to a 2.5 m room
SIREN_HZ = 0.9


def spans(timeline: dict) -> list[tuple[int, int]]:
    """[start, end) frame spans of the future: from "ruinas" until the sound goes back to the present ("noche").

    A quieter ambience inside it ("calma": the siren stops) is still the future.
    """
    out, inside, start = [], False, 0
    for b in timeline["beats"]:
        amb = b.get("ambience")
        if amb == "ruinas" and not inside:
            inside, start = True, b["start_frame"]
        elif amb == "noche" and inside:
            out.append((start, b["start_frame"]))
            inside = False
    if inside:
        out.append((start, timeline["total_frames"]))
    return out


def _only_during(objs, sp: list[tuple[int, int]], total: int) -> None:
    frames, values = [0], [1.0]
    for a, z in sp:
        frames += [a, z]
        values += [0.0, 1.0]
    for o in objs:
        bake(o, "hide_render", -1, frames, values, interp="CONSTANT")


def _rubble(root, island_center, seed: int = 31) -> list:
    rng = random.Random(seed)
    stone = material("rubble_stone", "#3a3440", 0.95)
    brick = material("rubble_brick", "#7a4a3c", 0.9)
    dust = material("rubble_dust", "#4a4550", 1.0)
    out = []
    cx, cy = island_center[0], island_center[1]
    for i in range(34):
        x, y = cx + rng.uniform(-3.0, 3.0), cy + rng.uniform(-1.3, 1.5)
        if -1.1 < x < 1.3 and 0.2 < y < 1.5:  # keep the desk area walkable / readable
            continue
        if rng.random() < 0.55:
            s = rng.uniform(0.05, 0.16)
            o = primitive("ico_sphere", f"rubble_{i}", (x, y, s * 0.5), (s, s * rng.uniform(0.7, 1.2), s * 0.6), root, stone, subdivisions=1)
        else:
            o = primitive("cube", f"rubble_brick_{i}", (x, y, 0.04), (0.11, 0.055, 0.04), root, brick)
        o.rotation_euler = (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0, 3.1))
        out.append(o)
    # Dust drifts on the floor and a slab fallen against the desk.
    for i in range(6):
        x, y = cx + rng.uniform(-2.5, 2.5), cy + rng.uniform(-1.0, 1.2)
        out.append(primitive("cylinder", f"rubble_dust_{i}", (x, y, 0.005), (rng.uniform(0.3, 0.6), rng.uniform(0.2, 0.4), 0.01), root, dust, vertices=9))
    slab = primitive("cube", "rubble_slab", (1.25, 0.25, 0.35), (0.5, 0.06, 0.35), root, stone)
    slab.rotation_euler = (rad(-25), rad(12), rad(15))
    out.append(slab)
    return out


def _haze(root, island_center) -> bpy.types.Object:
    """Dusty air so the spotlight draws a beam (EEVEE volumetrics)."""
    mat = bpy.data.materials.new("future_haze")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.012
    vol.inputs["Color"].default_value = srgb("#c9b8c4")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(vol.outputs["Volume"], out.inputs["Volume"])
    # From the robot to the back wall: the beam crosses all of it.
    c = Vector(island_center)
    box = primitive("cube", "future_haze", (c.x, (c.y + ROBOT_HEAD.y) / 2 + 0.6, 2.0), (4.0, (c.y - ROBOT_HEAD.y) / 2 + 1.2, 3.2), root, mat)
    box.visible_shadow = False
    return box


def _robot(root) -> list:
    """A colossal silhouette facing the island (+Y): dark plates, a visor and two red eyes, rim-lit from behind."""
    dark = material("robot_plate", "#0b0b10", 0.45)
    edge = material("robot_edge", "#1c1c26", 0.35)
    eye = material("robot_eye", "#ff2a1a", 0.3, emission=40.0)
    # Built around its eyes at the origin, then placed and scaled as one piece.
    h = Vector((0, 0, 0))
    rob = empty("ROBOT", tuple(ROBOT_HEAD), root)
    neck = empty("ROBOT_NECK", (0, -0.5, -0.9), rob)  # pivot: head, visor, jaw and eyes turn together
    def on_neck(o):
        o.parent = neck
        o.location = Vector(o.location) - Vector((0, -0.5, -0.9))
        return o
    parts = [
        on_neck(primitive("cube", "robot_head", (h.x, h.y - 0.5, h.z + 0.15), (1.15, 0.95, 0.95), rob, dark)),
        on_neck(primitive("cube", "robot_visor", (h.x, h.y + 0.47, h.z), (0.95, 0.06, 0.32), rob, edge)),
        on_neck(primitive("cube", "robot_jaw", (h.x, h.y - 0.25, h.z - 1.0), (0.8, 0.7, 0.25), rob, dark)),
        primitive("cube", "robot_neck", (h.x, h.y - 0.6, h.z - 1.5), (0.5, 0.5, 0.5), rob, edge),
        primitive("cube", "robot_chest", (h.x, h.y - 0.9, h.z - 4.0), (3.0, 1.4, 2.2), rob, dark),
        primitive("cube", "robot_shoulder_L", (h.x + 3.5, h.y - 0.9, h.z - 2.3), (1.3, 1.3, 1.0), rob, dark),
        primitive("cube", "robot_shoulder_R", (h.x - 3.5, h.y - 0.9, h.z - 2.3), (1.3, 1.3, 1.0), rob, dark),
        primitive("cube", "robot_arm_L", (h.x + 4.1, h.y - 0.6, h.z - 5.6), (0.8, 0.8, 2.6), rob, dark),
        primitive("cube", "robot_arm_R", (h.x - 4.1, h.y - 0.6, h.z - 5.6), (0.8, 0.8, 2.6), rob, dark),
    ]
    for p in parts:
        p.modifiers.new("bevel", "BEVEL").width = 0.08
    for side, dx in (("L", 0.42), ("R", -0.42)):
        parts.append(on_neck(primitive("cube", f"robot_eye_{side}", (h.x + dx, h.y + 0.52, h.z + 0.02), (0.22, 0.03, 0.07), rob, eye)))
        glow = bpy.data.lights.new(f"robot_eye_glow_{side}", "POINT")
        glow.color = srgb("#ff3020")[:3]
        glow.energy = 80  # glows, but doesn't light its own face: it must stay a silhouette
        glow.shadow_soft_size = 0.2
        g = bpy.data.objects.new(f"robot_eye_glow_{side}", glow)
        bpy.context.scene.collection.objects.link(g)
        g.parent = rob
        g.location = (h.x + dx, h.y + 1.4, h.z)
        on_neck(g)
        parts.append(g)
    # Rim from behind it: its edges cut out against the galaxy (cold, like the space light).
    rim = bpy.data.lights.new("robot_rim", "AREA")
    rim.color = srgb("#8fa8ff")[:3]
    rim.energy = 25000
    rim.size = 6.0
    r_obj = bpy.data.objects.new("robot_rim", rim)
    bpy.context.scene.collection.objects.link(r_obj)
    r_obj.location = ROBOT_HEAD + Vector((0, -9.0, 3.0))
    from lib import look_at

    look_at(r_obj, ROBOT_HEAD + Vector((0, 0, -3.0)))
    parts.append(r_obj)
    rob.scale = (ROBOT_SCALE,) * 3
    return [rob, neck, *parts]


def _spot_targets(timeline: dict, sp, heads: dict, ai: str | None, ai_spot_of_frame) -> tuple[list, list]:
    """Per frame: where the robot's spotlight points and how bright it is (0..1).

    A robot line lights whoever reacts to it (beat.reactor, the novato by default); the AI speaking
    pulls the light onto itself; other lines keep it where it is; "Aprobado" puts it out.
    """
    total = timeline["total_frames"]
    beats = timeline["beats"]
    beat_of = []
    for i, b in enumerate(beats):
        beat_of += [i] * (b["end_frame"] - b["start_frame"])
    beat_of += [len(beats) - 1] * (total - len(beat_of))
    in_ruins = [any(a <= f < z for a, z in sp) for f in range(total)]
    who: list[str | None] = []
    cur = None
    for b in beats:
        line = (b["line"] or "").lower()
        if b["speaker"] == "robot":
            cur = None if "probado" in line else (b.get("reactor") or "novato")
        elif b["speaker"] == ai and ai is not None:
            cur = ai
        who.append(cur)
    target, level = [], []
    pos, on = Vector((0, 0.4, 1.0)), 0.0
    for f in range(total):
        c = who[beat_of[f]]
        goal = (ai_spot_of_frame(f) if c == ai and ai_spot_of_frame else heads.get(c)) if c else None
        if goal is not None:
            pos = pos.lerp(goal, 0.12)  # the beam swings, it doesn't snap
        target.append(pos.copy())
        on += ((1.0 if c and in_ruins[f] else 0.0) - on) * 0.15
        level.append(on if in_ruins[f] else 0.0)
    return target, level


def build(timeline: dict, anchors: dict, heads: dict, roots: dict, ai: str | None, ai_spot_of_frame=None) -> None:
    sp = spans(timeline)
    if not sp:
        return
    fps, total = timeline["fps"], timeline["total_frames"]
    root = empty("FUTURE")
    center = anchors.get("island_center", (0, 0.35, 0))
    objs = _rubble(root, center)
    objs.append(_haze(root, center))
    objs += _robot(root)

    # Red siren from a corner of the ceiling, pulsing.
    siren = bpy.data.lights.new("future_siren", "POINT")
    siren.color = srgb("#ff2a1a")[:3]
    siren.shadow_soft_size = 0.3
    s_obj = bpy.data.objects.new("future_siren", siren)
    bpy.context.scene.collection.objects.link(s_obj)
    s_obj.location = (1.8, 1.2, 2.6)
    frames = list(range(total))
    bake(siren, "energy", -1, frames, [90 + 360 * max(0.0, math.sin(2 * math.pi * SIREN_HZ * f / fps)) ** 2 for f in frames])
    objs.append(s_obj)

    # The spotlight lives in the robot's head and follows its target.
    aim = empty("ROBOT_SPOT_TARGET", (0, 0.4, 1.0))
    spot = bpy.data.lights.new("robot_spot", "SPOT")
    spot.color = srgb("#ffd9cf")[:3]
    spot.spot_size = rad(9)
    spot.spot_blend = 0.35
    spot.shadow_soft_size = 0.05
    sp_obj = bpy.data.objects.new("robot_spot", spot)
    bpy.context.scene.collection.objects.link(sp_obj)
    sp_obj.location = ROBOT_HEAD + Vector((0, 1.2 * ROBOT_SCALE, 0.0))  # just in front of its face
    track = sp_obj.constraints.new("TRACK_TO")
    track.target = aim
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    targets, levels = _spot_targets(timeline, sp, heads, ai, ai_spot_of_frame)
    for i in range(3):
        bake(aim, "location", i, frames, [v[i] for v in targets])
    bake(spot, "energy", -1, frames, [9000.0 * v for v in levels])
    objs.append(sp_obj)
    beats = timeline["beats"]
    from lib import smoothstep

    # Power-on: the eyes are dark until its first line, then flicker on.
    first = next((b for b in beats if b["speaker"] == "robot"), None)
    eye_mat = bpy.data.materials["robot_eye"]
    bsdf_e = eye_mat.node_tree.nodes["Principled BSDF"]
    es_idx = list(bsdf_e.inputs).index(bsdf_e.inputs["Emission Strength"])
    if first is not None:
        t_on = first["start_frame"] + int(0.25 * fps)
        flick = {0: 0.0, 2: 1.0, 4: 0.1, 6: 1.0, 7: 0.3, 9: 1.0}
        power = []
        for f in frames:
            d = f - t_on
            if d < 0:
                power.append(0.0)
            elif d < 10:
                power.append(flick[max(k for k in flick if k <= d)])
            else:
                power.append(1.0)
        bake(eye_mat.node_tree, f'nodes["Principled BSDF"].inputs[{es_idx}].default_value', -1, frames, [40.0 * p for p in power])
        for side in ("L", "R"):
            bake(bpy.data.lights[f"robot_eye_glow_{side}"], "energy", -1, frames, [80.0 * p for p in power])
        # Head: scans the room for a moment, then keeps turning towards whatever its light is on.
        neck = bpy.data.objects["ROBOT_NECK"]
        yaw = []
        cur = 0.0
        for f, tgt in zip(frames, targets):
            d = tgt - ROBOT_HEAD
            follow = math.atan2(-d.x, d.y)  # face is +Y; turn about Z towards the target
            scan_t = (f - t_on) / fps
            if 0 <= scan_t < 1.6:
                want = math.radians(28) * math.sin(scan_t * 3.2)
            elif f < t_on:
                want = 0.0
            else:
                want = follow
            cur += (want - cur) * 0.12
            yaw.append(cur)
        bake(neck, "rotation_euler", 2, frames, yaw)
        bake(neck, "rotation_euler", 0, frames, [math.radians(-6) for _ in frames])  # looking down at the island

    # "Apartado": a white flash of the spotlight on its target (who is gone right after).
    gone_beat = next((b for b in beats if b["speaker"] == "robot" and b["line"] and "partado" in b["line"].lower()), None)
    if gone_beat is not None:
        flash_at = gone_beat["start_frame"] + int(0.35 * fps)
        boost = [1.0 + 5.0 * max(0.0, 1 - abs(f - flash_at) / 4.0) for f in frames]
        bake(spot, "energy", -1, frames, [9000.0 * v * b for v, b in zip(levels, boost)])

    # "Aprobado": the eyes cool from red to white, the siren dies, and the giant sinks away below the island.
    ok = next((b for b in beats if b["speaker"] == "robot" and b["line"] and "probado" in b["line"].lower()), None)
    if ok is not None:
        t_ok = ok["start_frame"] + int(0.6 * fps)
        def ease(f, start, dur):
            from lib import smoothstep
            return smoothstep((f - start) / max(1, dur))
        cool = [ease(f, t_ok, int(0.8 * fps)) for f in frames]
        red, white = srgb("#ff2a1a"), srgb("#dfe8ff")
        eye_mat = bpy.data.materials["robot_eye"]
        bsdf = eye_mat.node_tree.nodes["Principled BSDF"]
        idx = list(bsdf.inputs).index(bsdf.inputs["Emission Color"])
        for c in range(3):
            bake(eye_mat.node_tree, f'nodes["Principled BSDF"].inputs[{idx}].default_value', c, frames, [red[c] + (white[c] - red[c]) * k for k in cool])
        for side in ("L", "R"):
            light = bpy.data.lights[f"robot_eye_glow_{side}"]
            for c in range(3):
                bake(light, "color", c, frames, [red[c] + (white[c] - red[c]) * k for k in cool])
        base = [90 + 360 * max(0.0, math.sin(2 * math.pi * SIREN_HZ * f / fps)) ** 2 for f in frames]
        bake(siren, "energy", -1, frames, [e * (1 - ease(f, ok["start_frame"], int(0.5 * fps))) for f, e in zip(frames, base)])
        rob = bpy.data.objects["ROBOT"]
        # It sinks during the dawn, in the final wide shot (the threat leaves as the light comes up).
        dawn_b = next((b for b in beats if b.get("light") == "amanecer"), None)
        sink_from = dawn_b["start_frame"] - int(0.3 * fps) if dawn_b else t_ok + int(1.6 * fps)
        sink = [ease(f, sink_from, int(4.2 * fps)) for f in frames]
        bake(rob, "location", 2, frames, [ROBOT_HEAD.z - 18.0 * k for k in sink])
        # Its cold rim light goes with it: the dawn takes over the frame.
        bake(bpy.data.lights["robot_rim"], "energy", -1, frames, [25000.0 * (1 - k) for k in sink])
    # Dawn: a low golden light from where the robot stood, rising.
    dawn_beat = next((b for b in beats if b.get("light") == "amanecer"), None)
    if dawn_beat is not None:
        dawn = bpy.data.lights.new("future_dawn", "AREA")
        dawn.color = srgb("#ffb35c")[:3]
        dawn.size = 8.0
        d_obj = bpy.data.objects.new("future_dawn", dawn)
        bpy.context.scene.collection.objects.link(d_obj)
        d_obj.location = (0.5, -9.0, -1.0)
        from lib import look_at, smoothstep

        look_at(d_obj, (-0.2, 0.8, 1.2))
        start = dawn_beat["start_frame"]
        bake(dawn, "energy", -1, frames, [6000.0 * smoothstep((f - start) / (2.5 * fps)) for f in frames])
        # The dust settles: the air clears as the light comes up (otherwise the haze swallows the dawn).
        haze = bpy.data.materials["future_haze"].node_tree
        vol = next(n for n in haze.nodes if n.type == "PRINCIPLED_VOLUME")
        di = list(vol.inputs).index(vol.inputs["Density"])
        bake(haze, f'nodes["{vol.name}"].inputs[{di}].default_value', -1, frames,
             [0.012 * (1 - smoothstep((f - start + int(0.5 * fps)) / (2.0 * fps))) for f in frames])
        bake(d_obj, "location", 2, frames, [-1.0 + 2.5 * smoothstep((f - start) / (4.0 * fps)) for f in frames])
        objs.append(d_obj)
    _only_during(objs, sp, total)
    # The present's desk lamp doesn't survive into the future (and it would block the robot shots).
    lamp = [o for o in bpy.data.objects if "lampSquareTable" in o.name and o.type == "MESH"]
    frames_l, vals_l = [0], [0.0]
    for a, z in sp:
        frames_l += [a, z]
        vals_l += [1.0, 0.0]
    for o in lamp:
        bake(o, "hide_render", -1, frames_l, vals_l, interp="CONSTANT")

    # "Apartado": the flatmate is gone for the rest of the future.
    gone = gone_beat["start_frame"] + int(0.35 * fps) + 2 if gone_beat is not None else None
    for c, r in roots.items():
        if c in ("novato",) or c == ai or gone is None:
            continue
        hide_from = [(gone, z) for a, z in sp if a <= gone < z]
        if not hide_from:
            continue
        for o in r.children_recursive:
            if o.type not in ("MESH", "CURVE") or "PHONE" in o.name or o.name.startswith("phone_"):
                continue  # empties don't render; the phone has its own visibility
            frames_h, vals = [0], [0.0]
            for a, z in hide_from:
                frames_h += [a, z]
                vals += [1.0, 0.0]
            bake(o, "hide_render", -1, frames_h, vals, interp="CONSTANT")
