"""Claude as a small hand-made terracotta figure ("terrón de barro cocido").

Signature details (what makes it ours and recognisable):
  - a cream glaze dipped over the top that drips down the sides (glossy over matte clay);
  - the potter's thumbprint pressed into one cheek;
  - a recessed amber "thinking light" on top;
  - a tiny ceramic cup always by its side;
  - a mouth that only exists while talking, and a slow blink (animate.py).

Two shape variants (character.json "ceramic.variant"):
  loaf  - soft bread-loaf block, domed top, capsule eyes, two stubby legs
  brick - near-square block, flat top, square eyes, four square legs

Satisfies the rig interface (placeholders.py docstring). Extra controls used by animate.py:
    think_light  (its object colour R drives the emission: 0 = off, 1 = normal glow)
    ctrl_arm_L / ctrl_arm_R  (stubby arms; animate.py rotates them for gestures)
"""

from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from lib import empty, link, material, primitive, rad, srgb

VARIANTS = {
    "loaf": dict(W=0.54, D=0.4, H=0.46, taper=0.08, round=0.5, crown=0.07, jitter=0.007, eyes="capsule", legs=2),
    "brick": dict(W=0.52, D=0.4, H=0.46, taper=0.0, round=0.16, crown=0.0, jitter=0.005, eyes="square", legs=4),
}
LEG_H = 0.035
LID_AT = 0.86  # the jar mouth: the body is cut flat at this fraction of its height
LID_DOME = 0.075  # height of the lid dome
LID_GAP = 0.02  # resting slit between body and lid (where the thinking light leaks out)


def _cut_top(bm, lid_z: float) -> tuple[float, float]:
    """Slice the body flat at the jar mouth and close it; returns the mouth's half extents (x, y)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, lid_z), plane_no=(0, 0, 1), clear_outer=True)
    rim = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    bmesh.ops.holes_fill(bm, edges=rim, sides=0)
    top = [v for v in bm.verts if abs(v.co.z - lid_z) < 1e-4]
    return max(abs(v.co.x) for v in top), max(abs(v.co.y) for v in top)


def _lid(char_id: str, head, ex: float, ey: float, lid_z: float, glaze, clay_dark, think_mat):
    """Jar mouth (clay lip + inner glow) and a low glazed dome lid with a knob.

    `lid.<id>` (an empty at the rim) is the control animate.py lifts, tilts and rattles.
    """
    primitive("cylinder", f"jar_lip.{char_id}", (0, 0, lid_z - 0.006), (ex * 1.03, ey * 1.03, 0.014), head, clay_dark, vertices=28)
    glow_ring = primitive("cylinder", f"think_light.{char_id}", (0, 0, lid_z + 0.012), (ex * 0.93, ey * 0.93, 0.014), head, think_mat, vertices=28)
    ctrl = empty(f"lid.{char_id}", (0, 0, lid_z + LID_GAP), head)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=12, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for v in bm.verts:
        v.co = Vector((v.co.x * ex * 1.07, v.co.y * ey * 1.07, v.co.z * LID_DOME))
    mesh = bpy.data.meshes.new(f"lid_shell.{char_id}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"lid_shell.{char_id}", mesh)
    link(obj, ctrl, glaze)
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    # A rim band so the lid reads as a separate, thick piece.
    primitive("cylinder", f"lid_rim.{char_id}", (0, 0, 0.004), (ex * 1.075, ey * 1.075, 0.01), ctrl, glaze, vertices=28)
    primitive("cylinder", f"lid_knob_neck.{char_id}", (0, 0, LID_DOME + 0.008), (0.026, 0.026, 0.016), ctrl, glaze, vertices=12)
    primitive("uv_sphere", f"lid_knob.{char_id}", (0, 0, LID_DOME + 0.04), (0.05, 0.05, 0.035), ctrl, glaze, segments=12, ring_count=7)
    return glow_ring


def _kintsugi(head, bvh: BVHTree, v: dict, gold) -> None:
    """A crack repaired with gold running down one front corner: something broke and was mended."""
    W, D, H = v["W"], v["D"], v["H"]
    rng = random.Random(31)

    def crack(name, fx, fz, steps, drift, width):
        prev = None
        for i in range(steps):
            point, normal = _surface(bvh, W * fx, H * fz, D)
            point = point + normal * 0.002
            if prev is not None:
                d = point - prev
                seg = primitive("cylinder", f"{name}_{i}", tuple((point + prev) / 2), (width, width, d.length / 2 + 0.002), head, gold, vertices=5)
                seg.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            prev = point
            fx += rng.uniform(-0.035, 0.035) + drift
            fz -= rng.uniform(0.035, 0.075)
        return fx, fz

    # Main crack from the rim down the front corner, plus a short branch.
    crack("kintsugi", 0.34, LID_AT - 0.01, 9, 0.006, 0.0045)
    crack("kintsugi_branch", 0.37, LID_AT - 0.2, 3, -0.02, 0.0032)


def _shape_bmesh(v: dict, cuts: int, seed: int) -> bmesh.types.BMesh:
    W, D, H = v["W"], v["D"], v["H"]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    rng = random.Random(seed)
    for vert in bm.verts:
        q = vert.co.copy()
        q /= max(abs(q.x), abs(q.y), abs(q.z))
        p = q.lerp(q.normalized() * 1.18, v["round"])
        p = Vector((max(-1.0, min(1.0, c)) for c in p))
        t = (p.z + 1) / 2
        widen = 1 - v["taper"] / 2 + v["taper"] * t
        crown = v["crown"] * H * max(0.0, p.z) * (1 - p.x * p.x)
        co = Vector((p.x * W / 2 * widen, p.y * D / 2 * widen, (p.z + 1) / 2 * H + crown))
        if co.z < 0.04 * H:
            co.z = 0.0
        co += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * v["jitter"] * H
        vert.co = co
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    return bm


def _to_mesh(bm: bmesh.types.BMesh, name: str, tone_seed: int | None = None) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    for poly in mesh.polygons:
        poly.use_smooth = False
    if tone_seed is not None:  # per-face tone variation, like real fired clay
        rng = random.Random(tone_seed)
        attr = mesh.color_attributes.new("tone", "FLOAT_COLOR", "CORNER")
        for poly in mesh.polygons:
            k = 1 + rng.uniform(-0.06, 0.05)
            for li in poly.loop_indices:
                attr.data[li].color = (k, k, k, 1.0)
    return mesh


def _glaze_bmesh(v: dict, seed: int) -> bmesh.types.BMesh:
    """The top of a finer copy of the body, pushed out a little, with an irregular dripping edge."""
    H = v["H"]
    bm = _shape_bmesh(v, 14, seed)
    bm.normal_update()
    for vert in bm.verts:
        vert.co += vert.normal * 0.005
    rng = random.Random(seed + 1)
    front = -math.pi / 2
    # Two long drips frame the face at its upper corners; the rest run down the sides and back.
    drips = [(front + 0.62, 0.42), (front - 0.66, 0.3), (front + 0.3, 0.1), (front - 0.25, 0.07),
             (front + 1.5, 0.36), (front - 1.6, 0.4), (front + 2.3, 0.26),
             (math.pi / 2 + 0.4, 0.3), (math.pi / 2 - 0.5, 0.2), (front - 2.5, 0.28)]
    drips += [(rng.uniform(-math.pi, math.pi), rng.uniform(0.06, 0.14)) for _ in range(4)]

    def line(co: Vector) -> float:
        theta = math.atan2(co.y, co.x)
        z = 0.86 * H + 0.03 * H * math.sin(theta * 7 + seed) + 0.015 * H * math.sin(theta * 13)
        for a, depth in drips:
            d = abs((theta - a + math.pi) % (2 * math.pi) - math.pi)
            if abs(a - front) < 0.5 and depth > 0.12:  # eyes and brows stay clear: only short drips there
                continue
            z -= depth * H * max(0.0, 1 - d / 0.12) ** 0.6
        return z

    doomed = [f for f in bm.faces if f.calc_center_median().z < line(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    return bm


def _clay_material(name: str, color: str, roughness: float) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    attr = nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "tone"
    mul = nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = srgb(color)[:3]
    links.new(attr.outputs["Color"], mul.inputs[0])
    links.new(mul.outputs["Vector"], bsdf.inputs["Base Color"])
    return mat


def _glaze_material(color: str) -> bpy.types.Material:
    mat = bpy.data.materials.new("claude_glaze")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.15
    bsdf.inputs["Subsurface Weight"].default_value = 0.15
    return mat


def _think_material() -> bpy.types.Material:
    """Amber glow whose strength follows the object's colour (animated per frame)."""
    mat = bpy.data.materials.new("claude_think")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    info = nodes.new("ShaderNodeObjectInfo")
    sep = nodes.new("ShaderNodeSeparateColor")
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 7.0
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb("#ffb45a")
    base = nodes.new("ShaderNodeBsdfPrincipled")
    base.inputs["Base Color"].default_value = srgb("#5a2a14")
    base.inputs["Roughness"].default_value = 0.4
    add = nodes.new("ShaderNodeAddShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(info.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Red"], mul.inputs[0])
    links.new(mul.outputs["Value"], emit.inputs["Strength"])
    links.new(base.outputs["BSDF"], add.inputs[0])
    links.new(emit.outputs["Emission"], add.inputs[1])
    links.new(add.outputs["Shader"], out.inputs["Surface"])
    return mat


def _surface(bvh: BVHTree, x: float, z: float, D: float) -> tuple[Vector, Vector]:
    """Point and normal on the front (-Y) of the body at (x, z)."""
    hit, normal, _, _ = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    if hit is None:
        return Vector((x, -D / 2, z)), Vector((0, -1, 0))
    return hit, normal


def _thumbprint(head, bvh: BVHTree, v: dict, x: float, z: float, mat) -> None:
    """Concentric oval grooves, like a thumb pressed into wet clay."""
    point, normal = _surface(bvh, x, z, v["D"])
    rot = normal.to_track_quat("Z", "Y").to_euler()
    for i, r in enumerate((0.009, 0.015, 0.021, 0.027)):
        ring = primitive("torus", f"thumbprint_{i}", tuple(point + normal * 0.0008), (1.0, 1.35, 0.25), head, mat,
                         major_radius=r, minor_radius=0.0018, major_segments=20, minor_segments=4)
        ring.rotation_euler = rot


def _tiny_cup(parent, location, clay, glaze) -> None:
    cup = empty("claude_cup", location, parent)
    primitive("cylinder", "claude_cup_body", (0, 0, 0.03), (0.034, 0.034, 0.03), cup, clay, vertices=10)
    primitive("cylinder", "claude_cup_glaze", (0, 0, 0.045), (0.036, 0.036, 0.017), cup, glaze, vertices=10)
    primitive("cylinder", "claude_cup_coffee", (0, 0, 0.0615), (0.03, 0.03, 0.001), cup, material("coffee", "#2a160c", 0.2), vertices=10)
    handle = primitive("torus", "claude_cup_handle", (0.04, 0, 0.032), (1, 1, 1), cup, glaze,
                       major_radius=0.014, minor_radius=0.005, major_segments=8, minor_segments=4)
    handle.rotation_euler = (rad(90), 0, 0)


def build(char_id: str, meta: dict) -> bpy.types.Object:
    p = meta.get("ceramic", {})
    v = VARIANTS[p.get("variant", "loaf")]
    W, D, H = v["W"], v["D"], v["H"]
    seed = p.get("seed", 11)

    root = empty(f"CHAR_{char_id}")
    body = empty(f"ctrl_body.{char_id}", parent=root)
    clay = _clay_material(f"clay_{char_id}", p.get("color", "#a84f2c"), 0.85)
    clay_dark = material(f"clay_dark_{char_id}", p.get("dark", "#6e2c1a"), 0.8)
    clay_plain = material(f"clay_plain_{char_id}", p.get("color", "#a84f2c"), 0.85)
    groove = material(f"clay_groove_{char_id}", p.get("groove", "#7d3720"), 0.9)
    glaze = _glaze_material(p.get("glaze", "#efe2c8"))
    eye_mat = material(f"eye_{char_id}", "#17110f", 0.2)
    shine = material("eye_shine", "#ffffff", 0.3, emission=3.0)
    mouth_mat = material(f"mouth_{char_id}", "#2a120a", 0.7)

    # Legs stay put; everything above them leans and turns as one piece (ctrl_head).
    legs = [(0.11, 0.0), (-0.11, 0.0)] if v["legs"] == 2 else [(0.16, -0.1), (-0.16, -0.1), (0.16, 0.1), (-0.16, 0.1)]
    for i, (x, y) in enumerate(legs):
        if v["legs"] == 2:
            leg = primitive("cylinder", f"leg_{i}.{char_id}", (x, y, LEG_H / 2 + 0.005), (0.06, 0.065, LEG_H / 2 + 0.012), body, clay_plain, vertices=7)
        else:
            leg = primitive("cube", f"leg_{i}.{char_id}", (x, y, LEG_H / 2 + 0.005), (0.04, 0.04, LEG_H / 2 + 0.012), body, clay_plain)
        leg.data.polygons.foreach_set("use_smooth", [False] * len(leg.data.polygons))
    head = empty(f"ctrl_head.{char_id}", (0, 0, LEG_H), body)

    bm = _shape_bmesh(v, 2, seed)
    lid_z = H * LID_AT
    use_lid = p.get("top", "lid") == "lid"
    bvh_full = BVHTree.FromBMesh(bm)  # face features are placed on the uncut shape
    if use_lid:
        ex, ey = _cut_top(bm, lid_z)
    shell = bpy.data.objects.new(f"clay_body.{char_id}", _to_mesh(bm, f"clay_body.{char_id}", seed))
    link(shell, head, clay)
    bvh = bvh_full
    bm.free()

    if not use_lid:
        gbm = _glaze_bmesh(v, seed)
        glaze_obj = bpy.data.objects.new(f"glaze.{char_id}", _to_mesh(gbm, f"glaze.{char_id}"))
        glaze_obj.data.polygons.foreach_set("use_smooth", [True] * len(glaze_obj.data.polygons))
        gbm.free()
        link(glaze_obj, head, glaze)
        glaze_obj.modifiers.new("thickness", "SOLIDIFY").thickness = 0.009
    _kintsugi(head, bvh, v, material("kintsugi_gold", "#d9a53c", 0.3, emission=0.6))

    eye_z, eye_dx = H * 0.55, W * 0.17
    for side, sx in (("L", 1), ("R", -1)):
        surf, _ = _surface(bvh, sx * eye_dx, eye_z, D)
        if v["eyes"] == "capsule":
            eye = primitive("uv_sphere", f"eye_{side}.{char_id}", tuple(surf + Vector((0, -0.004, 0))),
                            (0.038, 0.024, 0.07), head, eye_mat, segments=12, ring_count=8)
            primitive("uv_sphere", f"eye_shine_{side}.{char_id}", (0.35, -0.8, 0.45), (0.28, 0.28, 0.2), eye, shine,
                      segments=6, ring_count=4)
        else:
            eye = primitive("cube", f"eye_{side}.{char_id}", tuple(surf + Vector((0, -0.006, 0))), (0.036, 0.012, 0.042), head, eye_mat)
            eye.modifiers.new("bevel", "BEVEL").width = 0.006
            primitive("cube", f"eye_shine_{side}.{char_id}", (0.4, -1.0, 0.45), (0.22, 0.2, 0.2), eye, shine)
        bsurf, _ = _surface(bvh, sx * eye_dx * 1.05, eye_z + 0.1, D)
        brow = primitive("cube", f"brow_{side}.{char_id}", tuple(bsurf + Vector((0, -0.016, 0))), (0.05, 0.009, 0.014), head, clay_dark)
        brow.modifiers.new("bevel", "BEVEL").width = 0.004

    _thumbprint(head, bvh, v, -W * 0.27, H * 0.3, groove)

    # Mouth: a thin slot that only exists while talking (mouth_rest is empty space).
    msurf = _surface(bvh, 0.0, H * 0.33, D)[0] + Vector((0, -0.003, 0))
    shapes = {
        "mouth_rest": (0.0001, 0.0001, 0.0001),
        "mouth_M": (0.035, 0.006, 0.004),
        "mouth_E": (0.045, 0.006, 0.01),
        "mouth_A": (0.038, 0.006, 0.022),
        "mouth_O": (0.02, 0.006, 0.02),
    }
    for name, size in shapes.items():
        kind = "cube" if name in ("mouth_rest", "mouth_M") or v["eyes"] == "square" else "uv_sphere"
        extra = {"segments": 10, "ring_count": 6} if kind == "uv_sphere" else {}
        m = primitive(kind, f"{name}.{char_id}", tuple(msurf), size, head, mouth_mat, **extra)
        m.hide_render = name != "mouth_rest"

    if use_lid:
        ring = _lid(char_id, head, ex, ey, lid_z, glaze, clay_dark, _think_material())
    else:
        ring = primitive("cylinder", f"think_light.{char_id}", (0, 0, H + 0.01), (0.04, 0.04, 0.004), head, _think_material(), vertices=14)
    ring.color = (0.35, 0, 0, 1)
    glow = bpy.data.lights.new(f"think_glow.{char_id}", "POINT")
    glow.color = srgb("#ffb45a")[:3]
    glow.energy = 0.0
    glow.shadow_soft_size = 0.05
    glow_obj = bpy.data.objects.new(f"think_glow.{char_id}", glow)
    link(glow_obj, head)
    glow_obj.location = (0, -D * 0.6, lid_z + 0.01)

    # Stubby arms, tucked against the sides (pivot at the shoulder; animate.py lifts them).
    for side, sx in (("L", 1), ("R", -1)):
        pivot = empty(f"ctrl_arm_{side}.{char_id}", (sx * (W / 2 + 0.005), 0.0, H * 0.5), head)
        if v["eyes"] == "capsule":
            arm = primitive("uv_sphere", f"arm_{side}.{char_id}", (sx * 0.014, 0, -0.05), (0.032, 0.036, 0.072), pivot, clay_plain, segments=8, ring_count=5)
        else:
            arm = primitive("cube", f"arm_{side}.{char_id}", (sx * 0.014, 0, -0.05), (0.026, 0.03, 0.06), pivot, clay_plain)
        arm.data.polygons.foreach_set("use_smooth", [False] * len(arm.data.polygons))

    if p.get("cup", True):  # on the desk, not on Claude: it must not lean or breathe with the body
        _tiny_cup(root, (W / 2 + 0.11, -0.06, 0), clay_plain, glaze)
    return root
