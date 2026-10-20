"""Objects with a face ("objeto con cara"): a desk lamp, a moka pot, a mug, a shoe... built from data.

personaje.json -> "placeholder": {"shape": "object"} and an "object" block (everything optional except "form"):

    "object": {
      "form": "lampara" | "cafetera" | "taza" | "olla" | "cajita" | "zapatilla" | "bloque" | "cilindro" | "bola" | "cono",
      "size": 0.6,                    height in metres (things on a desk are scaled down by the set)
      "width": 1.0, "depth": 1.0,     proportions (multipliers of the form's own)
      "sides": 16,                    facets of round shapes (8 = octagonal, like a moka pot)
      "flat": 0.7,                    "bola" only: how squashed (1 = round)
      "colors":  {"body": "#..", "accent": "#..", "detail": "#..", "inside": "#.."},
      "finish":  {"body": "esmalte", ...}       mate | esmalte | metal | tela | plastico | madera
      "face":    {"height": 0.55, "size": 1.0, "spacing": 1.0, "eyes": "ojos" | "botones",
                  "brows": "barra" | "arco" | "no", "cheeks": "#f0907a", "pupil": "#1c1512"},
      "arms":    {"style": "palito", "length": 1.0, "color": "detail"},     stubby arms (gestures)
      "feet":    true,                little feet under the body
      "accessories": [{"type": "vapor" | "lazo" | "hoja" | "gorro" | "gafas" | "pajarita" | "etiqueta", "color": "#.."}],
      "acting":  {"<part>": {"<emotion|action|talk|base>": {"rx": 10, "z": 0.02, ...}}},   override the acting part
      "light":   {"color": "#ffcf8a", "power": 1.0}    lampara: the bulb's light
      "arm":     {"yaw": 50, "lower": 22, "upper": 18}  lampara: the arm's plane (turned from the face) and its two angles
    }

Rig interface (rigs/placeholders.py, animate.py): CHAR_<id> > ctrl_body (feet) > ctrl_head (the moving piece) with
eye_L/R (the pupils, which look around), eyelid_L/R (lids that blink and act: animate.lid_angle), brow_L/R,
mouth_rest/M/E/A/O/smile (Rhubarb visemes), optional ctrl_arm_L/R. The part that acts (a lid, the lamp's arm, the
laces) carries a JSON `act_poses` property that animate._acting_parts plays per emotion and action. A lamp also has
`lamp_bulb` + `lamp_*` lights (animate._lamp): its light is part of how it acts.

Everything is built in world space at rest (root at the origin, facing -Y) and then parented keeping transforms.
Face features are placed by ray casting onto the face part, so they sit on any shape, and the mouths are
conformed to the surface (they bend around a mug).
"""

from __future__ import annotations

import json
import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import empty, link, srgb

FINISHES = {
    "mate": dict(roughness=0.82, metallic=0.0, spec=0.3),
    "esmalte": dict(roughness=0.24, metallic=0.0, spec=0.5, coat=0.5),
    "metal": dict(roughness=0.3, metallic=1.0, spec=0.5),
    "tela": dict(roughness=1.0, metallic=0.0, spec=0.15, sheen=0.7),
    "plastico": dict(roughness=0.42, metallic=0.0, spec=0.45),
    "madera": dict(roughness=0.7, metallic=0.0, spec=0.3, grain=True),
}

# Per-form defaults: colours/finishes, where the face sits, how the head is damped. Users override any of it.
FORM_DEFAULTS = {
    "lampara": dict(size=0.78, sides=16, colors={"body": "#6fae8c", "accent": "#2b2d33", "detail": "#c9a44c", "inside": "#f3e6c4",
                                                 "rod": "#b9bec6", "spring": "#d9dde2"},
                    finish={"body": "esmalte", "accent": "mate", "detail": "metal", "inside": "mate", "rod": "metal", "spring": "metal"}),
    "cafetera": dict(size=0.5, sides=8, colors={"body": "#b9bec4", "accent": "#8d939a", "detail": "#26211f", "inside": "#3a2418"},
                     finish={"body": "metal", "accent": "metal", "detail": "plastico", "inside": "mate"}),
    "taza": dict(size=0.42, sides=16, colors={"body": "#e9e2d3", "accent": "#d65a3a", "detail": "#d65a3a", "inside": "#4a2a17"},
                 finish={"body": "esmalte", "accent": "esmalte", "detail": "esmalte", "inside": "esmalte"}),
    "olla": dict(size=0.5, sides=18, colors={"body": "#c23b2e", "accent": "#f2ece0", "detail": "#2b2b2e", "inside": "#3b3b3e"},
                 finish={"body": "esmalte", "accent": "esmalte", "detail": "plastico", "inside": "metal"}),
    "cajita": dict(size=0.42, sides=4, colors={"body": "#d8b98a", "accent": "#b5402f", "detail": "#3a2a20", "inside": "#7a5a3a"},
                   finish={"body": "madera", "accent": "mate", "detail": "mate", "inside": "mate"}),
    "zapatilla": dict(size=0.34, sides=12, colors={"body": "#3f6fd8", "accent": "#f4f1ea", "detail": "#f4f1ea", "inside": "#22252c"},
                      finish={"body": "tela", "accent": "plastico", "detail": "tela", "inside": "tela"}),
    "bloque": dict(size=0.5, sides=4, colors={"body": "#7fb38a", "accent": "#2f3b33", "detail": "#f2ece0", "inside": "#2f3b33"},
                   finish={"body": "mate", "accent": "mate", "detail": "mate", "inside": "mate"}),
    "cilindro": dict(size=0.55, sides=16, colors={"body": "#e8c547", "accent": "#2f6f8f", "detail": "#f2ece0", "inside": "#2f6f8f"},
                     finish={"body": "esmalte", "accent": "mate", "detail": "mate", "inside": "mate"}),
    "bola": dict(size=0.42, sides=16, colors={"body": "#e9a96a", "accent": "#f6e3c4", "detail": "#7a4a2a", "inside": "#7a4a2a"},
                 finish={"body": "mate", "accent": "mate", "detail": "mate", "inside": "mate"}),
    "cono": dict(size=0.55, sides=14, colors={"body": "#ef7d3c", "accent": "#f4f1ea", "detail": "#2b2b2e", "inside": "#2b2b2e"},
                 finish={"body": "plastico", "accent": "plastico", "detail": "mate", "inside": "mate"}),
}

# Emotion tweaks every object face starts from (personaje.json "emotion_overrides" goes on top): with big white
# eyes, fear shrinks the pupils instead of growing them.
FACE_EMOTIONS = {
    "alarma": {"eye_s": 0.82},
    "panico": {"eye_s": 0.68},
    "aliviado": {"brow_z": 0.012},
}

EYE_WHITE = "#f7f2e8"
MOUTH_DARK = "#3a1519"
TONGUE = "#d9646c"
TEETH = "#f5f0e6"


# --- materials ---------------------------------------------------------------------------------------------------

def finish_material(name: str, color: str, finish: str = "mate") -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    f = FINISHES.get(finish, FINISHES["mate"])
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Roughness"].default_value = f["roughness"]
    bsdf.inputs["Metallic"].default_value = f["metallic"]
    bsdf.inputs["Specular IOR Level"].default_value = f["spec"]
    if f.get("coat"):
        bsdf.inputs["Coat Weight"].default_value = f["coat"]
        bsdf.inputs["Coat Roughness"].default_value = 0.12
    if f.get("sheen"):
        bsdf.inputs["Sheen Weight"].default_value = f["sheen"]
        bsdf.inputs["Sheen Roughness"].default_value = 0.6
    if f.get("grain"):
        # Soft wood grain: bands of the same colour a touch darker (no image textures to ship).
        tex = nodes.new("ShaderNodeTexWave")
        tex.inputs["Scale"].default_value = 3.5
        tex.inputs["Distortion"].default_value = 6.0
        tex.inputs["Detail"].default_value = 2.0
        ramp = nodes.new("ShaderNodeMix")
        ramp.data_type = "RGBA"
        dark = srgb(color)
        ramp.inputs[6].default_value = srgb(color)
        ramp.inputs[7].default_value = (dark[0] * 0.78, dark[1] * 0.74, dark[2] * 0.7, 1.0)
        ramp.inputs[0].default_value = 0.0
        mul = nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 0.55
        links.new(tex.outputs["Fac"], mul.inputs[0])
        links.new(mul.outputs["Value"], ramp.inputs[0])
        links.new(ramp.outputs[2], bsdf.inputs["Base Color"])
    return mat


def glow_material(name: str, color: str, strength: float) -> bpy.types.Material:
    """Emission whose strength follows the object's colour R (animate._lamp bakes it): the lamp's bulb."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    info = nodes.new("ShaderNodeObjectInfo")
    sep = nodes.new("ShaderNodeSeparateColor")
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = strength
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb(color)
    base = nodes.new("ShaderNodeBsdfPrincipled")
    base.inputs["Base Color"].default_value = srgb("#e8dcc0")
    base.inputs["Roughness"].default_value = 0.3
    add = nodes.new("ShaderNodeAddShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(info.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Red"], mul.inputs[0])
    links.new(mul.outputs["Value"], emit.inputs["Strength"])
    links.new(base.outputs["BSDF"], add.inputs[0])
    links.new(emit.outputs["Emission"], add.inputs[1])
    links.new(add.outputs["Shader"], out.inputs["Surface"])
    return mat


# --- geometry (bmesh, world space at rest) -------------------------------------------------------------------

def lathe_bm(profile: list[tuple[float, float]], sides: int, sx: float = 1.0, sy: float = 1.0,
             cap_bottom: bool = True, cap_top: bool = True, flat_front: bool = True) -> bmesh.types.BMesh:
    """Revolve (r, z) points (bottom to top) around Z. sx/sy stretch it into an oval; flat_front puts a facet
    (not an edge) facing -Y, where the face goes."""
    bm = bmesh.new()
    phase = -math.pi / 2 + (math.pi / sides if flat_front else 0.0)
    angles = [phase + 2 * math.pi * i / sides for i in range(sides)]
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((r * sx * math.cos(a), r * sy * math.sin(a), z)) for a in angles])
    for a, b in zip(rings, rings[1:]):
        n = sides
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                bm.faces.new((a[0], b[j], b[i]))
            elif len(b) == 1:
                bm.faces.new((a[i], a[j], b[0]))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    return bm


def box_bm(size, bevel: float = 0.0, segments: int = 2) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, offset_type="OFFSET", segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def ball_bm(radii, subdivisions: int = 2) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(radii), verts=bm.verts)
    return bm


def uv_ball_bm(radii, segments: int = 16, rings: int = 10, half: bool = False) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    if half:  # keep the upper half (z >= 0): an eyelid shell
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    bmesh.ops.scale(bm, vec=Vector(radii), verts=bm.verts)
    return bm


def tube_bm(points: list[Vector], radius: float | list[float], sides: int = 6, caps: bool = True) -> bmesh.types.BMesh:
    """A tube along a polyline (handles, springs, laces), rings kept parallel (no twist)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, list) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        tangents.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    normal = (up - tangents[0] * up.dot(tangents[0])).normalized()
    rings = []
    for p, t, r in zip(pts, tangents, radii):
        normal = (normal - t * normal.dot(t)).normalized()
        binormal = t.cross(normal)
        rings.append([bm.verts.new(p + r * (normal * math.cos(a) + binormal * math.sin(a)))
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            m = (k + 1) % sides
            bm.faces.new((a[k], a[m], b[m], b[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def to_object(name: str, bm: bmesh.types.BMesh, mat, smooth: bool = False, matrix: Matrix | None = None) -> bpy.types.Object:
    if matrix is not None:
        bm.transform(matrix)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.polygons.foreach_set("use_smooth", [smooth] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    link(obj)
    if mat is not None:
        if isinstance(mat, (list, tuple)):
            for m in mat:
                mesh.materials.append(m)
        else:
            mesh.materials.append(mat)
    return obj


def attach(obj, parent) -> bpy.types.Object:
    """Parent keeping the world transform (everything is built at rest in world space)."""
    bpy.context.view_layer.update()
    mw = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj.matrix_world = mw
    return obj


def frame_matrix(origin: Vector, out_normal: Vector, up_hint: Vector) -> Matrix:
    """A frame whose -Y looks out of the surface and +Z points up along it (the rig's face convention)."""
    y = (-out_normal).normalized()
    z = (up_hint - y * up_hint.dot(y))
    z = z.normalized() if z.length > 1e-6 else Vector((0, 0, 1))
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = origin
    return m


# --- the face --------------------------------------------------------------------------------------------------

class FaceFrame:
    """Where the face looks: rays start in front of `center` and travel along `forward` onto the target meshes.
    (u, v) are metres to the character's left (+right of `right`) and up."""

    def __init__(self, targets: list, center: Vector, forward: Vector, up: Vector):
        bpy.context.view_layer.update()
        bm = bmesh.new()
        for obj in targets:
            part = bmesh.new()
            part.from_mesh(obj.data)
            part.transform(obj.matrix_world)
            tmp = bpy.data.meshes.new("_face_tmp")
            part.to_mesh(tmp)
            part.free()
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        self.bvh = BVHTree.FromBMesh(bm)
        bm.free()
        self.center, self.forward = Vector(center), Vector(forward).normalized()
        self.up = (Vector(up) - self.forward * Vector(up).dot(self.forward)).normalized()
        self.right = self.forward.cross(self.up)  # character's left = camera's right for -Y faces... see below
        # forward=+Y, up=+Z -> right = Y x Z = +X (the character's left, where eye_L goes)

    def cast(self, u: float, v: float) -> tuple[Vector, Vector]:
        start = self.center + self.right * u + self.up * v - self.forward * 2.0
        hit, normal, _, _ = self.bvh.ray_cast(start, self.forward, 4.0)
        if hit is None:  # off the silhouette: stay on the plane through the centre
            return self.center + self.right * u + self.up * v, -self.forward
        if normal.dot(self.forward) > 0:
            normal = -normal
        return hit, normal


def _poly_mouth(kind: str, w: float) -> list[tuple[list[tuple[float, float]], int]]:
    """2D shapes of each mouth (metres around the mouth centre), with a material index each: 0 dark, 1 tongue, 2 teeth."""
    def arc(n, x0, x1, f):
        return [(x0 + (x1 - x0) * i / n, f(x0 + (x1 - x0) * i / n)) for i in range(n + 1)]

    hw = w / 2

    def crescent(width, curve, thick, lift=0.0):
        h = width / 2
        top = arc(10, -h, h, lambda x: lift + curve * (x / h) ** 2 + thick / 2 * max(0.0, 1 - (x / h) ** 2) ** 0.5)
        bot = arc(10, h, -h, lambda x: lift + curve * (x / h) ** 2 - thick / 2 * max(0.0, 1 - (x / h) ** 2) ** 0.5)
        return top + bot[1:-1]

    def oval(rx, ry, n=16, flat_top=0.0, dy=0.0):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            y = ry * math.sin(a)
            if y > 0:
                y *= 1 - flat_top
            pts.append((rx * math.cos(a), y + dy))
        return pts

    if kind == "mouth_rest":
        return [(crescent(w * 0.62, 0.05 * w, 0.06 * w), 0)]
    if kind == "mouth_M":
        return [(crescent(w * 0.5, 0.01 * w, 0.045 * w), 0)]
    if kind == "mouth_smile":
        return [(crescent(w * 0.72, 0.14 * w, 0.065 * w, lift=-0.05 * w), 0)]
    if kind == "mouth_E":
        mouth = oval(hw * 0.86, 0.17 * w, flat_top=0.55)
        teeth = [(x * 0.82, y) for x, y in oval(hw * 0.86, 0.17 * w, flat_top=0.55) if y >= -0.001]
        teeth = [(-hw * 0.62, 0.035 * w), (hw * 0.62, 0.035 * w), (hw * 0.58, 0.0), (-hw * 0.58, 0.0)]
        return [(mouth, 0), (teeth, 2)]
    if kind == "mouth_A":
        mouth = oval(hw * 0.74, 0.3 * w, flat_top=0.35, dy=-0.06 * w)
        tongue = oval(hw * 0.42, 0.09 * w, flat_top=0.0, dy=-0.25 * w)
        return [(mouth, 0), (tongue, 1)]
    if kind == "mouth_O":
        mouth = oval(0.2 * w, 0.24 * w, dy=-0.04 * w)
        tongue = oval(0.12 * w, 0.06 * w, dy=-0.19 * w)
        return [(mouth, 0), (tongue, 1)]
    raise KeyError(kind)


class Face:
    def __init__(self, b: "Builder", frame: FaceFrame, fs: float, spec: dict, lid_mat, head):
        self.b, self.frame, self.fs, self.spec, self.lid_mat, self.head = b, frame, fs, spec, lid_mat, head
        cid = b.id
        self.white = finish_material(f"{cid}_eye_white", EYE_WHITE, "esmalte")
        self.pupil = finish_material(f"{cid}_pupil", spec.get("pupil", "#1c1512"), "esmalte")
        self.shine = bpy.data.materials.get("eye_shine") or _shine()
        self.dark = finish_material(f"{cid}_mouth", MOUTH_DARK, "mate")
        self.tongue = finish_material(f"{cid}_tongue", TONGUE, "mate")
        self.teeth = finish_material(f"{cid}_teeth", TEETH, "esmalte")
        self.brow = finish_material(f"{cid}_brow", spec.get("brow_color", "#2a1d17"), "mate")

    def build(self) -> dict:
        fs, sp = self.fs, self.spec
        size = sp.get("size", 1.0)
        fs *= size
        ev = fs * sp.get("eye_v", 0.08)
        dx = fs * 0.23 * sp.get("spacing", 1.0)
        out = {}
        for side, sx in (("L", 1), ("R", -1)):
            out[f"eye_{side}"] = self._eye(side, sx * dx, ev, fs)
            if sp.get("brows", "barra") != "no":
                self._brow(side, sx, sx * dx, ev + fs * 0.25, fs)
        mv = ev - fs * sp.get("mouth_drop", 0.36)
        for kind in ("mouth_rest", "mouth_M", "mouth_E", "mouth_A", "mouth_O", "mouth_smile"):
            m = self._mouth(kind, 0.0, mv, fs * 0.42 * sp.get("mouth_size", 1.0))
            m.hide_render = kind != "mouth_rest"
        if sp.get("cheeks"):
            mat = finish_material(f"{self.b.id}_cheeks", sp["cheeks"], "mate")
            for side, sx in (("L", 1), ("R", -1)):
                self._decal(f"cheek_{side}", [(sx * dx * 1.35 + 0.075 * fs * math.cos(a), ev - 0.2 * fs + 0.04 * fs * math.sin(a))
                                              for a in (2 * math.pi * i / 14 for i in range(14))], mat, lift=0.0012)
        self.eye_dx, self.eye_v, self.mouth_v = dx, ev, mv
        return out

    def _eye(self, side: str, u: float, v: float, fs: float):
        cid, sp = self.b.id, self.spec
        rx, rz = 0.14 * fs, 0.168 * fs
        ry = 0.07 * fs
        hit, n = self.frame.cast(u, v)
        socket = empty(f"eye_socket_{side}.{cid}")
        socket.matrix_world = frame_matrix(hit + n * (ry * 0.15), n, self.frame.up)
        attach(socket, self.head)
        if sp.get("eyes", "ojos") == "botones":
            # Bead eyes: one glossy dark bead (it squashes to blink, like the template's placeholders).
            eye = to_object(f"eye_{side}.{cid}", uv_ball_bm((1, 1, 1), 14, 10), self.pupil, smooth=True)
            eye.parent = socket
            eye.location = (0, -ry * 0.3, 0)
            eye.scale = (rx * 0.55, ry * 0.8, rz * 0.62)
            shine = to_object(f"eye_shine_{side}.{cid}", uv_ball_bm((1, 1, 1), 8, 6), self.shine, smooth=True)
            shine.parent = eye
            shine.location = (0.35, -0.72, 0.42)
            shine.scale = (0.26, 0.3, 0.26)
            eye["gaze_range"] = (rx * 0.12, rz * 0.1)
            return eye
        scale = empty(f"eye_scale_{side}.{cid}", parent=socket)
        scale.scale = (rx, ry, rz)
        white = to_object(f"eye_white_{side}.{cid}", uv_ball_bm((1, 1, 1), 18, 12), self.white, smooth=True)
        white.parent = scale
        lid = to_object(f"eyelid_{side}.{cid}", uv_ball_bm((1.09, 1.09, 1.09), 18, 12, half=True), self.lid_mat, smooth=True)
        lid.parent = scale
        from rigs.animate import lid_angle

        lid.rotation_euler = (lid_angle(1.0), 0, 0)
        # The pupil (eye_L/R in the rig interface): it looks around inside the white and widens with emotion.
        eye = to_object(f"eye_{side}.{cid}", uv_ball_bm((1, 1, 1), 14, 10), self.pupil, smooth=True)
        eye.parent = socket
        eye.location = (0, -ry * 0.86, -rz * 0.04)
        eye.scale = (rx * 0.56, ry * 0.18, rz * 0.6)
        shine = to_object(f"eye_shine_{side}.{cid}", uv_ball_bm((1, 1, 1), 8, 6), self.shine, smooth=True)
        shine.parent = eye
        shine.location = (0.36, -0.55, 0.42)
        shine.scale = (0.28, 0.42, 0.26)
        eye["gaze_range"] = (rx * 0.36, rz * 0.28)
        return eye

    def _brow(self, side: str, sx: int, u: float, v: float, fs: float) -> None:
        cid = self.b.id
        hit, n = self.frame.cast(u, v)
        socket = empty(f"brow_socket_{side}.{cid}")
        socket.matrix_world = frame_matrix(hit, n, self.frame.up)
        attach(socket, self.head)
        w, t = 0.18 * fs, 0.04 * fs
        style = self.spec.get("brows", "barra")
        bow = 0.035 * fs if style == "arco" else 0.012 * fs
        pts = [Vector((-w / 2 + w * i / 6, -t * 0.9, bow * (1 - (2 * i / 6 - 1) ** 2))) for i in range(7)]
        radii = [t * (0.55 + 0.45 * math.sin(math.pi * i / 6)) for i in range(7)]
        brow = to_object(f"brow_{side}.{cid}", tube_bm(pts, radii, 6), self.brow)
        brow.parent = socket
        brow.rotation_euler = (0, math.radians(sx * -5), 0)

    def _conform(self, pts2d: list[tuple[float, float]], u0: float, v0: float, front: float, back: float):
        """World positions (front, back) of a 2D outline laid on the surface around (u0, v0)."""
        fr, bk = [], []
        for x, y in pts2d:
            hit, n = self.frame.cast(u0 + x, v0 + y)
            fr.append(hit + n * front)
            bk.append(hit - n * back)
        return fr, bk

    def _slab(self, bm, pts2d, u0, v0, front, back, mat_index):
        fr, bk = self._conform(pts2d, u0, v0, front, back)
        vf = [bm.verts.new(p) for p in fr]
        vb = [bm.verts.new(p) for p in bk]
        f = bm.faces.new(vf)
        f.material_index = mat_index
        g = bm.faces.new(list(reversed(vb)))
        g.material_index = mat_index
        n = len(vf)
        for i in range(n):
            j = (i + 1) % n
            q = bm.faces.new((vf[j], vf[i], vb[i], vb[j]))
            q.material_index = mat_index

    def _mouth(self, kind: str, u: float, v: float, w: float):
        bm = bmesh.new()
        for pts, mi in _poly_mouth(kind, w):
            lift = 0.0016 if mi == 0 else 0.0026
            self._slab(bm, pts, u, v, lift * self.fs / 0.25, 0.004 * self.fs / 0.25, mi)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        obj = to_object(f"{kind}.{self.b.id}", bm, [self.dark, self.tongue, self.teeth])
        return attach(obj, self.head)

    def _decal(self, name: str, pts2d, mat, lift: float = 0.001):
        bm = bmesh.new()
        self._slab(bm, pts2d, 0.0, 0.0, lift * self.fs / 0.25, 0.002, 0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return attach(to_object(f"{name}.{self.b.id}", bm, mat), self.head)


def _shine() -> bpy.types.Material:
    from lib import material

    return material("eye_shine", "#ffffff", 0.3, emission=3.0)


# --- the builder ----------------------------------------------------------------------------------------------

class Builder:
    def __init__(self, char_id: str, meta: dict):
        self.id = char_id
        o = dict(meta.get("object") or {})
        self.form = o.get("form", "cilindro")
        if self.form not in FORMS:
            raise ValueError(f"{char_id}: form «{self.form}» does not exist ({', '.join(FORMS)})")
        d = FORM_DEFAULTS[self.form]
        self.o = o
        self.H = float(o.get("size", d["size"]))
        self.W = float(o.get("width", 1.0))
        self.D = float(o.get("depth", 1.0))
        self.sides = int(o.get("sides", d["sides"]))
        colors = {**d["colors"], **(o.get("colors") or {})}
        finish = {**d["finish"], **(o.get("finish") or {})}
        self.colors = colors
        self.mats = {role: finish_material(f"{char_id}_{role}", colors[role], finish.get(role, "mate")) for role in colors}
        self.root = empty(f"CHAR_{char_id}")
        self.body = empty(f"ctrl_body.{char_id}", parent=self.root)
        self.head = None
        self.face_spec = {**(o.get("face") or {})}

    def mat(self, role: str):
        if role.startswith("#"):
            return finish_material(f"{self.id}_{role[1:]}", role, "mate")
        return self.mats.get(role) or self.mats["body"]

    def part(self, name: str, bm, role: str, parent, smooth: bool = False, matrix: Matrix | None = None):
        obj = to_object(f"{name}.{self.id}", bm, self.mat(role), smooth, matrix)
        return attach(obj, parent)

    def make_head(self, pivot_z: float, gain: float = 0.55):
        self.head = empty(f"ctrl_head.{self.id}", (0, 0, pivot_z), self.body)
        self.head["gain"] = gain
        return self.head

    def acting(self, obj, poses: dict, key: str) -> None:
        override = (self.o.get("acting") or {}).get(key) or {}
        merged = {k: {**poses.get(k, {}), **override.get(k, {})} for k in set(poses) | set(override)}
        obj["act_poses"] = json.dumps(merged)

    def finish(self, face_targets, center, forward, up, fs, lid_role: str = "body", arm_z: float | None = None,
               half_width: float | None = None, top: Vector | None = None, neck: Vector | None = None):
        frame = FaceFrame(face_targets, Vector(center), Vector(forward), Vector(up))
        face = Face(self, frame, fs, self.face_spec, self.mat(lid_role), self.head)
        face.build()
        self.root["emotion_defaults"] = json.dumps(FACE_EMOTIONS)
        arms = self.o.get("arms")
        if arms and arm_z is not None and half_width is not None:
            self._arms(arms, arm_z, half_width)
        for acc in self.o.get("accessories") or []:
            accessory(self, acc, face, top, neck)
        return face

    def _arms(self, spec: dict, z: float, half_width: float) -> None:
        H, k = self.H, spec.get("length", 1.0)
        mat = spec.get("color", "detail")
        for side, sx in (("L", 1), ("R", -1)):
            pivot = empty(f"ctrl_arm_{side}.{self.id}", (sx * half_width, 0.0, z))
            attach(pivot, self.head)
            L = 0.24 * H * k
            arm = self.part(f"arm_{side}", tube_bm([Vector((sx * half_width, 0, z)), Vector((sx * (half_width + 0.012 * H), 0, z - L))],
                                                   0.016 * H, 6), mat, pivot)
            arm.name = f"arm_{side}.{self.id}"
            hand = self.part(f"hand_{side}", ball_bm((0.034 * H, 0.03 * H, 0.036 * H), 2), mat, pivot,
                             matrix=Matrix.Translation((sx * (half_width + 0.014 * H), 0, z - L - 0.02 * H)))
            hand.name = f"hand_{side}.{self.id}"

    def feet(self, half_width: float, front_y: float) -> float:
        """Two little feet under the body; returns their height (the body sits on them)."""
        h = 0.07 * self.H
        for side, sx in (("L", 1), ("R", -1)):
            self.part(f"foot_{side}", ball_bm((0.07 * self.H, 0.09 * self.H, h / 2 + 0.01 * self.H), 1), "detail", self.body,
                      matrix=Matrix.Translation((sx * half_width * 0.5, front_y * 0.35, h / 2)))
        return h * 0.85


# --- forms ---------------------------------------------------------------------------------------------------

def _round_profile(r: float, h: float, chamfer: float, z0: float = 0.0, top_r: float | None = None) -> list:
    top_r = r if top_r is None else top_r
    c = chamfer
    return [(0, z0), (r - c, z0), (r, z0 + c), (top_r, z0 + h - c), (top_r - c, z0 + h), (0, z0 + h)]


def form_cilindro(b: Builder):
    H = b.H
    lift = b.feet(0.3 * H * b.W, -0.3 * H * b.D) if b.o.get("feet") else 0.0
    R = 0.34 * H * b.W
    head = b.make_head(lift + 0.3 * H)
    body = b.part("body", lathe_bm(_round_profile(R, H, 0.05 * H, lift), b.sides, 1.0, b.D), "body", head)
    b.part("rim", lathe_bm([(R * 1.01, lift + H * 0.9), (R * 1.03, lift + H * 0.91), (R * 1.03, lift + H * 0.96), (R * 1.0, lift + H * 0.965)],
                           b.sides, 1.0, b.D, cap_bottom=False, cap_top=False), "accent", head)
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.5)), (0, 1, 0), (0, 0, 1), 2 * R * 0.78,
                    arm_z=lift + 0.55 * H, half_width=R * 1.0, top=Vector((0, 0, lift + H)), neck=Vector((0, -R * b.D, lift + 0.22 * H)))


def form_bloque(b: Builder):
    H = b.H
    W, D = 0.8 * H * b.W, 0.6 * H * b.D
    lift = b.feet(W / 2, -D / 2) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.3 * H)
    body = b.part("body", box_bm((W, D, H), bevel=0.07 * H, segments=2), "body", head,
                  matrix=Matrix.Translation((0, 0, lift + H / 2)))
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.52)), (0, 1, 0), (0, 0, 1), min(W * 0.82, H * 0.8),
                    arm_z=lift + 0.55 * H, half_width=W / 2, top=Vector((0, 0, lift + H)), neck=Vector((0, -D / 2, lift + 0.2 * H)))


def form_bola(b: Builder):
    H = b.H
    flat = float(b.o.get("flat", 0.78))
    rz = H / 2
    rx = rz / flat * 0.92 * b.W
    ry = rx * 0.92 * b.D
    lift = b.feet(rx * 0.7, -ry) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.25 * H)
    body = b.part("body", ball_bm((rx, ry, rz), 2), "body", head, matrix=Matrix.Translation((0, 0, lift + rz)))
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.5)), (0, 1, 0), (0, 0, 1), rx * 1.1,
                    arm_z=lift + 0.5 * H, half_width=rx * 0.98, top=Vector((0, 0, lift + H)), neck=Vector((0, -ry * 0.9, lift + 0.2 * H)))


def form_cono(b: Builder):
    H = b.H
    Rb, Rt = 0.42 * H * b.W, 0.16 * H * b.W
    if b.o.get("inverted"):
        Rb, Rt = Rt * 1.35, Rb
    lift = b.feet(Rb * 0.8, -Rb) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.25 * H)
    prof = [(0, lift), (Rb * 0.96, lift), (Rb, lift + 0.03 * H), (Rt, lift + H * 0.97), (Rt * 0.9, lift + H), (0, lift + H)]
    body = b.part("body", lathe_bm(prof, b.sides, 1.0, b.D), "body", head)
    band = []
    for z0, z1 in ((0.5, 0.6),):
        r0, r1 = Rb + (Rt - Rb) * z0, Rb + (Rt - Rb) * z1
        band.append(b.part("band", lathe_bm([(r0 * 1.012, lift + z0 * H), (r1 * 1.012, lift + z1 * H)], b.sides, 1.0, b.D,
                                            cap_bottom=False, cap_top=False), "accent", head))
    zf = b.face_spec.get("height", 0.36)
    rf = Rb + (Rt - Rb) * zf
    return b.finish([body, *band], (0, 0, lift + H * zf), (0, 1, 0), (0, 0, 1), 2 * rf * 0.7,
                    arm_z=lift + 0.4 * H, half_width=rf, top=Vector((0, 0, lift + H)), neck=Vector((0, -Rb, lift + 0.12 * H)))


def form_taza(b: Builder):
    H = b.H
    R = 0.36 * H * b.W
    t = 0.07 * R
    lift = b.feet(R * 0.8, -R) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.3 * H)
    prof = [(0, lift), (R * 0.88, lift), (R * 0.95, lift + 0.02 * H), (R, lift + 0.08 * H), (R * 1.02, lift + 0.92 * H),
            (R * 1.02, lift + H), (R * 1.02 - t, lift + H), (R * 1.0 - t, lift + 0.92 * H), (R * 0.98 - t, lift + 0.86 * H), (0, lift + 0.86 * H)]
    body = b.part("body", lathe_bm(prof, b.sides, 1.0, b.D), "body", head)
    b.part("drink", lathe_bm([(0, lift + 0.87 * H), (R * 0.985 - t, lift + 0.87 * H)], b.sides, 1.0, b.D, cap_bottom=False, cap_top=False),
           "inside", head)
    b.part("stripe", lathe_bm([(R * 1.026, lift + 0.8 * H), (R * 1.026, lift + 0.86 * H)], b.sides, 1.0, b.D, cap_bottom=False, cap_top=False),
           "accent", head)
    # The handle on its left (+X), a D shape: half in the wall.
    hx = R * 1.0
    pts = [Vector((hx - 0.02 * H, 0, lift + 0.76 * H)), Vector((hx + 0.12 * H, 0, lift + 0.74 * H)), Vector((hx + 0.2 * H, 0, lift + 0.62 * H)),
           Vector((hx + 0.2 * H, 0, lift + 0.4 * H)), Vector((hx + 0.12 * H, 0, lift + 0.28 * H)), Vector((hx - 0.02 * H, 0, lift + 0.26 * H))]
    b.part("handle", tube_bm(pts, 0.05 * H, 8), "detail", head)
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.46)), (0, 1, 0), (0, 0, 1), 2 * R * 0.74,
                    arm_z=lift + 0.5 * H, half_width=R * 1.02, top=Vector((0, 0, lift + H)), neck=Vector((0, -R, lift + 0.16 * H)))


def form_olla(b: Builder):
    H = b.H
    R = 0.52 * H * b.W
    Hb = 0.64 * H
    lift = b.feet(R * 0.7, -R) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.25 * H)
    prof = [(0, lift), (R * 0.92, lift), (R, lift + 0.05 * H), (R, lift + Hb - 0.04 * H), (R * 1.05, lift + Hb - 0.02 * H),
            (R * 1.05, lift + Hb), (R * 0.97, lift + Hb), (0, lift + Hb)]
    body = b.part("body", lathe_bm(prof, b.sides, 1.0, b.D), "body", head)
    for side, sx in (("L", 1), ("R", -1)):
        pts = [Vector((sx * R * 0.96, -0.06 * H, lift + Hb - 0.1 * H)), Vector((sx * (R + 0.1 * H), -0.06 * H, lift + Hb - 0.08 * H)),
               Vector((sx * (R + 0.1 * H), 0.06 * H, lift + Hb - 0.08 * H)), Vector((sx * R * 0.96, 0.06 * H, lift + Hb - 0.1 * H))]
        b.part(f"handle_{side}", tube_bm(pts, 0.025 * H, 6), "detail", head)
    pivot = empty(f"lid_pivot.{b.id}", (0, 0, lift + Hb))
    attach(pivot, head)
    lid_prof = [(R * 1.0, lift + Hb), (R * 0.98, lift + Hb + 0.03 * H), (R * 0.7, lift + Hb + 0.12 * H), (R * 0.25, lift + Hb + 0.16 * H), (0, lift + Hb + 0.165 * H)]
    b.part("lid", lathe_bm(lid_prof, b.sides, 1.0, b.D), "accent", pivot)
    b.part("knob", lathe_bm([(0, lift + Hb + 0.15 * H), (0.07 * H, lift + Hb + 0.16 * H), (0.08 * H, lift + Hb + 0.21 * H), (0, lift + Hb + 0.22 * H)],
                            10), "detail", pivot)
    b.acting(pivot, {"alarma": {"z": 0.09 * H, "rx": -10}, "panico": {"z": 0.14 * H, "rx": 12, "ry": -8},
                     "orgulloso": {"z": 0.015 * H}, "confuso": {"ry": -9, "z": 0.01 * H}, "juzgando": {"ry": 6},
                     "aliviado": {"z": 0.02 * H}, "talk": {"z": 0.012 * H}, "recoil": {"z": 0.05 * H}}, "lid")
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.33)), (0, 1, 0), (0, 0, 1), 2 * R * 0.56,
                    arm_z=lift + 0.38 * H, half_width=R, top=Vector((0, 0, lift + H)), neck=Vector((0, -R, lift + 0.1 * H)))


def form_cajita(b: Builder):
    H = b.H
    W, D = 0.95 * H * b.W, 0.78 * H * b.D
    Hb = 0.74 * H
    lift = b.feet(W / 2, -D / 2) if b.o.get("feet") else 0.0
    head = b.make_head(lift + 0.25 * H)
    body = b.part("body", box_bm((W, D, Hb), bevel=0.03 * H, segments=1), "body", head, matrix=Matrix.Translation((0, 0, lift + Hb / 2)))
    b.part("inside", box_bm((W * 0.9, D * 0.9, 0.01 * H)), "inside", head, matrix=Matrix.Translation((0, 0, lift + Hb - 0.002)))
    pivot = empty(f"lid_pivot.{b.id}", (0, D / 2, lift + Hb))
    attach(pivot, head)
    b.part("lid", box_bm((W * 1.04, D * 1.04, 0.2 * H), bevel=0.03 * H, segments=1), "accent", pivot,
           matrix=Matrix.Translation((0, 0, lift + Hb + 0.1 * H)))
    b.acting(pivot, {"alarma": {"rx": -38}, "panico": {"rx": -55}, "orgulloso": {"rx": -12}, "confuso": {"rx": -8, "ry": 4},
                     "aliviado": {"rx": -10}, "juzgando": {"rx": -4}, "talk": {"rx": -5}}, "lid")
    return b.finish([body], (0, 0, lift + H * b.face_spec.get("height", 0.38)), (0, 1, 0), (0, 0, 1), min(W, Hb) * 0.8,
                    arm_z=lift + 0.4 * H, half_width=W / 2, top=Vector((0, 0, lift + H)), neck=Vector((0, -D / 2, lift + 0.12 * H)))


def form_cafetera(b: Builder):
    """A moka pot: octagonal boiler and jug pinched at the waist, a lid that flips open on its hinge, a dark handle."""
    H = b.H
    w = b.W
    Rb, Rw, Rt = 0.36 * H * w, 0.27 * H * w, 0.34 * H * w
    head = b.make_head(0.28 * H, gain=0.5)
    boiler = [(0, 0), (Rb * 0.97, 0), (Rb, 0.015 * H), (Rw * 1.02, 0.4 * H), (Rw * 1.02, 0.4 * H), (0, 0.4 * H)]
    b.part("boiler", lathe_bm(boiler, b.sides, 1.0, b.D), "body", head)
    b.part("waist", lathe_bm([(0, 0.395 * H), (Rw * 1.12, 0.395 * H), (Rw * 1.12, 0.46 * H), (0, 0.46 * H)], b.sides, 1.0, b.D), "accent", head)
    jug = [(0, 0.455 * H), (Rw * 0.98, 0.455 * H), (Rt, 0.86 * H), (Rt * 1.03, 0.875 * H), (Rt * 0.97, 0.88 * H), (0, 0.88 * H)]
    upper = b.part("jug", lathe_bm(jug, b.sides, 1.0, b.D), "body", head)
    # Spout on its right (-X) and handle on its left (+X): the front stays free for the face.
    spout = bmesh.new()
    sp = [spout.verts.new(v) for v in ((-Rt * 0.9, -0.07 * H, 0.82 * H), (-Rt * 0.9, 0.07 * H, 0.82 * H), (-Rt * 0.92, 0.0, 0.9 * H),
                                       (-Rt - 0.11 * H, 0.0, 0.905 * H), (-Rt * 0.95, 0.0, 0.7 * H))]
    for f in ((sp[0], sp[3], sp[1]), (sp[0], sp[2], sp[3]), (sp[1], sp[3], sp[2]), (sp[0], sp[4], sp[3]), (sp[1], sp[3], sp[4])):
        spout.faces.new(f)
    bmesh.ops.recalc_face_normals(spout, faces=spout.faces)
    b.part("spout", spout, "body", head)
    hinge = Vector((Rt * 0.96, 0, 0.885 * H))
    pts = [Vector((Rt * 0.92, 0, 0.8 * H)), Vector((Rt + 0.1 * H, 0, 0.8 * H)), Vector((Rt + 0.2 * H, 0, 0.72 * H)),
           Vector((Rt + 0.24 * H, 0, 0.56 * H)), Vector((Rt + 0.2 * H, 0, 0.5 * H))]
    b.part("handle", tube_bm(pts, [0.03 * H, 0.04 * H, 0.045 * H, 0.045 * H, 0.035 * H], 8), "detail", head)
    b.part("bracket", tube_bm([Vector((Rt * 0.9, 0, 0.84 * H)), Vector((Rt + 0.05 * H, 0, 0.86 * H))], 0.02 * H, 6), "accent", head)
    b.part("valve", lathe_bm([(0, 0), (0.035 * H, 0), (0.035 * H, 0.05 * H), (0, 0.05 * H)], 6),
           "accent", head, matrix=Matrix.Translation((-Rb * 0.78, 0, 0.2 * H)) @ Matrix.Rotation(math.radians(-90), 4, "Y"))
    pivot = empty(f"lid_pivot.{b.id}", tuple(hinge))
    attach(pivot, head)
    lid = [(Rt * 0.99, 0.875 * H), (Rt * 0.99, 0.9 * H), (Rt * 0.75, 0.95 * H), (Rt * 0.25, 0.975 * H), (0, 0.978 * H)]
    b.part("lid", lathe_bm(lid, b.sides, 1.0, b.D, cap_bottom=True), "body", pivot)
    b.part("knob", lathe_bm([(0, 0.97 * H), (0.05 * H, 0.97 * H), (0.06 * H, 1.0 * H), (0.045 * H, 1.03 * H), (0, 1.035 * H)], 8), "detail", pivot)
    b.acting(pivot, {"alarma": {"ry": 26}, "panico": {"ry": 40}, "orgulloso": {"ry": 7}, "confuso": {"ry": 10},
                     "juzgando": {"ry": 4}, "aliviado": {"ry": 6}, "talk": {"ry": 4}, "recoil": {"ry": 20}}, "lid")
    zf = b.face_spec.get("height", 0.64)
    return b.finish([upper], (0, 0, H * zf), (0, 1, 0), (0, 0, 1), 0.42 * H * w,
                    arm_z=0.62 * H, half_width=Rt * 0.92, top=Vector((0, 0, 1.03 * H)), neck=Vector((0, -Rw * 1.1, 0.43 * H)))


def form_lampara(b: Builder):
    """An articulated desk lamp. The shade is the head (the face lives on it); the two arm sections are the part that
    acts (curious: leans in and tilts; sad: the arm sags and the light dims; startled: it shoots up)."""
    H = b.H
    k = H / 0.78
    cid = b.id
    base_r = 0.19 * k * b.W
    b.part("base", lathe_bm([(0, 0), (base_r * 0.97, 0), (base_r, 0.012 * k), (base_r, 0.035 * k), (base_r * 0.9, 0.05 * k),
                             (0.07 * k, 0.065 * k), (0.05 * k, 0.085 * k), (0, 0.09 * k)], 24), "body", b.body)
    b.part("base_ring", lathe_bm([(base_r * 1.004, 0.036 * k), (base_r * 0.98, 0.046 * k)], 24, cap_bottom=False, cap_top=False),
           "accent", b.body)
    # Arm: base joint -> elbow -> head joint. Two thin steel sections (a pair of parallel rods each), a coil spring
    # beside each section and round joints with brass caps: an articulated metal lamp. The arm's plane is turned
    # `arm_yaw` degrees from the face so the zigzag reads from the front too (side on, the sections overlap).
    arm = b.o.get("arm") or {}
    yaw = math.radians(float(arm.get("yaw", 50)))
    Rz = Matrix.Rotation(yaw, 3, "Z")
    lat = Rz @ Vector((1, 0, 0))  # the joints' axis
    j0 = Vector((0, 0.03 * k, 0.1 * k))
    lower_len, upper_len = 0.42 * k, 0.4 * k
    a0 = math.radians(float(arm.get("lower", 22)))  # lower arm leans back (degrees from vertical)
    j1 = j0 + (Rz @ Vector((0, math.sin(a0), math.cos(a0)))) * lower_len
    a1 = math.radians(float(arm.get("upper", 18)))  # upper arm reaches forward (degrees above horizontal)
    j2 = j1 + (Rz @ Vector((0, -math.cos(a1), math.sin(a1)))) * upper_len
    b.body["gain"] = 0.0  # the base stays planted: the arm and the shade do the acting
    lower = empty(f"arm_lower.{cid}", tuple(j0))
    lower.rotation_euler = (0, 0, yaw)
    attach(lower, b.body)
    upper = empty(f"arm_upper.{cid}", tuple(j1))
    upper.rotation_euler = (0, 0, yaw)
    attach(upper, lower)
    b.part("post", tube_bm([Vector((0, 0.03 * k, 0.07 * k)), j0], 0.016 * k, 10), "accent", b.body)
    for name, a, c, parent in (("lower", j0, j1, lower), ("upper", j1, j2, upper)):
        axis = (c - a).normalized()
        for sx in (1, -1):
            off = lat * (sx * 0.02 * k)
            b.part(f"rod_{name}_{'L' if sx > 0 else 'R'}", tube_bm([a + axis * 0.02 * k + off, c - axis * 0.02 * k + off], 0.0075 * k, 8),
                   "rod", parent, smooth=True)
        # Two cross braces keep the pair reading as one section (not two loose sticks).
        for t in (0.33, 0.7):
            m = a.lerp(c, t)
            b.part(f"brace_{name}_{int(t * 100)}", tube_bm([m - lat * 0.02 * k, m + lat * 0.02 * k], 0.005 * k, 6), "rod", parent)
        # The spring: beside the section, on the outer side, hooked near both joints (the lamp's "muscle").
        normal = axis.cross(lat).normalized()
        side = lat * 0.045 * k
        s0, s1 = a + axis * 0.05 * k + side + normal * 0.012 * k, c - axis * 0.12 * k + side + normal * 0.012 * k
        turns, n = 12, 168
        helix = []
        for i in range(n + 1):
            t = i / n
            ang = 2 * math.pi * turns * t
            helix.append(s0.lerp(s1, t) + (lat * math.cos(ang) + normal * math.sin(ang)) * 0.011 * k)
        b.part(f"spring_{name}", tube_bm(helix, 0.0026 * k, 5), "spring", parent, smooth=True)
        for end, to in ((s0, a), (s1, c - axis * 0.05 * k)):
            b.part(f"spring_hook_{name}_{'a' if end is s0 else 'b'}", tube_bm([end, to + side * 0.4], 0.0022 * k, 5), "spring", parent)
    def joint(name, p, parent, r):
        m = Matrix.Translation(p) @ Rz.to_4x4() @ Matrix.Rotation(math.radians(90), 4, "Y")
        b.part(name, lathe_bm([(0, -0.05 * k), (r * k, -0.05 * k), (r * k, 0.05 * k), (0, 0.05 * k)], 14), "accent", parent, matrix=m, smooth=True)
        for sx in (1, -1):
            m2 = Matrix.Translation(p + lat * (sx * 0.055 * k)) @ Rz.to_4x4() @ Matrix.Rotation(math.radians(90 * sx), 4, "Y")
            b.part(f"{name}_cap_{'L' if sx > 0 else 'R'}", lathe_bm([(0, -0.008 * k), (0.02 * k, -0.008 * k), (0.017 * k, 0.008 * k), (0, 0.011 * k)], 12),
                   "detail", parent, matrix=m2, smooth=True)

    joint("knob_base", j0, lower, 0.028)
    joint("knob_elbow", j1, upper, 0.026)
    # Between the arm and the shade: `arm_comp` undoes the arm's bends exactly (same turned axis), so the shade's own
    # tilt (`shade_tilt`) is pure expression and the head stays free for nods and gaze.
    comp = empty(f"arm_comp.{cid}", tuple(j2))
    comp.rotation_euler = (0, 0, yaw)
    attach(comp, upper)
    neck = empty(f"shade_tilt.{cid}", tuple(j2))
    attach(neck, comp)
    head = empty(f"ctrl_head.{cid}", tuple(j2))
    attach(head, neck)
    b.head = head
    head["gain"] = 1.0
    joint("knob_head", j2, comp, 0.024)
    # The shade: a bell whose mouth looks forward and down (at her notes). Its own axis: from the opening to the top.
    tilt = math.radians(float(b.o.get("shade_tilt", 4)))  # opening from straight down towards the front
    axis = Vector((0, math.sin(tilt), math.cos(tilt)))  # opening -> top (top leans back)
    R = 0.15 * k * b.W
    Hs = 0.2 * k
    top_center = j2 + Vector((0, -0.035 * k, -0.02 * k))
    rim_center = top_center - axis * Hs
    rot = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
    sm = Matrix.Translation(rim_center) @ rot
    t = 0.008 * k
    outer = [(R * 1.03, 0.0), (R * 1.05, 0.012 * k), (R * 0.99, 0.03 * k), (R * 0.9, 0.08 * k), (R * 0.74, 0.13 * k),
             (R * 0.5, 0.17 * k), (R * 0.3, 0.19 * k), (R * 0.18, Hs), (0, Hs + 0.004 * k)]
    shade = b.part("shade", lathe_bm(outer, b.sides, 1.0, b.D, cap_bottom=False), "body", head, matrix=sm)
    inner = [(R * 1.03 - t, 0.0), (R * 0.97 - t, 0.03 * k), (R * 0.88 - t, 0.08 * k), (R * 0.72 - t, 0.13 * k), (R * 0.48 - t, 0.165 * k),
             (0.0, 0.18 * k)]
    lining = b.part("shade_lining", lathe_bm(inner, b.sides, 1.0, b.D, cap_bottom=False, cap_top=False), "inside", head, matrix=sm)
    for poly in lining.data.polygons:  # the lining faces the inside
        poly.flip()
    b.part("shade_lip", lathe_bm([(R * 1.035, -0.001), (R * 1.055, 0.0125 * k)], b.sides, 1.0, b.D, cap_bottom=False, cap_top=False),
           "accent", head, matrix=sm)
    # Bulb + its light: part of the character (the documented exception to "no emission on characters").
    light = b.o.get("light") or {}
    lc = light.get("color", "#ffcf8a")
    bulb_pos = rim_center + axis * 0.07 * k
    bulb = to_object(f"lamp_bulb.{cid}", ball_bm((0.045 * k, 0.045 * k, 0.05 * k), 2), glow_material(f"{cid}_bulb", lc, 6.0),
                     matrix=Matrix.Translation(bulb_pos) @ rot)
    attach(bulb, head)
    bulb.color = (1.0, 0, 0, 1)
    b.part("bulb_socket", lathe_bm([(0, 0), (0.03 * k, 0), (0.032 * k, 0.04 * k), (0, 0.045 * k)], 10), "accent", head,
           matrix=Matrix.Translation(rim_center + axis * 0.1 * k) @ rot)
    power = float(light.get("power", 1.0))
    spot = bpy.data.lights.new(f"lamp_spot.{cid}", "SPOT")
    spot.color = srgb(lc)[:3]
    spot.energy = 38.0 * power
    spot.spot_size = math.radians(88)
    spot.spot_blend = 0.55
    spot.shadow_soft_size = 0.03
    so = bpy.data.objects.new(f"lamp_spot.{cid}", spot)
    link(so)
    so.matrix_world = Matrix.Translation(bulb_pos - axis * 0.01 * k) @ rot  # spot shines down its -Z = out of the mouth
    attach(so, head)
    fill = bpy.data.lights.new(f"lamp_fill.{cid}", "POINT")
    fill.color = srgb(lc)[:3]
    fill.energy = 2.2 * power
    fill.shadow_soft_size = 0.04
    fo = bpy.data.objects.new(f"lamp_fill.{cid}", fill)
    link(fo)
    fo.location = bulb_pos - axis * 0.05 * k
    attach(fo, head)
    # The arm acts: per emotion (and a few actions) the two sections bend; the head adds its own nods and tilts.
    arm_lower = {"alarma": {"rx": -6}, "panico": {"rx": -8, "ry": 2}, "hundido": {"rx": 5}, "confuso": {"ry": -4, "rx": 2},
                 "orgulloso": {"rx": -2}, "juzgando": {"ry": 2}, "aliviado": {"rx": -1},
                 "lean_in": {"rx": 6}, "recoil": {"rx": -6}, "slump": {"rx": 5}, "stretch": {"rx": -8},
                 "shrug": {"ry": 3}, "talk_gesture": {"rx": 1.5}}
    arm_upper = {"alarma": {"rx": -12}, "panico": {"rx": -16}, "hundido": {"rx": 12}, "confuso": {"rx": -3, "ry": -4},
                 "orgulloso": {"rx": -5}, "juzgando": {"rx": 3}, "aliviado": {"rx": -3},
                 "lean_in": {"rx": 7}, "recoil": {"rx": -10}, "slump": {"rx": 12}, "stretch": {"rx": -14},
                 "talk": {"rx": -1.0}}
    b.acting(lower, arm_lower, "arm_lower")
    b.acting(upper, arm_upper, "arm_upper")
    undo = {}
    for key in set(arm_lower) | set(arm_upper):
        pose = {c: -(arm_lower.get(key, {}).get(c, 0.0) + arm_upper.get(key, {}).get(c, 0.0)) for c in ("rx", "ry")}
        undo[key] = {c: v for c, v in pose.items() if v}
    comp["act_poses"] = json.dumps(undo)
    # What the shade itself does (on top of a level shade): nods forward when sad, tips back when startled, cocks
    # its head when curious.
    b.acting(neck, {"confuso": {"ry": -30}, "hundido": {"rx": 5}, "alarma": {"rx": -6}, "panico": {"rx": -8},
                    "orgulloso": {"rx": -5}, "juzgando": {"rx": 3, "ry": 8}, "aliviado": {"ry": 7},
                    "lean_in": {"rx": 8}, "recoil": {"rx": -6}, "slump": {"rx": 16}, "stretch": {"rx": -10},
                    "shrug": {"ry": 3}, "talk": {"rx": -0.4}}, "shade")
    # Face on the front of the shade, which faces forward and up.
    up = axis.copy()
    front_dir = Vector((0, -math.cos(tilt), math.sin(tilt)))
    center = rim_center + axis * Hs * b.face_spec.get("height", 0.42)
    face = b.finish([shade], center, -front_dir, up, R * 1.3, lid_role="body")
    return face


def form_zapatilla(b: Builder):
    """A sneaker pointing at the camera: eyes on the vamp, mouth by the toe, laces that act (they perk up when it is
    startled and droop when it is sad)."""
    H = b.H
    L, Wd = 2.1 * H * b.D, 0.9 * H * b.W
    b.face_spec.setdefault("spacing", 0.72)
    head = b.make_head(0.0, gain=0.5)
    sole_h = 0.11 * H
    b.part("sole", box_bm((Wd * 1.02, L * 1.02, sole_h), bevel=0.045 * H, segments=2), "accent", head,
           matrix=Matrix.Translation((0, 0, sole_h / 2)))
    bm = ball_bm((Wd * 0.5, L * 0.5, 0.6 * H), 3)
    for v in bm.verts:
        y = v.co.y / (L * 0.5)  # -1 toe .. 1 heel
        v.co.z = max(0.0, v.co.z) * (1.0 + 0.32 * y) * (1.0 - 0.35 * max(0.0, -y) ** 2)
    bmesh.ops.translate(bm, vec=Vector((0, 0, sole_h * 0.8)), verts=bm.verts)
    upper = b.part("upper", bm, "body", head)
    b.part("toe_cap", ball_bm((Wd * 0.45, 0.12 * L, 0.1 * H), 2), "accent", head, matrix=Matrix.Translation((0, -0.39 * L, sole_h + 0.02 * H)))
    top = FaceFrame([upper], Vector((0, 0, 0.5 * H)), Vector((0, 0, -1)), Vector((0, 1, 0)))

    def on_top(x, y, lift=0.0, scale=(1, 1, 1), role="inside", name="", bmesh_=None):
        hit, n = top.cast(x, y)  # (u = x, v = y) on the top surface
        m = frame_matrix(hit + n * lift, n, Vector((0, 1, 0)))
        return b.part(name, bmesh_ or ball_bm(scale, 2), role, head, matrix=m), hit, n

    on_top(0, 0.25 * L, 0.0, (Wd * 0.3, 0.02 * H, 0.16 * L), "inside", "collar")
    on_top(0, 0.47 * L, 0.0, (Wd * 0.14, 0.03 * H, 0.06 * H), "accent", "heel_tab",
           box_bm((Wd * 0.2, 0.05 * H, 0.18 * H), bevel=0.02 * H))
    hit, n = top.cast(0, 0.1 * L)
    b.part("tongue", box_bm((Wd * 0.34, 0.04 * H, 0.26 * H), bevel=0.02 * H), "detail", head,
           matrix=Matrix.Translation(hit + Vector((0, -0.02 * L, 0.1 * H))) @ Matrix.Rotation(math.radians(-30), 4, "X"))
    lace_pts = []
    for i, y in enumerate((-0.14, -0.05, 0.04)):
        hl, nl = top.cast(-Wd * 0.2, y * L)
        hr, nr = top.cast(Wd * 0.2, y * L)
        mid, nm = top.cast(0, y * L)
        b.part(f"lace_{i}", tube_bm([hl + nl * 0.01 * H, mid + nm * 0.018 * H, hr + nr * 0.01 * H], 0.02 * H, 6), "detail", head)
        lace_pts.append(mid + nm * 0.02 * H)
    knot = lace_pts[-1] + Vector((0, 0.02 * L, 0.02 * H))
    pivot = empty(f"laces_bow.{b.id}", tuple(knot))
    attach(pivot, head)
    for sx in (1, -1):
        loop = [knot + Vector((sx * x * H, y * H, z * H)) for x, y, z in
                ((0.0, 0, 0.0), (0.06, -0.02, 0.07), (0.15, -0.02, 0.1), (0.2, 0.0, 0.05), (0.13, 0.01, 0.0), (0.0, 0, 0.0))]
        b.part(f"bow_loop_{'L' if sx > 0 else 'R'}", tube_bm(loop, 0.018 * H, 6), "detail", pivot)
        end = [knot, knot + Vector((sx * 0.05 * H, -0.06 * H, -0.03 * H)), knot + Vector((sx * 0.09 * H, -0.1 * H, -0.12 * H))]
        b.part(f"bow_end_{'L' if sx > 0 else 'R'}", tube_bm(end, 0.016 * H, 6), "detail", pivot)
    b.acting(pivot, {"alarma": {"rx": -35, "s": 0.2}, "panico": {"rx": -45, "s": 0.3}, "hundido": {"rx": 40},
                     "orgulloso": {"rx": -12}, "confuso": {"ry": 25}, "aliviado": {"rx": -8},
                     "talk": {"rz": 10}}, "laces")
    # The face: a frame looking at the toe box from the front and a little above.
    fwd = Vector((0, 0.8, -0.6)).normalized()
    upv = Vector((0, 0.6, 0.8))
    zf = b.face_spec.get("height", 0.33)
    return b.finish([upper], Vector((0, -0.3 * L, zf * H)), fwd, upv, Wd * 0.85, top=knot + Vector((0, 0.15 * L, 0.25 * H)))


FORMS = {
    "lampara": form_lampara, "cafetera": form_cafetera, "taza": form_taza, "olla": form_olla, "cajita": form_cajita,
    "bloque": form_bloque, "cilindro": form_cilindro, "bola": form_bola, "cono": form_cono, "zapatilla": form_zapatilla,
}


# --- accessories ----------------------------------------------------------------------------------------------

def accessory(b: Builder, acc: dict, face: Face, top: Vector | None, neck: Vector | None) -> None:
    kind = acc.get("type")
    H = b.H
    color = acc.get("color")
    head = b.head
    if kind == "vapor" and top is not None:
        # Steam puffs over the top: hidden (tiny) at rest, they burst out when it is startled or boiling over.
        pivot = empty(f"steam.{b.id}", tuple(top + Vector((0, 0, 0.02 * H))))
        attach(pivot, head)
        mat = finish_material(f"{b.id}_steam", color or "#f4f2ee", "mate")
        for i, (x, z, r) in enumerate(((-0.03, 0.04, 0.05), (0.03, 0.1, 0.045), (-0.01, 0.16, 0.04))):
            p = to_object(f"steam_{i}.{b.id}", ball_bm((r * H, r * H, r * H * 0.9), 2), mat,
                          matrix=Matrix.Translation(top + Vector((x * H, 0, z * H))))
            attach(p, pivot)
        b.acting(pivot, {"base": {"s": -0.97}, "alarma": {"s": 0.97}, "panico": {"s": 1.25, "z": 0.03 * H},
                         "orgulloso": {"s": 0.5}}, "steam")
    elif kind == "lazo" and top is not None:
        mat = b.mat(color or "accent")
        for sx in (1, -1):
            wing = to_object(f"bow_{'L' if sx > 0 else 'R'}.{b.id}", ball_bm((0.07 * H, 0.03 * H, 0.05 * H), 1), mat,
                             matrix=Matrix.Translation(top + Vector((sx * 0.07 * H, 0, 0.03 * H))) @ Matrix.Rotation(math.radians(sx * 20), 4, "Y"))
            attach(wing, head)
        attach(to_object(f"bow_knot.{b.id}", ball_bm((0.03 * H, 0.03 * H, 0.03 * H), 1), mat,
                         matrix=Matrix.Translation(top + Vector((0, 0, 0.03 * H)))), head)
    elif kind == "hoja" and top is not None:
        stem = to_object(f"stem.{b.id}", tube_bm([top, top + Vector((0.01 * H, 0, 0.08 * H))], 0.012 * H, 5),
                         finish_material(f"{b.id}_stem", "#5a3a22", "mate"))
        attach(stem, head)
        leaf = to_object(f"leaf.{b.id}", ball_bm((0.08 * H, 0.03 * H, 0.012 * H), 1), finish_material(f"{b.id}_leaf", color or "#4f9a4a", "mate"),
                         matrix=Matrix.Translation(top + Vector((0.07 * H, 0, 0.07 * H))) @ Matrix.Rotation(math.radians(-25), 4, "Y"))
        attach(leaf, head)
    elif kind == "gorro" and top is not None:
        mat = finish_material(f"{b.id}_hat", color or "#f6f3ec", "tela")
        hs = float(acc.get("size", 1.6)) * H
        band = to_object(f"hat_band.{b.id}", lathe_bm([(0, 0), (0.17 * hs, 0), (0.18 * hs, 0.1 * hs), (0, 0.1 * hs)], 14), mat,
                         matrix=Matrix.Translation(top - Vector((0, 0, 0.01 * H))))
        attach(band, head)
        for i, (x, y, z, r) in enumerate(((0, 0, 0.2, 0.15), (0.1, 0.02, 0.17, 0.1), (-0.1, 0.0, 0.17, 0.1), (0.0, 0.09, 0.17, 0.1),
                                           (0.0, -0.09, 0.17, 0.1))):
            puff = to_object(f"hat_puff_{i}.{b.id}", ball_bm((r * hs, r * hs, r * hs * 0.85), 2), mat,
                             matrix=Matrix.Translation(top + Vector((x * hs, y * hs, z * hs))))
            attach(puff, head)
    elif kind == "pajarita" and neck is not None:
        mat = b.mat(color or "accent")
        for sx in (1, -1):
            wing = to_object(f"bowtie_{'L' if sx > 0 else 'R'}.{b.id}", lathe_bm([(0, 0), (0.05 * H, 0.0), (0, 0.085 * H)], 10, flat_front=False), mat,
                             matrix=Matrix.Translation(neck + Vector((sx * 0.085 * H, -0.02 * H, 0))) @ Matrix.Rotation(math.radians(-sx * 90), 4, "Y")
                             @ Matrix.Diagonal((1.0, 0.45, 1.0, 1.0)))
            attach(wing, head)
        attach(to_object(f"bowtie_knot.{b.id}", ball_bm((0.022 * H, 0.02 * H, 0.025 * H), 1), mat,
                         matrix=Matrix.Translation(neck + Vector((0, -0.015 * H, 0)))), head)
    elif kind == "gafas":
        mat = finish_material(f"{b.id}_glasses", color or "#1d1b1a", "plastico")
        r = 0.2 * face.fs * face.spec.get("size", 1.0)
        rings = []
        for side, sx in (("L", 1), ("R", -1)):
            hit, n = face.frame.cast(sx * face.eye_dx, face.eye_v)
            m = frame_matrix(hit + n * 0.02 * face.fs, n, face.frame.up) @ Matrix.Rotation(math.radians(90), 4, "X")
            pts = [Vector((r * math.cos(a), r * 1.0 * math.sin(a), 0)) for a in (2 * math.pi * i / 20 for i in range(21))]
            ring = to_object(f"glasses_{side}.{b.id}", tube_bm(pts, 0.012 * face.fs, 5, caps=False), mat, matrix=m)
            attach(ring, head)
            rings.append(hit + n * 0.02 * face.fs)
        attach(to_object(f"glasses_bridge.{b.id}", tube_bm([rings[0] - Vector((r * 0.9, 0, -0.01 * face.fs)), rings[1] + Vector((r * 0.9, 0, 0.01 * face.fs))],
                                                           0.01 * face.fs, 5), mat), head)
    elif kind == "etiqueta" and neck is not None:
        z0 = neck.z + 0.04 * H
        # A band around the body at the neck height (only round bodies: it is a lathe).
        r = abs(neck.y) * 1.03
        band = to_object(f"label.{b.id}", lathe_bm([(r, z0), (r, z0 + 0.12 * H)], b.sides, 1.0, b.D, cap_bottom=False, cap_top=False),
                         b.mat(color or "accent"))
        attach(band, head)


def build(char_id: str, meta: dict) -> bpy.types.Object:
    b = Builder(char_id, meta)
    FORMS[b.form](b)
    return b.root
