"""Copies of the AI in the room (beat.ai_copies / beat.ai_mini, regenerar-coro).

Every regenerate click is one more jar. The copies are full builds of the AI, animated like it but each from its
own point of view (whose mouth moves in each beat: delivery.chorus = all of them, delivery.mini = only the tiny
one). They are parked out of sight while they are not in the room, so they appear on the cut, already there.
"""

from __future__ import annotations

import math

from mathutils import Vector

from lib import bake, rad

MINI_SCALE = 0.4  # of the AI's own scale
CHEAT = 0.5  # copies turn this share of the way to face the novato (the rest stays open to camera, like the AI)
PARK = Vector((0.0, 0.0, -60.0))  # under the island, out of every shot
MAIN, MINI = "claude_main", "mini"  # gaze ids for the original and the tiny one, as the others see them


def counts(timeline: dict) -> tuple[list[int], list[bool]]:
    """Per frame: how many copies of the AI stand in the room (the AI included) and whether the mini is there."""
    n, mini, per_n, per_mini = 1, False, [], []
    for b in timeline["beats"]:
        n = b.get("ai_copies") or n
        mini = b["ai_mini"] if b.get("ai_mini") is not None else mini
        span = b["end_frame"] - b["start_frame"]
        per_n += [n] * span
        per_mini += [mini] * span
    pad = timeline["total_frames"] - len(per_n)
    return per_n + [n] * pad, per_mini + [mini] * pad


def wanted(timeline: dict) -> tuple[int, bool]:
    n, mini = counts(timeline)
    return max(n, default=1) - 1, any(mini)


def voiced(timeline: dict, ai: str, who: str) -> dict:
    """The timeline as one jar sees it: it is the speaker only of the lines its own mouth says.

    who: "main" (the AI: its solo and chorus lines), "copy" (chorus lines), "mini" (mini lines) or
    "other" (everyone else). A jar that keeps quiet sees the one talking: MAIN (the original) or MINI.
    """
    speaks = {"main": ("solo", "chorus"), "copy": ("chorus",), "mini": ("mini",)}.get(who, ())
    beats = []
    for b in timeline["beats"]:
        if b["speaker"] == ai:
            d = b.get("delivery") or {}
            kind = "mini" if d.get("mini") else "chorus" if d.get("chorus", 1) > 1 else "solo"
            if kind == "mini" and kind not in speaks:
                b = {**b, "speaker": MINI}
            elif kind not in speaks and who != "other":
                b = {**b, "speaker": MAIN}
        beats.append(b)
    return {**timeline, "beats": beats}


def place(anchors: dict, ai_root, n: int, mini: bool, load) -> tuple[list, object | None]:
    """Build n copies at the set's copy spots and the mini behind the mug. load(char_id) builds a character."""
    spots = anchors.get("copy_spots", [])
    if n > len(spots):
        raise ValueError(f"the set has room for {len(spots)} copies of the AI, the script asks for {n}")
    char_id = ai_root.name.split("_", 1)[1].split(".")[0]
    k = ai_root.scale[0]
    out = []
    target = Vector(anchors.get("copy_target") or anchors["slots"]["left"])  # where the novato sits: they all stare at him
    for loc in spots[:n]:
        d = target - Vector(loc)
        yaw = CHEAT * math.degrees(math.atan2(d.x, -d.y))  # yaw 0 faces -Y (the camera side)
        root = load(char_id)
        root.location, root.rotation_euler, root.scale = loc, (0, 0, rad(yaw)), (k,) * 3
        for cup in [o for o in root.children_recursive if o.name.split(".")[0] == "claude_cup"]:
            for obj in [cup, *cup.children_recursive]:
                obj.hide_render = obj.hide_viewport = True  # only the original (and the mini) keep their tiny cup
        out.append(root)
    small = None
    if mini:
        loc, yaw = anchors["mini_spot"]
        small = load(char_id)
        small.location, small.rotation_euler, small.scale = loc, (0, 0, rad(yaw)), (k * MINI_SCALE,) * 3
    return out, small


def park(timeline: dict, copies: list, small) -> None:
    """Out of sight (under the island) while they are not in the room; on the cut, already in place."""
    per_n, per_mini = counts(timeline)
    jars = [(root, lambda f, i=i: per_n[f] > i + 1) for i, root in enumerate(copies)]
    if small is not None:
        jars.append((small, lambda f: per_mini[f]))
    for root, here in jars:
        home = root.location.copy()
        frames, vals, last = [], [], None
        for f in range(len(per_n)):
            v = here(f)
            if v != last:
                frames.append(f)
                vals.append(home if v else home + PARK)
                last = v
        for i in range(3):
            bake(root, "location", i, frames, [p[i] for p in vals], interp="CONSTANT")


def glow(jars: list, energy: float = 6.0) -> None:
    """Every jar gives off a little warm light of its own, spilling forward out of the lid's slit: in the dark room
    they light the desk, the floor, each other and their own faces from above (the shading stays: no emissive clay,
    it flattens them). Parked jars take their light with them."""
    import bpy

    from lib import find, link, srgb

    for root in jars:
        head = find(root, "ctrl_head") or root
        lid = find(root, "think_light")
        bpy.context.view_layer.update()
        top = head.matrix_world.inverted() @ lid.matrix_world.translation if lid else head.location
        data = bpy.data.lights.new(f"self_glow.{root.name}", "POINT")
        data.color = srgb("#ffb45a")[:3]
        data.energy = energy
        data.shadow_soft_size = 0.12
        obj = bpy.data.objects.new(f"self_glow.{root.name}", data)
        link(obj, head)
        obj.location = (top.x, top.y - 0.3, top.z + 0.02)


def cameras(anchors: dict, small_head: Vector | None, yaw: float) -> dict:
    """The tiny one's close-up: low, just over the mug, at its own scale."""
    if small_head is None:
        return {}
    from cameras import _facing

    off = _facing(Vector((-0.06, -0.62, 0.03)), yaw)
    return {"closeup_mini": dict(loc=small_head + off, target=small_head + Vector((0, 0, -0.025)), lens=55, fstop=2.0)}
