"""Shared helpers for scripts that run inside Blender (stdlib + bpy only)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from bpy_extras import anim_utils

ROOT = Path(__file__).resolve().parent.parent
INTERP = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}


def load_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def style() -> dict:
    return load_json(ROOT / "assets/style.json")


# Who plays each role slot in this scene (timeline["cast"], e.g. {"novato": "estudiante", "claude": "lucio"}).
# Mirrors reels/cast.py: the slot keeps its id (objects, cameras, sets), the body and look come from the player.
CAST: dict[str, str] = {}
CHARACTER_DIRS = ((ROOT / "personajes", "personaje.json"), (ROOT / "assets/characters", "character.json"))


def set_cast(cast: dict | None) -> None:
    CAST.clear()
    CAST.update(cast or {})


def character_dir(char_id: str) -> Path:
    """Folder of the character behind an id (a role slot resolves to its player)."""
    real = CAST.get(char_id, char_id)
    for folder, name in CHARACTER_DIRS:
        if (folder / real / name).exists():
            return folder / real
    return ROOT / "assets/characters" / real


def character_meta(char_id: str) -> dict:
    folder = character_dir(char_id)
    name = "personaje.json" if (folder / "personaje.json").exists() else "character.json"
    return load_json(folder / name)


def srgb(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """Hex sRGB -> linear RGBA for Blender color sockets."""
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    h = hex_color.lstrip("#")
    return (*(lin(int(h[i : i + 2], 16) / 255) for i in (0, 2, 4)), alpha)


def material(name: str, color: str, roughness: float = 0.85, emission: float = 0.0) -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    if emission:
        bsdf.inputs["Emission Color"].default_value = srgb(color)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def link(obj: bpy.types.Object, parent: bpy.types.Object | None = None, mat: bpy.types.Material | None = None):
    if obj.name not in bpy.context.scene.collection.objects:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    if mat is not None:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def empty(name: str, location=(0, 0, 0), parent=None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_size = 0.1
    return link(obj, parent)


def primitive(kind: str, name: str, location, scale=(1, 1, 1), parent=None, mat=None, **kwargs) -> bpy.types.Object:
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=(0, 0, 0), **kwargs)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name
    obj.location = location
    obj.scale = scale
    return link(obj, parent, mat)


def find(root: bpy.types.Object, base_name: str) -> bpy.types.Object | None:
    """Find a descendant by rig-interface name, ignoring '.suffix' (e.g. 'eye_L.novato', 'eye_L.001')."""
    for child in root.children_recursive:
        if child.name.split(".")[0] == base_name:
            return child
    return None


def bake(obj, path: str, index: int, frames: list[int], values: list[float], interp: str = "LINEAR") -> None:
    """Write a whole F-curve at once (much faster than keyframe_insert per frame)."""
    if not frames:
        return
    obj.keyframe_insert(path, index=index, frame=frames[0])
    anim = obj.animation_data
    cb = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    fc = cb.fcurves.find(path, index=max(index, 0))
    fc.keyframe_points.clear()
    fc.keyframe_points.add(len(frames))
    fc.keyframe_points.foreach_set("co", [x for f, v in zip(frames, values) for x in (float(f), float(v))])
    fc.keyframe_points.foreach_set("interpolation", [INTERP[interp]] * len(frames))
    fc.update()


def smoothstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * t for x, y in zip(a, b))
    return a + (b - a) * t


def look_at(obj: bpy.types.Object, target) -> None:
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


rad = math.radians
