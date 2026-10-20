"""Musical episodes (timeline["score"], reels/score.py): every note moves and lights something, on its frame.

- tarro notes: the jar of that pitch hops (anticipation squash, stretch, the lid pops) and its lid flashes its own
  colour, dying away with the sound.
- bombo: the room washes pump in the section's palette, the cameras punch in and everyone nods to the beat.
- caja: a cold back light snaps on the jars' rims. hats: a light runs along the fairy lights.
- sections: palette per bar, `impact` (a white flash into the drop: the whole band jumps, arms up),
  `blackout_tail` (every room light dead, the jars gasp), `wobble` (a floor light breathes with the bass).
- faces: a jar sings its own notes (mouth open), grins through the loud sections, squints happily on accents;
  an accent ('D6!') also spins it round once.

All on delta channels and new lights, so the regular animation (blinks, breathing, the copies parking) stays as is.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from lib import bake, find, srgb

# Jar 0 is the AI itself: it keeps its own amber. The copies get the rest, in order.
JAR_COLORS = ["#ffb45a", "#ff4f8b", "#3dd6ff", "#a26bff", "#5dff9e", "#ffe14d", "#ff7a3d", "#4d7bff", "#ff5ad1", "#7dfff0",
              "#c6ff4d", "#ff9aa8"]
PALETTES = {
    "ambar": ["#ffb45a", "#ff8a3d", "#ffd38a"],
    "neon": ["#ff2fb3", "#2fe6ff", "#b14bff"],
    "frio": ["#3d8bff", "#6a5cff", "#2fe6ff"],
    "arcoiris": ["#ff3b6b", "#ffb02e", "#3dff8b", "#2fb8ff", "#b14bff"],
    "negro": [],
}
# Room lights the blackout kills (the set's own; the jars keep glowing: they are the show).
ROOM_LIGHTS = ("lamp_key", "lamp_light", "fairy_glow", "moon_rim", "room_fill", "galaxy_rim", "ai_rim", "galaxy_under", "screen_light")
# (name, location, target, cone °, energy): colour pools on the back wall, and beams from up high behind the desk
# that cut through the haze down onto the band, like stage lights.
WASHES = [
    ("wash_L", (-1.3, -0.6, 2.7), (-1.2, 1.7, 1.1), 60, 700.0),
    ("wash_R", (1.5, -0.6, 2.7), (1.4, 1.6, 1.2), 60, 700.0),
    ("beam_L", (-1.1, 1.4, 2.9), (-0.4, 0.2, 0.0), 22, 900.0),
    ("beam_C", (0.25, 1.5, 3.0), (0.25, 0.1, 0.0), 18, 900.0),
    ("beam_R", (1.5, 1.4, 2.9), (0.9, 0.2, 0.0), 22, 900.0),
]
HAZE_DENSITY = 0.018
HOP = 0.045  # m, a full-velocity hop
SPIN = 9  # frames for the full turn on an accent
LIGHT_DECAY = 0.35  # s, a jar's flash dies with its sound


def _per_frame(total: int, fill: float = 0.0) -> list[float]:
    return [fill] * total


def _section_at(score: dict, total: int) -> list[dict | None]:
    out = [None] * total
    for s in score["sections"]:
        for f in range(s["start_frame"], min(s["end_frame"], total)):
            out[f] = s
    return out


def _blackout(score: dict, total: int) -> list[float]:
    """1 where the room is lit, 0 in a section's blackout tail or a 'negro' palette."""
    lit = [1.0] * total
    for s in score["sections"]:
        dark_from = s["end_frame"] - s["blackout_tail"] if s["blackout_tail"] else s["end_frame"]
        for f in range(max(0, dark_from), min(s["end_frame"], total)):
            lit[f] = 0.0
    return lit


def _pulses(hits: list[tuple[int, float]], total: int, decay_frames: float, attack: int = 0) -> list[float]:
    """Sum of exponential pulses (velocity-scaled) starting at each hit frame, capped at 1.5."""
    out = [0.0] * total
    span = int(decay_frames * 6)
    for f0, v in hits:
        for f in range(max(0, f0 - attack), min(total, f0 + span)):
            t = f - f0
            out[f] += v * (math.exp(-t / decay_frames) if t >= 0 else (attack + t + 1) / (attack + 1) * 0.6)
    return [min(1.5, x) for x in out]


def _material_copy(obj, color: str, strength_input: str | None = None):
    """Give one object its own copy of its material, emitting `color`."""
    slot = obj.material_slots[0] if obj.material_slots else None
    if slot is None or slot.material is None:
        return None
    mat = slot.material.copy()
    slot.material = mat
    for node in mat.node_tree.nodes:
        if node.type == "EMISSION":
            node.inputs["Color"].default_value = srgb(color)
        elif node.type == "BSDF_PRINCIPLED" and strength_input:
            node.inputs["Emission Color"].default_value = srgb(color)
    return mat


def _jars(timeline: dict, jars: list, lit: list[float], fps: int, total: int) -> None:
    score = timeline["score"]
    frames = list(range(total))
    # The drop: the whole band leaps together (bigger than any note), lids flying.
    impacts = [s["start_frame"] for s in score["sections"] if s["impact"]]
    for j, root in enumerate(jars):
        mine = sorted((n for n in score["notes"] if n["track"] == "tarro" and n.get("jar") == j), key=lambda n: n["frame"])
        color = JAR_COLORS[j % len(JAR_COLORS)]
        lift = _per_frame(total)
        stretch = _per_frame(total)
        lid = _per_frame(total)
        lid_flip = _per_frame(total)
        spin = _per_frame(total)
        hops = [(n["frame"], n["vel"], n["accent"]) for n in mine]
        # Everyone lands the drop a frame apart, left to right: a ripple rather than a robot.
        hops += [(f0 + j, 2.6, False) for f0 in impacts]
        hops.sort()
        for i, (f0, v, accent) in enumerate(hops):
            gap = (hops[i + 1][0] - f0) if i + 1 < len(hops) else 12
            span = max(4, min(14 if v > 1.5 else 10, gap))  # a hop never overlaps the next one of the same jar
            if accent:
                v *= 1.6
            for f in range(max(0, f0 - 3), min(total, f0 + 16)):
                t = f - f0
                if t < 0:  # anticipation: it crouches before the note
                    stretch[f] = min(stretch[f], -0.07 * min(v, 1.6) * (t + 4) / 3)
                    continue
                if t < span:
                    lift[f] = max(lift[f], HOP * v * math.sin(math.pi * t / span))
                    lid[f] = max(lid[f], 0.03 * v * math.sin(math.pi * min(1.0, t / max(3, span - 1))))
                s = 0.12 * min(v, 1.6) * math.exp(-t / 2.4) * math.cos(t * 0.9)
                if abs(s) > abs(stretch[f]):
                    stretch[f] = s
            if accent or v > 1.5:
                # A full turn (accent) or the lid somersaults off the top (the drop).
                for f in range(f0, min(total, f0 + SPIN + 1)):
                    k = (f - f0) / SPIN
                    e = k * k * (3 - 2 * k)
                    if accent:
                        spin[f] = 2 * math.pi * e
                    else:
                        lid_flip[f] = 2 * math.pi * e
                for f in range(f0 + SPIN + 1, min(total, f0 + SPIN + 2)):
                    spin[f] = lid_flip[f] = 0.0
        bake(root, "delta_location", 2, frames, lift)
        bake(root, "delta_scale", 2, frames, [1 + s for s in stretch])
        for axis in (0, 1):
            bake(root, "delta_scale", axis, frames, [1 - s * 0.5 for s in stretch])
        bake(root, "delta_rotation_euler", 2, frames, spin)
        lid_ctrl = find(root, "lid")
        if lid_ctrl is not None:
            bake(lid_ctrl, "delta_location", 2, frames, lid)
            bake(lid_ctrl, "delta_rotation_euler", 0, frames, lid_flip)
        if not mine:
            continue

        flash = _pulses([(n["frame"], n["vel"]) for n in mine], total, LIGHT_DECAY * fps, attack=1)
        ring = find(root, "think_light")
        if ring is not None:
            _material_copy(ring, color)
            bake(ring, "color", 0, frames, [0.35 + 6.0 * x for x in flash])
        glow = find(root, "think_glow")
        if glow is not None:
            glow.data.color = srgb(color)[:3]
            bake(glow.data, "energy", -1, frames, [0.4 * l + 70 * x for x, l in zip(flash, lit)])
        own = bpy.data.objects.get(f"self_glow.{root.name}")
        if own is not None:
            own.data.color = srgb(color)[:3]
            bake(own.data, "energy", -1, frames, [2.0 * l + 90 * x for x, l in zip(flash, lit)])


def _groove(timeline: dict, jars: list, novato, kicks: list[tuple[int, float]], sec_at: list, total: int) -> None:
    """Everyone moves with the beat: the jars sway and headbang on every kick, the lead nods and bounces in his chair."""
    frames = list(range(total))
    nod = _pulses(kicks, total, 4.0, attack=2)
    energy = [(s["energy"] if s else 0.0) for s in sec_at]
    bar = timeline["score"]["bar_frames"]
    for j, root in enumerate(jars):
        side = 1 if j % 2 else -1
        # Neighbours lean opposite ways, half a beat apart: the row reads as a crowd, not a copy-paste.
        sway = [side * 0.07 * e * math.sin(math.pi * (f / bar * 4 + 0.5 * j)) for f, e in zip(frames, energy)]
        bake(root, "delta_rotation_euler", 1, frames, sway)
        head = find(root, "ctrl_head")
        if head is not None:
            bake(head, "delta_rotation_euler", 0, frames, [0.2 * e * x for e, x in zip(energy, nod)])
    if novato is not None:
        head = find(novato, "ctrl_head")
        if head is not None:
            bake(head, "delta_rotation_euler", 0, frames, [0.16 * e * x for e, x in zip(energy, nod)])
        body = find(novato, "ctrl_body")
        if body is not None:
            bake(body, "delta_location", 2, frames, [-0.025 * e * x for e, x in zip(energy, nod)])


def _faces(timeline: dict, jars: list, sec_at: list, lit: list[float], total: int) -> None:
    """The jars perform: each sings its own notes, grins through the loud parts, squints happily on its accents and
    on the drop, and gasps (wide eyes, round mouth) in the blackout."""
    score = timeline["score"]
    frames = list(range(total))
    impacts = [s["start_frame"] for s in score["sections"] if s["impact"]]
    for j, root in enumerate(jars):
        mine = [n for n in score["notes"] if n["track"] == "tarro" and n.get("jar") == j]
        mouth = ["mouth_smile" if (s and s["energy"] >= 0.5) else "mouth_rest" for s in sec_at]
        eye = [1.0] * total
        brow = [0.0] * total
        for f in frames:
            if not lit[f]:
                mouth[f], eye[f] = "mouth_O", 1.3
        for n in mine:
            hold = max(3, min(n["frames"], 9))
            shape = "mouth_O" if (n["accent"] or n["frames"] >= 6) else "mouth_A"
            for f in range(n["frame"], min(total, n["frame"] + hold)):
                mouth[f] = shape
            for f in range(n["frame"], min(total, n["frame"] + 8)):
                brow[f] = max(brow[f], 0.012 * math.exp(-(f - n["frame"]) / 3))
        happy = [n["frame"] for n in mine if n["accent"]] + impacts
        for f0 in happy:  # ^ ^ : eyes pop wide on the hit, then a happy squint
            for f in range(f0, min(total, f0 + 14)):
                t = f - f0
                eye[f] = 1.35 if t < 2 else min(eye[f], 0.4 + 0.6 * max(0.0, (t - 2) / 12) ** 2)
        for name in ("mouth_rest", "mouth_M", "mouth_E", "mouth_A", "mouth_O", "mouth_smile"):
            obj = find(root, name)
            if obj is None:
                continue
            want = name if find(root, "mouth_smile") or name != "mouth_smile" else None
            keys_f, keys_v, last = [], [], None
            for f, m in zip(frames, mouth):
                m = m if find(root, m) else "mouth_rest"
                hidden = 0.0 if m == want else 1.0
                if hidden != last:
                    keys_f.append(f)
                    keys_v.append(hidden)
                    last = hidden
            bake(obj, "hide_render", -1, keys_f, keys_v, interp="CONSTANT")
        for side in ("L", "R"):
            e = find(root, f"eye_{side}")
            if e is not None:
                bake(e, "delta_scale", 2, frames, eye)
            b = find(root, f"brow_{side}")
            if b is not None:
                bake(b, "delta_location", 2, frames, brow)


def _arms(timeline: dict, jars: list, kicks: list[tuple[int, float]], sec_at: list, total: int) -> None:
    """Hands up for the drop: both stubby arms shoot up on the impact and pump on every kick through the section."""
    score = timeline["score"]
    frames = list(range(total))
    pump = _pulses(kicks, total, 3.5)
    up = [0.0] * total
    for s in score["sections"]:
        if not s["impact"]:
            continue
        for f in range(s["start_frame"], min(total, s["end_frame"])):
            t = f - s["start_frame"]
            up[f] = min(1.0, t / 3) * (1.0 if t < score["bar_frames"] else 0.55)
    if not any(up):
        return
    for root in jars:
        for side, sign in (("L", -1), ("R", 1)):
            arm = find(root, f"ctrl_arm_{side}")
            if arm is None:
                continue
            out = [sign * math.radians(110 * u + 35 * u * min(1.0, p)) for u, p in zip(up, pump)]
            bake(arm, "delta_rotation_euler", 1, frames, out)
            bake(arm, "delta_rotation_euler", 0, frames, [math.radians(-20) * u for u in up])


def _bass_light(timeline: dict, sec_at: list, lit: list[float], fps: int, total: int) -> None:
    """A big light on the floor in front of the band breathes with the bass: the wobble you hear, you see."""
    score = timeline["score"]
    frames = list(range(total))
    bar = score["bar_frames"]
    level = [0.0] * total
    for n in (n for n in score["notes"] if n["track"] == "bajo"):
        for f in range(n["frame"], min(total, n["frame"] + n["frames"])):
            s = sec_at[f]
            t = f - n["frame"]
            if s and s["wobble"]:
                level[f] = 0.5 - 0.5 * math.cos(2 * math.pi * s["wobble"] * (f - s["start_frame"]) / bar)
            else:
                level[f] = 0.35 + 0.65 * math.exp(-t / (0.12 * fps))
    if not any(level):
        return
    data = bpy.data.lights.new("bass_floor", "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = 2.4, 0.8
    data.color = srgb("#8a3dff")[:3]
    obj = bpy.data.objects.new("bass_floor", data)
    bpy.context.scene.collection.objects.link(obj)
    # From above the front of the band, down onto the floor around them (at floor level its edge drew a hard line).
    obj.location = (0.35, -1.3, 1.1)
    obj.rotation_euler = (Vector((0.35, 0.1, 0.0)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    bake(data, "energy", -1, frames, [260 * v * l for v, l in zip(level, lit)])


def _washes(timeline: dict, kicks, snares, sec_at: list, lit: list[float], fps: int, total: int) -> None:
    score = timeline["score"]
    frames = list(range(total))
    bar = score["bar_frames"]
    pump = _pulses(kicks, total, 0.2 * fps)
    impact_hits = [(s["start_frame"], 1.0) for s in score["sections"] if s["impact"]]
    boom = _pulses(impact_hits, total, 0.6 * fps)
    for k, (name, loc, target, cone, peak) in enumerate(WASHES):
        data = bpy.data.lights.new(name, "SPOT")
        data.spot_size = math.radians(cone)
        data.spot_blend = 0.7
        data.shadow_soft_size = 0.3
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        energy, cols = [], [[], [], []]
        for f in frames:
            s = sec_at[f]
            pal = PALETTES[s["palette"]] if s else []
            e = s["energy"] if s else 0.0
            if pal:
                c = srgb(pal[((f - s["start_frame"]) // bar + k) % len(pal)])  # each bar the colours rotate
            else:
                c = (0, 0, 0, 1)
            # A bed that never drops to black, the kick on top, a white-hot flash on the drop.
            energy.append(peak * lit[f] * ((0.18 + 0.5 * e) * (1 if pal else 0) + e * pump[f] * 1.2 + boom[f] * 2.5))
            mix = min(1.0, boom[f])
            for i in range(3):
                cols[i].append(c[i] * (1 - mix) + mix)
        bake(data, "energy", -1, frames, energy)
        for i in range(3):
            bake(data, "color", i, frames, cols[i])
    # The clap: a cold back light snaps the jars' rims out of the dark.
    data = bpy.data.lights.new("snare_rim", "AREA")
    data.size = 1.2
    data.color = srgb("#cfe0ff")[:3]
    obj = bpy.data.objects.new("snare_rim", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0.6, 2.6, 2.0)
    obj.rotation_euler = (Vector((0.5, 0.5, 0.6)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    snap = _pulses(snares, total, 0.12 * fps)
    bake(data, "energy", -1, frames, [180 * x * l for x, l in zip(snap, lit)])


def _fairy(timeline: dict, hats: list[tuple[int, float, bool]], sec_at: list, lit: list[float], fps: int, total: int) -> None:
    """A light runs along the fairy lights: one bulb per hat (three on an open hat), in the section's colours."""
    bulbs = sorted((o for o in bpy.data.objects if o.name.startswith("fairy_") and not o.name.startswith("fairy_wire")
                    and o.name.split("_")[1].isdigit()), key=lambda o: int(o.name.split("_")[1]))
    if not bulbs:
        return
    frames = list(range(total))
    head_hits: list[list[tuple[int, float]]] = [[] for _ in bulbs]
    pos = 0
    for f0, v, open_ in hats:
        for _ in range(3 if open_ else 1):
            head_hits[pos % len(bulbs)].append((f0, v))
            pos += 1
    for i, bulb in enumerate(bulbs):
        mat = _material_copy(bulb, PALETTES["arcoiris"][i % len(PALETTES["arcoiris"])], strength_input="Emission Strength")
        if mat is None:
            continue
        node = mat.node_tree.nodes.get("Principled BSDF")
        if node is None:
            continue
        idx = list(node.inputs).index(node.inputs["Emission Strength"])
        glow = _pulses(head_hits[i], total, 0.25 * fps)
        bake(mat.node_tree, f'nodes["Principled BSDF"].inputs[{idx}].default_value', -1, frames,
             [(0.6 + 60 * g) * l for g, l in zip(glow, lit)])


def _room(lit: list[float], total: int) -> None:
    """The blackout: the set's own lights die with the washes (on top of whatever the mood already baked)."""
    frames = list(range(total))
    if all(lit):
        return
    from bpy_extras import anim_utils

    for name in ROOM_LIGHTS:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "LIGHT":
            continue
        data = obj.data
        fc = None
        if data.animation_data and data.animation_data.action:
            cb = anim_utils.action_get_channelbag_for_slot(data.animation_data.action, data.animation_data.action_slot)
            fc = cb.fcurves.find("energy") if cb else None
        base = [fc.evaluate(f) if fc else data.energy for f in frames]
        bake(data, "energy", -1, frames, [b * l for b, l in zip(base, lit)])


def _haze(lit: list[float], total: int) -> None:
    """Dusty air over the island so the beams draw lines (EEVEE volumetrics); the galaxy dims in the blackout."""
    from lib import primitive

    mat = bpy.data.materials.new("score_haze")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = HAZE_DENSITY
    vol.inputs["Color"].default_value = srgb("#d8d0e0")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(vol.outputs["Volume"], out.inputs["Volume"])
    # Big enough to hold every camera too: a ray that leaves the haze draws a hard edge across the floor.
    box = primitive("cube", "score_haze", (0.2, -0.5, 1.5), (4.5, 4.5, 2.6), None, mat)
    box.visible_shadow = False
    scene = bpy.context.scene
    scene.eevee.volumetric_tile_size = "4"
    scene.eevee.volumetric_samples = 48
    scene.eevee.use_volumetric_shadows = True
    world = scene.world
    for bg in (n for n in world.node_tree.nodes if n.type == "BACKGROUND") if world and not all(lit) else ():
        idx = list(bg.inputs).index(bg.inputs["Strength"])
        base = bg.inputs["Strength"].default_value
        bake(world.node_tree, f'nodes["{bg.name}"].inputs[{idx}].default_value', -1, list(range(total)),
             [base * (0.15 + 0.85 * l) for l in lit])


def _punch(kicks: list[tuple[int, float]], sec_at: list, score: dict, fps: int, total: int) -> None:
    """The cameras push in on every kick (harder the louder the section) and jolt on the drop."""
    frames = list(range(total))
    pulse = _pulses(kicks, total, 3.0)
    boom = _pulses([(s["start_frame"], 1.0) for s in score["sections"] if s["impact"]], total, 0.3 * fps)
    amount = [0.035 * (s["energy"] if s else 0) * p + 0.12 * b for s, p, b in zip(sec_at, pulse, boom)]
    for cam in (o for o in bpy.data.objects if o.type == "CAMERA" and o.parent is None):
        track = next((c for c in cam.constraints if c.type == "TRACK_TO"), None)
        if track is None or track.target is None:
            continue
        d = track.target.matrix_world.translation - cam.location
        if d.length < 1e-4:
            continue
        reach = min(1.0, d.length)  # close-ups move less in metres (they are already close)
        d = d.normalized() * reach
        for i in range(3):
            bake(cam, "delta_location", i, frames, [d[i] * a for a in amount])


def cameras(copies: list) -> dict:
    """band: low and square on to the V of jars on the floor, the lead at the desk behind; band_side: from the left."""
    bpy.context.view_layer.update()
    pts = [r.matrix_world.translation for r in copies]
    mid = sum(pts, Vector()) / len(pts)
    return {
        # Inside the island's front edge (further back the lens sees past the floor into the dark rock).
        "band": dict(loc=mid + Vector((0.0, -1.7, 0.6)), target=mid + Vector((0.0, 0.3, 0.6)), lens=18, fstop=None),
        # From the front-left and above: off the line of either arm of the V, so no jar hides another.
        "band_side": dict(loc=mid + Vector((-0.7, -1.6, 1.0)), end=mid + Vector((-0.45, -1.7, 1.05)),
                          target=mid + Vector((0.15, 0.15, 0.2)), lens=24, fstop=None),
    }


def apply(timeline: dict, jars: list, novato=None) -> None:
    score = timeline.get("score")
    if not score:
        return
    fps, total = timeline["fps"], timeline["total_frames"]
    sec_at = _section_at(score, total)
    lit = _blackout(score, total)
    kicks = [(n["frame"], n["vel"]) for n in score["notes"] if n["track"] == "bombo"]
    snares = [(n["frame"], n["vel"]) for n in score["notes"] if n["track"] == "caja"]
    hats = [(n["frame"], n["vel"], n["open"]) for n in score["notes"] if n["track"] == "hats"]
    _jars(timeline, jars, lit, fps, total)
    _groove(timeline, jars, novato, kicks, sec_at, total)
    _faces(timeline, jars, sec_at, lit, total)
    _arms(timeline, jars, kicks, sec_at, total)
    _bass_light(timeline, sec_at, lit, fps, total)
    _washes(timeline, kicks, snares, sec_at, lit, fps, total)
    _fairy(timeline, hats, sec_at, lit, fps, total)
    _room(lit, total)
    _haze(lit, total)
    _punch(kicks, sec_at, score, fps, total)
