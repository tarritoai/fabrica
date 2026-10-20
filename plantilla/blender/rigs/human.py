"""The human lead (role "humano", internal id novato): faceted low-poly, soft-chibi proportions (~3.5 heads).

Bottle-green hoodie (hood behind the neck, cream drawstrings, kangaroo pocket), dark jeans,
chunky white sneakers, mitten hands with a thumb, a big faceted head with a small triangular
nose, 3-day stubble (vertex tint), thick mobile brows, and spiky brown hair with a crown cowlick
(a separate `hair` object so it can bounce).

Same skeleton as placeholders.capsule (neck pivot, shoulders, elbows), so rigs/arms.py and the
phone poses work unchanged.
"""

from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Euler, Vector

from lib import empty, link, material, primitive, rad, srgb
from rigs.placeholders import FOREARM, MOUTHS, UPPER_ARM

NECK_Z = 1.22  # ctrl_head pivot (rigs/arms.py phone poses assume this)
HEAD_C = 0.2  # head centre above the neck


def _flat(obj) -> None:
    obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))


def _tinted_material(name: str, color: str, roughness: float) -> bpy.types.Material:
    """Base colour multiplied by the mesh's `tone` colour attribute (stubble, fabric variation)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    attr = nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "tone"
    mul = nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = srgb(color)[:3]
    links.new(attr.outputs["Color"], mul.inputs[0])
    links.new(mul.outputs["Vector"], bsdf.inputs["Base Color"])
    return mat


def _head_mesh(name: str, stubble: bool) -> bpy.types.Mesh:
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        # Rounder skull, slightly wider cheeks, flatter face plane.
        v.co = Vector((x * 0.25 * (1 + 0.06 * (1 - abs(z))), y * 0.23 * (0.92 if y < 0 else 1.0), z * 0.245))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    attr = mesh.color_attributes.new("tone", "FLOAT_COLOR", "CORNER")
    rng = random.Random(5)
    for poly in mesh.polygons:
        c = poly.center
        k = 1 + rng.uniform(-0.025, 0.02)
        jaw = stubble and c.z < -0.06 and c.y < 0.08 and abs(c.x) < 0.22
        if jaw:  # 3-day stubble: a cool, darker tint on the jaw
            k *= 0.78
        for li in poly.loop_indices:
            attr.data[li].color = (k, k * (0.97 if jaw else 1), k * (1.0 if jaw else 1), 1.0)
    for poly in mesh.polygons:
        poly.use_smooth = False
    return mesh


def _face(char_id: str, head, cz: float, skin_dark, look: dict | None = None) -> None:
    look = look or {}
    front = -0.205
    eye_mat = material("eye_black", "#050505", 0.25)
    shine = material("eye_shine", "#ffffff", 0.3, emission=3.0)
    tear_mat = material("tear", "#bcd9f5", 0.05, emission=0.45)
    brow_mat = material(f"brow_{char_id}", "#2a170d", 0.85)
    mouth_mat = material("mouth_dark", "#2a0d0d", 0.7)
    es = float(look.get("eye_scale", 1.0))  # smaller eyes leave skin inside round glasses (they read as sunglasses)
    for side, sx in (("L", 1), ("R", -1)):
        eye = primitive("uv_sphere", f"eye_{side}.{char_id}", (sx * 0.092, front + 0.012, cz + 0.0),
                        (0.056 * es, 0.04, 0.064 * es), head, eye_mat, segments=10, ring_count=8)
        primitive("uv_sphere", f"eye_shine_{side}.{char_id}", (0.35, -0.75, 0.4), (0.3, 0.3, 0.3), eye, shine, segments=6, ring_count=4)
        # Wet eyes (beat.tears): a second, lower highlight and a glossy waterline; hidden until animated.
        wet = primitive("uv_sphere", f"eye_wet_{side}.{char_id}", (-0.3, -0.8, -0.45), (0.17, 0.17, 0.12), eye, shine, segments=6, ring_count=4)
        wet.hide_render = True
        line = primitive("uv_sphere", f"eye_waterline_{side}.{char_id}", (0, -0.55, -0.82), (0.8, 0.25, 0.12), eye, tear_mat, segments=10, ring_count=4)
        line.hide_render = True
        brow_size = (0.055, 0.008, 0.009) if look.get("thin_brows") else (0.066, 0.018, 0.019)
        brow = primitive("cube", f"brow_{side}.{char_id}", (sx * 0.095, front - 0.016, cz + 0.098), brow_size, head, brow_mat)
        if look.get("lashes"):
            # Two little flicks on the outer upper edge; children of the eye, so they close with every blink.
            for j, (lx, lz, tilt) in enumerate(((0.62, 0.78, 35), (0.88, 0.5, 55))):
                lash = primitive("cube", f"lash_{side}{j}.{char_id}", (sx * lx, -0.35, lz), (0.26, 0.12, 0.07), eye, eye_mat)
                lash.rotation_euler = (0, rad(-sx * tilt), 0)
        if look.get("blush"):
            cheek = primitive("uv_sphere", f"blush_{side}.{char_id}", (sx * 0.135, front + 0.012, cz - 0.075), (0.035, 0.008, 0.02), head,
                              material(f"blush_{char_id}", look["blush"], 0.9), segments=8, ring_count=4)
            _flat(cheek)
        brow.rotation_euler = (0, rad(sx * -6), 0)
    # One tear (beat.tears = "tear"): a small drop under the left eye (camera right), hidden until it rolls.
    tear = primitive("uv_sphere", f"tear.{char_id}", (0.098, front - 0.004, cz - 0.052), (0.01, 0.007, 0.015), head, tear_mat, segments=8, ring_count=6)
    tear.hide_render = True
    # Small faceted triangular nose.
    nose = primitive("cone", f"nose.{char_id}", (0, front - 0.03, cz - 0.045), (0.028, 0.028, 0.035), head, skin_dark, vertices=3)
    nose.rotation_euler = (rad(-100), 0, rad(180))
    _flat(nose)
    mz, my = cz - 0.11, front + 0.018
    shapes = {
        "mouth_rest": (0.05, 0.01, 0.008),
        "mouth_M": (0.045, 0.01, 0.004),
        "mouth_E": (0.06, 0.01, 0.02),
        "mouth_A": (0.05, 0.01, 0.045),
        "mouth_O": (0.032, 0.01, 0.035),
    }
    for name, size in shapes.items():
        kind = "cube" if name in ("mouth_rest", "mouth_M") else "uv_sphere"
        extra = {"segments": 10, "ring_count": 6} if kind == "uv_sphere" else {}
        m = primitive(kind, f"{name}.{char_id}", (0, my, mz), size, head, mouth_mat, **extra)
        m.hide_render = name != "mouth_rest"
    # Closed-mouth smile (shown at rest when relieved/happy): a thick arc, low-poly.
    curve = bpy.data.curves.new(f"mouth_smile.{char_id}", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.007
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    pts = [math.radians(a) for a in range(205, 340, 22)]
    spline.points.add(len(pts) - 1)
    for pt, a in zip(spline.points, pts):
        pt.co = (0.05 * math.cos(a), 0.0, 0.03 + 0.04 * math.sin(a), 1.0)
    curve.materials.append(mouth_mat)
    smile = bpy.data.objects.new(f"mouth_smile.{char_id}", curve)
    link(smile, head)
    smile.location = (0, my - 0.004, mz + 0.004)
    smile.hide_render = True
    if look.get("glasses"):
        # Round glasses (a student at 3 a.m.): two rings in front of the eyes and a bridge; they move with the head.
        frame = material(f"glasses_{char_id}", look["glasses"] if isinstance(look["glasses"], str) else "#1d1b1a", 0.4)
        for side, sx in (("L", 1), ("R", -1)):
            # Wider than the eyes: a ring of skin between eye and rim (rims hugging big dark eyes read as sunglasses).
            ring = primitive("torus", f"glasses_{side}.{char_id}", (sx * 0.1, front - 0.036, cz + 0.004), (1.0, 1.0, 1.0), head, frame,
                             major_radius=0.074, minor_radius=0.0065, major_segments=18, minor_segments=5)
            ring.rotation_euler = (rad(90), 0, 0)
            arm = primitive("cube", f"glasses_arm_{side}.{char_id}", (sx * 0.2, -0.08, cz + 0.012), (0.006, 0.12, 0.006), head, frame)
            arm.rotation_euler = (0, 0, rad(sx * 8))
        primitive("cube", f"glasses_bridge.{char_id}", (0, front - 0.04, cz + 0.016), (0.03, 0.005, 0.006), head, frame)
    for side, sx in (() if look.get("hair_style") in ("bob", "long") else (("L", 1), ("R", -1))):  # hair covers them
        ear = primitive("uv_sphere", f"ear_{side}.{char_id}", (sx * 0.245, 0.01, cz + 0.0), (0.03, 0.045, 0.06), head, skin_dark, segments=6, ring_count=4)
        _flat(ear)


def _hair(char_id: str, head, cz: float, color: str):
    """Messy spikes swept to one side, plus the crown cowlick (silhouette signature)."""
    mat = material(f"hair_{char_id}", color, 0.9)
    hair = empty(f"hair.{char_id}", (0, 0, cz), head)
    cap = primitive("ico_sphere", f"hair_cap.{char_id}", (0, 0.035, 0.09), (0.262, 0.248, 0.19), hair, mat, subdivisions=1)
    cap.rotation_euler = (rad(-14), 0, 0)
    # Fringe shelf over the forehead.
    fringe = primitive("ico_sphere", f"hair_fringe.{char_id}", (0.03, -0.14, 0.195), (0.2, 0.08, 0.055), hair, mat, subdivisions=1)
    fringe.rotation_euler = (rad(-25), rad(-8), 0)
    rng = random.Random(9)
    spikes = [(-0.12, -0.11, 0.23, -35, 30), (-0.02, -0.13, 0.25, -40, 20), (0.08, -0.11, 0.23, -38, 25), (0.17, -0.06, 0.16, -20, 45),
              (-0.17, -0.02, 0.17, -10, -10), (0.0, 0.0, 0.25, -5, 30), (0.12, 0.08, 0.2, 20, 35), (-0.1, 0.1, 0.19, 25, 15)]
    for i, (x, y, z, tilt_x, tilt_y) in enumerate(spikes):
        h = 0.11 + rng.uniform(-0.015, 0.03)
        sp = primitive("cone", f"hair_spike_{i}.{char_id}", (x, y, z), (0.07, 0.055, h), hair, mat, vertices=4)
        sp.rotation_euler = (rad(tilt_x), rad(tilt_y), rad(rng.uniform(0, 90)))
        _flat(sp)
    # Cowlick: a small swirl of spikes at the crown, pointing back.
    for i in range(3):
        a = i * 2.1
        sp = primitive("cone", f"hair_cowlick_{i}.{char_id}", (0.03 + 0.03 * math.cos(a), 0.15 + 0.03 * math.sin(a), 0.2), (0.035, 0.03, 0.08), hair, mat, vertices=4)
        sp.rotation_euler = (rad(55), rad(25 * math.cos(a)), a)
        _flat(sp)
    _flat(cap)
    _flat(fringe)
    return hair


def _hair_curly(char_id: str, head, cz: float, color: str):
    """A loose mop of curls: lumpy faceted balls over the crown, sides and a heavy fringe."""
    mat = material(f"hair_{char_id}", color, 0.95)
    hair = empty(f"hair.{char_id}", (0, 0, cz), head)
    cap = primitive("ico_sphere", f"hair_cap.{char_id}", (0, 0.03, 0.1), (0.27, 0.26, 0.2), hair, mat, subdivisions=1)
    _flat(cap)
    rng = random.Random(21)
    n = 0
    for ring_z, ring_r, count in ((0.27, 0.12, 6), (0.21, 0.22, 11), (0.12, 0.26, 12), (0.02, 0.262, 8)):
        for i in range(count):
            a = (i + rng.uniform(-0.25, 0.25)) / count * 2 * math.pi
            x, y = ring_r * math.cos(a), ring_r * math.sin(a)
            if ring_z < 0.15 and y < 0.02:
                continue  # below the fringe only the sides behind the ears: nothing near the eyes
            r = rng.uniform(0.055, 0.075)
            c = primitive("ico_sphere", f"hair_curl_{n}.{char_id}", (x, y + 0.02, ring_z + rng.uniform(-0.02, 0.02)), (r, r, r * 0.9), hair, mat, subdivisions=1)
            c.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
            _flat(c)
            n += 1
    # Heavy curly fringe over the forehead.
    for i, x in enumerate((-0.13, -0.05, 0.03, 0.11)):
        r = rng.uniform(0.06, 0.072)
        c = primitive("ico_sphere", f"hair_fringe_{i}.{char_id}", (x, -0.16, 0.225 + rng.uniform(-0.01, 0.01)), (r * 0.9, r * 0.8, r * 0.7), hair, mat, subdivisions=1)
        _flat(c)
    return hair


def _hair_long(char_id: str, head, cz: float, color: str, style: str):
    """Longer hair in the same faceted style. style: long (falls past the shoulders, side-swept fringe),
    bun (messy bun on top, a couple of loose strands: 3 a.m. in bed), bob (chin-length with blunt bangs)."""
    mat = material(f"hair_{char_id}", color, 0.9)
    hair = empty(f"hair.{char_id}", (0, 0, cz), head)
    rng = random.Random(33)

    def chunk(name, loc, scale, rot=(0, 0, 0)):
        c = primitive("ico_sphere", f"hair_{name}.{char_id}", loc, scale, hair, mat, subdivisions=1)
        c.rotation_euler = tuple(rad(a) for a in rot)
        _flat(c)
        return c

    chunk("cap", (0, 0.025, 0.085), (0.272, 0.26, 0.205), (-12, 0, 0))
    if style == "bob":
        chunk("bangs", (0, -0.15, 0.19), (0.22, 0.075, 0.07), (-18, 0, 0))
        for side, sx in (("L", 1), ("R", -1)):  # rounded sides to the chin, clear of the eyes
            chunk(f"side_{side}", (sx * 0.215, 0.0, -0.03), (0.075, 0.2, 0.2), (0, sx * 6, 0))
        chunk("back", (0, 0.11, -0.02), (0.25, 0.14, 0.21))
        for side, sx in (("L", 1), ("R", -1)):  # temples: no skin showing between the crown and the sides
            chunk(f"temple_{side}", (sx * 0.2, -0.04, 0.1), (0.085, 0.15, 0.13), (0, sx * 10, 0))
        return hair
    # Side-swept fringe (long, bun): two soft chunks from the parting, leaving the eyes clear.
    chunk("fringe_a", (0.06, -0.15, 0.2), (0.17, 0.07, 0.06), (-22, -10, 14))
    chunk("fringe_b", (-0.13, -0.13, 0.17), (0.09, 0.06, 0.07), (-20, 12, -20))
    if style == "bun":
        chunk("bun", (0, 0.14, 0.285), (0.095, 0.09, 0.085), (rng.uniform(0, 30), rng.uniform(0, 30), 0))
        chunk("bun_tie", (0, 0.11, 0.24), (0.06, 0.055, 0.025), (-30, 0, 0))
        for side, sx in (("L", 1), ("R", -1)):  # hair pulled back over the sides (no bare scalp)
            chunk(f"pulled_{side}", (sx * 0.19, 0.05, 0.1), (0.1, 0.21, 0.17), (0, sx * 8, 0))
        chunk("crown", (0, 0.08, 0.17), (0.23, 0.2, 0.13))
        for side, sx in (("L", 1), ("R", -1)):  # loose strands by the ears
            chunk(f"strand_{side}", (sx * 0.2, -0.07, -0.05), (0.025, 0.03, 0.11), (8, sx * 10, 0))
        chunk("nape", (0, 0.13, -0.04), (0.2, 0.11, 0.12))
        return hair
    # long: curtains framing the face down to the shoulders, a mass behind.
    for side, sx in (("L", 1), ("R", -1)):
        chunk(f"curtain_{side}", (sx * 0.215, -0.03, -0.12), (0.07, 0.11, 0.3), (6, sx * 4, 0))
        chunk(f"curtain_tip_{side}", (sx * 0.2, -0.0, -0.36), (0.065, 0.1, 0.09))
    chunk("back", (0, 0.12, -0.15), (0.26, 0.13, 0.36))
    return hair


def _seated_legs(char_id: str, body, jeans, shoe, sole) -> None:
    """Sitting on a sofa: thighs forward from the hips, shins down to the floor (seat height ~0.42 m)."""
    for side, x in (("L", 0.13), ("R", -0.13)):
        thigh = primitive("cylinder", f"leg_thigh_{side}.{char_id}", (x, -0.2, 0.5), (0.1, 0.1, 0.21), body, jeans, vertices=7)
        thigh.rotation_euler = (rad(90), 0, 0)
        _flat(thigh)
        primitive("uv_sphere", f"leg_knee_{side}.{char_id}", (x, -0.41, 0.5), (0.1, 0.1, 0.1), body, jeans, segments=7, ring_count=4)
        shin = primitive("cylinder", f"leg_shin_{side}.{char_id}", (x, -0.43, 0.28), (0.088, 0.088, 0.22), body, jeans, vertices=7)
        _flat(shin)
        sh = primitive("cube", f"leg_shoe_{side}.{char_id}", (x, -0.48, 0.055), (0.08, 0.13, 0.05), body, shoe)
        sh.modifiers.new("bevel", "BEVEL").width = 0.02
        primitive("cube", f"leg_sole_{side}.{char_id}", (x, -0.48, 0.012), (0.085, 0.135, 0.014), body, sole)


def build(char_id: str, meta: dict) -> bpy.types.Object:
    p = meta.get("human", {})
    skin_c = p.get("skin", "#d99a72")
    root = empty(f"CHAR_{char_id}")
    body = empty(f"ctrl_body.{char_id}", parent=root)

    skin = _tinted_material(f"skin_{char_id}", skin_c, 0.75)
    skin_plain = material(f"skin_plain_{char_id}", skin_c, 0.75)
    skin_dark = material(f"skin_dark_{char_id}", p.get("skin_dark", "#c4835e"), 0.75)
    hoodie = material(f"hoodie_{char_id}", p.get("hoodie", "#2f5d46"), 0.9)
    hoodie_dark = material(f"hoodie_dark_{char_id}", p.get("hoodie_dark", "#244a37"), 0.9)
    string = material("drawstring", "#efe3c8", 0.8)
    jeans = material(f"jeans_{char_id}", p.get("jeans", "#27324a"), 0.9)
    shoe = material("sneaker", "#f1efe9", 0.7)
    sole = material("sneaker_sole", "#cfcac0", 0.8)

    # Legs + chunky sneakers (or sitting on a sofa).
    seated = p.get("pose") == "sofa"
    if seated:
        _seated_legs(char_id, body, jeans, shoe, sole)
    for side, x in (() if seated else (("L", 0.12), ("R", -0.12))):
        leg = primitive("cylinder", f"leg_{side}.{char_id}", (x, 0, 0.3), (0.09, 0.095, 0.25), body, jeans, vertices=7)
        _flat(leg)
        sh = primitive("cube", f"leg_shoe_{side}.{char_id}", (x, -0.04, 0.055), (0.08, 0.13, 0.05), body, shoe)
        sh.modifiers.new("bevel", "BEVEL").width = 0.02
        primitive("cube", f"leg_sole_{side}.{char_id}", (x, -0.04, 0.012), (0.085, 0.135, 0.014), body, sole)

    # Hoodie torso (slightly wider at the chest), pocket, hood behind the neck, drawstrings.
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.27, radius2=0.32, depth=0.66)
    for v in bm.verts:
        v.co.y *= 0.74
        v.co.z += 0.86
        if v.co.z > 1.0:  # rounder shoulders
            v.co.x *= 0.92
    torso_mesh = bpy.data.meshes.new(f"torso.{char_id}")
    bm.to_mesh(torso_mesh)
    bm.free()
    torso = bpy.data.objects.new(f"torso.{char_id}", torso_mesh)
    link(torso, body, hoodie)
    _flat(torso)
    primitive("uv_sphere", f"shoulders.{char_id}", (0, 0, 1.17), (0.3, 0.225, 0.1), body, hoodie, segments=8, ring_count=4)
    primitive("cube", f"pocket.{char_id}", (0, -0.222, 0.72), (0.17, 0.012, 0.09), body, hoodie_dark)
    primitive("cube", f"waistband.{char_id}", (0, 0, 0.55), (0.305, 0.228, 0.03), body, hoodie_dark).data.polygons.foreach_set("use_smooth", [False] * 6)
    hood = primitive("torus", f"hood.{char_id}", (0, 0.06, 1.24), (1.0, 1.0, 1.6), body, hoodie, major_radius=0.15, minor_radius=0.065, major_segments=10, minor_segments=5)
    hood.rotation_euler = (rad(-20), 0, 0)
    _flat(hood)
    for side, x in (("L", 0.05), ("R", -0.05)):
        s = primitive("cylinder", f"drawstring_{side}.{char_id}", (x, -0.215, 1.04), (0.008, 0.008, 0.09), body, string, vertices=5)
        s.rotation_euler = (rad(-6), 0, 0)
        primitive("cylinder", f"aglet_{side}.{char_id}", (x, -0.222, 0.945), (0.011, 0.011, 0.012), body, string, vertices=5)

    if p.get("apron"):
        # Work apron (café, bakery, kitchen): a bib over the chest, a strap round the neck, ties at the waist.
        apron = material(f"apron_{char_id}", p["apron"], 0.95)
        bib = primitive("cube", f"apron_bib.{char_id}", (0, -0.232, 0.96), (0.17, 0.01, 0.13), body, apron)
        bib.rotation_euler = (rad(-4), 0, 0)
        skirt = primitive("cube", f"apron_skirt.{char_id}", (0, -0.238, 0.62), (0.26, 0.012, 0.22), body, apron)
        skirt.rotation_euler = (rad(4), 0, 0)
        primitive("cube", f"apron_pocket.{char_id}", (0, -0.252, 0.66), (0.12, 0.004, 0.06), body,
                  material(f"apron_seam_{char_id}", p.get("apron_dark", "#3b3b3b"), 0.95))
        for side, x in (("L", 0.13), ("R", -0.13)):
            strap = primitive("cube", f"apron_strap_{side}.{char_id}", (x * 0.75, -0.16, 1.14), (0.012, 0.09, 0.012), body, apron)
            strap.rotation_euler = (rad(-35), 0, rad(-x * 60))

    # Arms: sleeves + cuff + mitten hand with thumb (same pivots as the capsule rig).
    for side, x in (("L", 0.31), ("R", -0.31)):
        shoulder = empty(f"ctrl_arm_{side}.{char_id}", (x, 0, 1.13), body)
        shoulder.rotation_mode = "QUATERNION"
        up = primitive("cylinder", f"arm_{side}.{char_id}", (0, 0, -UPPER_ARM / 2), (0.068, 0.068, UPPER_ARM / 2 + 0.03), shoulder, hoodie, vertices=7)
        _flat(up)
        elbow = empty(f"ctrl_forearm_{side}.{char_id}", (0, 0, -UPPER_ARM), shoulder)
        elbow.rotation_mode = "QUATERNION"
        primitive("uv_sphere", f"elbow_{side}.{char_id}", (0, 0, 0), (0.066, 0.066, 0.066), elbow, hoodie, segments=7, ring_count=4)
        fa = primitive("cylinder", f"forearm_{side}.{char_id}", (0, 0, -FOREARM / 2 + 0.01), (0.062, 0.062, FOREARM / 2), elbow, hoodie, vertices=7)
        _flat(fa)
        primitive("cylinder", f"cuff_{side}.{char_id}", (0, 0, -FOREARM + 0.015), (0.058, 0.058, 0.018), elbow, hoodie_dark, vertices=7)
        hand = primitive("cube", f"hand_{side}.{char_id}", (0, 0, -FOREARM - 0.035), (0.045, 0.032, 0.05), elbow, skin_plain)
        hand.modifiers.new("bevel", "BEVEL").width = 0.012
        thumb = primitive("cube", f"thumb_{side}.{char_id}", (0.0, -0.035, -FOREARM - 0.02), (0.016, 0.018, 0.028), elbow, skin_plain)
        thumb.rotation_euler = (rad(20), 0, 0)

    # Neck + head.
    primitive("cylinder", f"neck.{char_id}", (0, 0, 1.24), (0.08, 0.08, 0.05), body, skin_plain, vertices=7)
    head = empty(f"ctrl_head.{char_id}", (0, 0, NECK_Z), body)
    head_obj = bpy.data.objects.new(f"head.{char_id}", _head_mesh(f"head.{char_id}", p.get("stubble", True)))
    link(head_obj, head, skin)
    head_obj.location = (0, 0, HEAD_C)
    _face(char_id, head, HEAD_C, skin_dark, p)
    style = p.get("hair_style")
    if style in ("long", "bun", "bob"):
        _hair_long(char_id, head, HEAD_C, p.get("hair", "#3a2414"), style)
    else:
        (_hair_curly if style == "curly" else _hair)(char_id, head, HEAD_C, p.get("hair", "#3a2414"))
    return root
