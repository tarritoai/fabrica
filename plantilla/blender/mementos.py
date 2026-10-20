"""Floating memories: small glowing objects that rise around the novato while he remembers.

Script fields (per beat): `memento` makes one appear; `mementos: "away"` dims them and lets them drift
off into the galaxy; `mementos: "keep"` sends one spark of light back into the AI's thinking slit.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from lib import bake, empty, material, primitive, rad, smoothstep, srgb

# Offsets from the novato's left eye (world axes). Measured with world_to_camera_view on medium_novato_low:
# the free space is the window to the right of his head and the strip under the fairy lights.
SLOTS = [Vector((0.22, 0.3, 0.30)), Vector((0.36, 0.3, -0.02)), Vector((-0.16, 0.3, 0.55)), Vector((0.08, 0.3, 0.62))]
SIZE = 2.4
APPEAR = 0.6  # s
AWAY = 3.0  # s
GLOW = "#ffc98a"


def _glow_material(name: str, color: str, strength: float) -> bpy.types.Material:
    """Lit base colour plus a warm emission whose strength is animated (node 'glow')."""
    mat = material(name, color, 0.6)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = srgb(GLOW)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def _digits_image(text: str, w: int = 96, h: int = 40) -> bpy.types.Image:
    """Seven-segment clock face (e.g. '04:00') drawn pixel by pixel."""
    segs = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
    img = bpy.data.images.new(f"clock_{text}", w, h)
    on, off = srgb("#ff6a3d"), srgb("#1a0c08")
    px = [off] * (w * h)

    def rect(x0, y0, x1, y1):
        for y in range(max(0, y0), min(h, y1)):
            for x in range(max(0, x0), min(w, x1)):
                px[y * w + x] = on

    x = 8
    for ch in text:
        if ch == ":":
            rect(x + 1, 12, x + 4, 15)
            rect(x + 1, 25, x + 4, 28)
            x += 8
            continue
        dw, dh, t = 14, 28, 3
        y0 = 6
        s = segs[ch]
        if "a" in s: rect(x, y0 + dh - t, x + dw, y0 + dh)
        if "g" in s: rect(x, y0 + dh // 2 - 1, x + dw, y0 + dh // 2 + 2)
        if "d" in s: rect(x, y0, x + dw, y0 + t)
        if "f" in s: rect(x, y0 + dh // 2, x + t, y0 + dh)
        if "b" in s: rect(x + dw - t, y0 + dh // 2, x + dw, y0 + dh)
        if "e" in s: rect(x, y0, x + t, y0 + dh // 2)
        if "c" in s: rect(x + dw - t, y0, x + dw, y0 + dh // 2)
        x += dw + 6
    img.pixels.foreach_set([c for p in px for c in p])
    img.pack()
    return img


def _cv(root, glow_mat_name: str) -> list:
    paper = _glow_material(f"{glow_mat_name}_paper", "#f2ede2", 0.0)
    ink = material("memento_ink", "#4b4f5c", 0.8)
    photo = material("memento_photo", "#7f9cc4", 0.8)
    mats = [paper]
    for i, ang in enumerate((-16, -4, 9)):
        sheet = empty(f"cv_sheet_{i}", (0.004 * i, 0.002 * i, -0.004 * i), root)
        sheet.rotation_euler = (0, 0, rad(ang))
        primitive("cube", f"cv_paper_{i}", (0, 0, 0), (0.05, 0.001, 0.07), sheet, paper)
        if i == 2:  # only the top sheet shows its layout: photo + text lines
            primitive("cube", f"cv_photo", (-0.028, -0.0012, 0.045), (0.013, 0.0004, 0.016), sheet, photo)
            for j in range(6):
                wdt = 0.03 if j < 2 else 0.04
                primitive("cube", f"cv_line_{j}", (0.008 if j < 2 else 0.0, -0.0012, 0.05 - j * 0.017 - (0.01 if j >= 2 else 0)),
                          (wdt, 0.0004, 0.0018), sheet, ink)
    return mats


def _box(root, glow_mat_name: str) -> list:
    card = _glow_material(f"{glow_mat_name}_card", "#b88654", 0.0)
    tape = material("memento_tape", "#d9c28f", 0.5)
    box = primitive("cube", "box_body", (0, 0, 0), (0.06, 0.045, 0.045), root, card)
    box.modifiers.new("bevel", "BEVEL").width = 0.004
    primitive("cube", "box_tape", (0, 0, 0.0455), (0.0605, 0.012, 0.0008), root, tape)
    primitive("cube", "box_label", (0.0, -0.0455, 0.012), (0.03, 0.0008, 0.012), root, material("memento_label", "#efe9dc", 0.8))
    return [card]


def _clock(root, glow_mat_name: str) -> list:
    case = _glow_material(f"{glow_mat_name}_case", "#22252c", 0.0)
    body = primitive("cube", "clock_body", (0, 0, 0), (0.06, 0.03, 0.032), root, case)
    body.modifiers.new("bevel", "BEVEL").width = 0.006
    face_mat = bpy.data.materials.new("memento_clock_face")
    face_mat.use_nodes = True
    nodes, links = face_mat.node_tree.nodes, face_mat.node_tree.links
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = _digits_image("04:00")
    tex.interpolation = "Closest"
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 4.0
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    face = primitive("plane", "clock_face", (0, -0.0305, 0), (0.05, 0.021, 1), root, face_mat)
    face.rotation_euler = (rad(90), 0, 0)
    return [case, face_mat]


def _mug(root, glow_mat_name: str) -> list:
    m = _glow_material(f"{glow_mat_name}_mug", "#e6dfd2", 0.0)
    primitive("cylinder", "memmug_body", (0, 0, 0), (0.035, 0.035, 0.045), root, m, vertices=14)
    primitive("cylinder", "memmug_coffee", (0, 0, 0.042), (0.031, 0.031, 0.003), root, material("coffee", "#2a160c", 0.2), vertices=14)
    h = primitive("torus", "memmug_handle", (0.04, 0, 0), (1, 1, 1), root, m, major_radius=0.02, minor_radius=0.006, major_segments=10, minor_segments=5)
    h.rotation_euler = (rad(90), 0, 0)
    return [m]


def _halo(name: str, parent, radius: float):
    """Soft warm glow around a memento: an additive emission sphere, strongest where it faces the camera.

    Returns the Value node whose output (glow strength) gets animated.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = "BLENDED"
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    lw = nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(lw.outputs["Facing"], inv.inputs[1])
    pw = nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 4.0
    links.new(inv.outputs[0], pw.inputs[0])
    level = nodes.new("ShaderNodeValue")
    level.name = "glow"
    level.outputs[0].default_value = 0.0
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    links.new(pw.outputs[0], mul.inputs[0])
    links.new(level.outputs[0], mul.inputs[1])
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb(GLOW)
    links.new(mul.outputs[0], emit.inputs["Strength"])
    add = nodes.new("ShaderNodeAddShader")
    links.new(emit.outputs[0], add.inputs[0])
    links.new(nodes.new("ShaderNodeBsdfTransparent").outputs[0], add.inputs[1])
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(add.outputs[0], out.inputs["Surface"])
    halo = primitive("uv_sphere", name, (0, 0, 0), (radius,) * 3, parent, mat, segments=32, ring_count=16)
    halo.data.shade_smooth()
    halo.visible_shadow = False
    return mat.node_tree, level


BUILDERS = {"cv": _cv, "caja": _box, "reloj": _clock, "taza": _mug}
EMISSION = {"cv": 0.45, "caja": 0.3, "reloj": 0.3, "taza": 0.4}  # glow strength on the base material


def _emission_socket(mat):
    if not mat.node_tree or "Principled BSDF" not in mat.node_tree.nodes:
        return None
    return mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]


def build(timeline: dict, head: Vector, ai_slit: Vector | None) -> None:
    fps, total = timeline["fps"], timeline["total_frames"]
    beats = timeline["beats"]
    away = next((b["start_frame"] for b in beats if b.get("mementos") == "away"), None)
    keep = next((b["start_frame"] for b in beats if b.get("mementos") == "keep"), None)
    spawned = [(b["memento"], b["start_frame"]) for b in beats if b.get("memento")]
    if not spawned:
        return
    frames = list(range(0, total))
    for n, (kind, start) in enumerate(spawned):
        root = empty(f"MEMENTO_{n}_{kind}")
        root.rotation_mode = "XYZ"
        mats = BUILDERS[kind](root, f"memento_{n}")
        glow = bpy.data.lights.new(f"memento_glow_{n}", "POINT")
        glow.color = srgb(GLOW)[:3]
        glow.shadow_soft_size = 0.06
        glow_obj = bpy.data.objects.new(f"memento_glow_{n}", glow)
        bpy.context.scene.collection.objects.link(glow_obj)
        glow_obj.parent = root
        glow_obj.location = (0, -0.08, 0)
        halo_tree, _ = _halo(f"memento_halo_{n}", root, 0.1)

        base = head + SLOTS[n % len(SLOTS)]
        # Drift direction: out of the room (back, up and to its own side), into the galaxy.
        side = 1 if SLOTS[n % len(SLOTS)].x > 0 else -1
        drift = Vector((0.6 * side, 3.2, 1.4))
        phase = n * 1.7
        loc, rot, scl, light, emis = [], [], [], [], []
        for f in frames:
            t = f / fps
            a = smoothstep((f - start) / (APPEAR * fps)) if f >= start else 0.0
            pop = 1.0 + 0.12 * math.sin(math.pi * a) if 0 < a < 1 else 1.0
            k = smoothstep((f - away) / (AWAY * fps)) if away is not None and f >= away else 0.0
            bob = Vector((0.006 * math.sin(t * 0.9 + phase), 0, 0.014 * math.sin(t * 1.15 + phase)))
            rise = Vector((0, 0, -0.08 * (1 - a)))  # floats up into place
            loc.append(base + bob + rise + drift * (k ** 1.6))
            rot.append((rad(8 * math.sin(t * 0.7 + phase)), rad(6 * math.sin(t * 0.5 + phase)), rad(-18 * side + 14 * math.sin(t * 0.4 + phase))))
            s = a * pop * (1 - 0.55 * k)
            scl.append(s * SIZE)
            fade = 1 - k
            light.append(0.35 * a * fade * (1 + 0.15 * math.sin(t * 2 + phase)))
            emis.append(EMISSION[kind] * a * fade)
        for i in range(3):
            bake(root, "location", i, frames, [v[i] for v in loc])
            bake(root, "rotation_euler", i, frames, [v[i] for v in rot])
            bake(root, "scale", i, frames, scl)
        bake(glow, "energy", -1, frames, light)
        bake(halo_tree, 'nodes["glow"].outputs[0].default_value', -1, frames, [0.45 * v / EMISSION[kind] for v in emis])
        for m in mats:
            sock = _emission_socket(m)
            if sock is not None:
                bake(m.node_tree, f'nodes["Principled BSDF"].inputs[{list(m.node_tree.nodes["Principled BSDF"].inputs).index(sock)}].default_value', -1, frames, emis)
        vis_end = (away + int(AWAY * fps)) if away is not None else None
        bake(root, "hide_render", -1, [0, start] + ([vis_end] if vis_end else []), [1.0, 0.0] + ([1.0] if vis_end else []), interp="CONSTANT")
        for child in root.children_recursive:
            bake(child, "hide_render", -1, [0, start] + ([vis_end] if vis_end else []), [1.0, 0.0] + ([1.0] if vis_end else []), interp="CONSTANT")

    if keep is not None and ai_slit is not None:
        _spark(keep, fps, total, ai_slit)


def _spark(start: int, fps: int, total: int, target: Vector) -> None:
    """A spark of light comes back from the galaxy and sinks into the AI's thinking slit."""
    mat = material("memento_spark", GLOW, 0.4, emission=12.0)
    spark = primitive("uv_sphere", "MEMENTO_spark", (0, 0, 0), (0.012, 0.012, 0.012), None, mat, segments=10, ring_count=6)
    spark.visible_shadow = False
    halo_tree, _ = _halo("memento_spark_halo", spark, 3.5)
    glow = bpy.data.lights.new("memento_spark_glow", "POINT")
    glow.color = srgb(GLOW)[:3]
    glow.shadow_soft_size = 0.02
    glow_obj = bpy.data.objects.new("memento_spark_glow", glow)
    bpy.context.scene.collection.objects.link(glow_obj)
    glow_obj.parent = spark
    # From deep in the galaxy behind the room (where the memories drifted off), down into the slit.
    origin = target + Vector((0.35, 3.0, 0.45))
    ctrl = target + Vector((0.1, 0.8, 0.28))
    dur = int(1.5 * fps)
    frames = list(range(max(0, start - 1), min(total, start + dur + 6)))
    loc, energy, scl = [], [], []
    for f in frames:
        k = min(1.0, max(0.0, (f - start) / dur))
        e = smoothstep(k)
        # Quadratic bezier: arcs in from the galaxy and drops into the slit.
        p = origin * (1 - e) ** 2 + ctrl * 2 * e * (1 - e) + target * e * e
        loc.append(p)
        on = 0.0 if f < start or f > start + dur else 1.0
        # Dims as it sinks into the slit (a point light touching the glaze would blow it out).
        energy.append(on * 0.25 * (1 - smoothstep((k - 0.7) / 0.3)))
        scl.append(on * 0.022 * (1.0 + 0.3 * math.sin(f * 0.9)) * (1 - 0.6 * smoothstep((k - 0.8) / 0.2)))
    for i in range(3):
        bake(spark, "location", i, frames, [v[i] for v in loc])
        bake(spark, "scale", i, frames, scl)
    bake(glow, "energy", -1, frames, energy)
    bake(halo_tree, 'nodes["glow"].outputs[0].default_value', -1, frames, [1.5 * e / 0.25 if e else 0.0 for e in energy])
