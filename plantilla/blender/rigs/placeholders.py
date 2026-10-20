"""Generic placeholder characters that satisfy the rig interface (PLAN.md §6).

Hierarchy per character:
    CHAR_<id> (empty, placement)
      ctrl_body (empty, pivot at feet; procedural actions animate this)
        body meshes…
        ctrl_head (empty, pivot at neck)
          head meshes, eye_L, eye_R, brow_L, brow_R, mouth_A/E/O/M/rest
        ctrl_arm_L / ctrl_arm_R (optional, capsule only: pivot at the shoulder, arm hangs along -Z,
          ctrl_forearm_<side> at the elbow, UPPER_ARM below it; hand FOREARM below the elbow.
          rigs/arms.py solves both joints to reach hand targets)
Real character .blend files only need CHAR_<id> plus the facial controls;
ctrl_body / ctrl_head are optional.
"""

from __future__ import annotations

import bpy

from lib import empty, material, primitive, rad

MOUTHS = ("mouth_rest", "mouth_M", "mouth_E", "mouth_A", "mouth_O")
UPPER_ARM = 0.29
FOREARM = 0.28


def _face(char_id: str, head: bpy.types.Object, center, radius_y: float, eye_dx: float, scale: float = 1.0) -> None:
    """Eyes (black spheres + highlight), prism brows and viseme mouths on the -Y face."""
    cx, cy, cz = center
    front = cy - radius_y
    eye_mat = material("eye_black", "#050505", 0.25)
    shine_mat = material("eye_shine", "#ffffff", 0.3, emission=3.0)
    mouth_mat = material("mouth_dark", "#2a0d0d", 0.7)
    brow_mat = material(f"brow_{char_id}", "#2b1d14", 0.8)
    s = scale
    for side, sx in (("L", 1), ("R", -1)):
        eye = primitive(
            "uv_sphere", f"eye_{side}.{char_id}", (cx + sx * eye_dx, front + 0.01, cz + 0.05 * s),
            (0.055 * s, 0.04 * s, 0.065 * s), head, eye_mat, segments=10, ring_count=8,
        )
        primitive(
            "uv_sphere", f"eye_shine_{side}.{char_id}", (0.35, -0.75, 0.4), (0.3, 0.3, 0.3), eye, shine_mat,
            segments=6, ring_count=4,
        )
        primitive(
            "cube", f"brow_{side}.{char_id}", (cx + sx * eye_dx, front + 0.005, cz + 0.16 * s),
            (0.06 * s, 0.015 * s, 0.014 * s), head, brow_mat,
        )

    mz = cz - 0.11 * s
    my = front + 0.012
    shapes = {
        "mouth_rest": (0.05, 0.01, 0.008),
        "mouth_M": (0.045, 0.01, 0.004),
        "mouth_E": (0.06, 0.01, 0.02),
        "mouth_A": (0.05, 0.01, 0.045),
        "mouth_O": (0.032, 0.01, 0.035),
    }
    for name, (sx_, sy_, sz_) in shapes.items():
        kind = "cube" if name in ("mouth_rest", "mouth_M") else "uv_sphere"
        extra = {"segments": 10, "ring_count": 6} if kind == "uv_sphere" else {}
        m = primitive(kind, f"{name}.{char_id}", (cx, my, mz), (sx_ * s, sy_ * s, sz_ * s), head, mouth_mat, **extra)
        m.hide_render = name != "mouth_rest"


def capsule(char_id: str, meta: dict) -> bpy.types.Object:
    p = meta["placeholder"]
    root = empty(f"CHAR_{char_id}")
    body = empty(f"ctrl_body.{char_id}", parent=root)
    cloth = material(f"cloth_{char_id}", p["color"], 0.9)
    skin = material(f"skin_{char_id}", p["head_color"], 0.75)
    hair = material(f"hair_{char_id}", p["hair_color"], 0.9)
    dark = material("pants_dark", "#22252c", 0.9)

    for side, x in (("L", 0.12), ("R", -0.12)):
        primitive("cylinder", f"leg_{side}.{char_id}", (x, 0, 0.27), (0.085, 0.085, 0.27), body, dark, vertices=6)
    primitive("cylinder", f"torso.{char_id}", (0, 0, 0.86), (0.3, 0.22, 0.34), body, cloth, vertices=8)
    primitive("uv_sphere", f"shoulders.{char_id}", (0, 0, 1.17), (0.3, 0.22, 0.1), body, cloth, segments=8, ring_count=4)
    for side, x in (("L", 0.31), ("R", -0.31)):
        shoulder = empty(f"ctrl_arm_{side}.{char_id}", (x, 0, 1.13), body)
        shoulder.rotation_mode = "QUATERNION"
        primitive("cylinder", f"arm_{side}.{char_id}", (0, 0, -UPPER_ARM / 2), (0.062, 0.062, UPPER_ARM / 2 + 0.02), shoulder, cloth, vertices=6)
        elbow = empty(f"ctrl_forearm_{side}.{char_id}", (0, 0, -UPPER_ARM), shoulder)
        elbow.rotation_mode = "QUATERNION"
        primitive("uv_sphere", f"elbow_{side}.{char_id}", (0, 0, 0), (0.058, 0.058, 0.058), elbow, cloth, segments=6, ring_count=4)
        primitive("cylinder", f"forearm_{side}.{char_id}", (0, 0, -FOREARM / 2), (0.055, 0.055, FOREARM / 2), elbow, cloth, vertices=6)
        primitive("uv_sphere", f"hand_{side}.{char_id}", (0, 0, -FOREARM - 0.02), (0.05, 0.04, 0.058), elbow, skin, segments=8, ring_count=5)

    head = empty(f"ctrl_head.{char_id}", (0, 0, 1.22), body)
    hz = 0.2  # head centre above the neck pivot
    primitive("ico_sphere", f"head.{char_id}", (0, 0, hz), (0.24, 0.22, 0.26), head, skin, subdivisions=2)
    hair_obj = primitive("ico_sphere", f"hair.{char_id}", (0, 0.03, hz + 0.09), (0.25, 0.23, 0.2), head, hair, subdivisions=1)
    hair_obj.rotation_euler = (rad(-12), 0, 0)
    _face(char_id, head, (0, 0, hz), 0.21, 0.085)
    return root


def block(char_id: str, meta: dict) -> bpy.types.Object:
    """Neutral rounded block: the whole body is the face."""
    root = empty(f"CHAR_{char_id}")
    body = empty(f"ctrl_body.{char_id}", parent=root)
    mat = material(f"body_{char_id}", meta["placeholder"]["color"], 0.8)
    b = primitive("cube", f"block.{char_id}", (0, 0, 0.36), (0.36, 0.28, 0.34), body, mat)
    bev = b.modifiers.new("bevel", "BEVEL")
    bev.width = 0.08
    bev.segments = 2
    head = empty(f"ctrl_head.{char_id}", (0, 0, 0.36), body)
    _face(char_id, head, (0, 0, 0.04), 0.285, 0.12, scale=1.4)
    return root


def sphere(char_id: str, meta: dict) -> bpy.types.Object:
    root = empty(f"CHAR_{char_id}")
    body = empty(f"ctrl_body.{char_id}", parent=root)
    mat = material(f"body_{char_id}", meta["placeholder"]["color"], 0.8)
    primitive("ico_sphere", f"ball.{char_id}", (0, 0, 0.38), (0.38, 0.36, 0.38), body, mat, subdivisions=2)
    head = empty(f"ctrl_head.{char_id}", (0, 0, 0.38), body)
    _face(char_id, head, (0, 0, 0.04), 0.35, 0.12, scale=1.4)
    return root


def human(char_id: str, meta: dict) -> bpy.types.Object:
    from rigs import human as model

    return model.build(char_id, meta)


def thing(char_id: str, meta: dict) -> bpy.types.Object:
    """An object with a face built from data (personaje.json "object"): rigs/thing.py."""
    from rigs import thing as model

    return model.build(char_id, meta)


BUILDERS = {"capsule": capsule, "block": block, "sphere": sphere, "human": human, "object": thing}

try:  # the original series' clay jar lives in the brand pack (rigs/ceramic.py), not in the template
    from rigs import ceramic as _ceramic

    BUILDERS["ceramic"] = _ceramic.build
except ImportError:
    pass


def build(char_id: str, meta: dict) -> bpy.types.Object:
    shape = meta["placeholder"]["shape"]
    if shape not in BUILDERS:
        raise ValueError(f"character {char_id}: unknown shape {shape!r} (use 'object' for a thing with a face, 'human' for a person)")
    return BUILDERS[shape](char_id, meta)
