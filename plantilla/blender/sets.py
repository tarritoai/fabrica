"""Sets (escenarios). Each builder returns anchor points used by placement and cameras.

`habitacion` is the default: a bedroom-office, the human at the desk facing camera, a window behind (a city by
night or by day), a bookcase, posters and a cork board. Everything you can change without code is in
`timeline["set_options"]` (script.json "set_options"; unknown keys are ignored, every key has a default):

    habitacion: {"window": "noche" | "dia", "wall": "#4f5d78", "floor": "#5b4636", "desk": "#6b4a35",
                 "rug": "#6a4f5e", "chair": "#2e3440", "posters": true, "poster_colors": ["#e8c25a", ...],
                 "corcho": true, "shelf": true, "plants": true, "sofa": false, "apuntes": true, "city": true,
                 "curtains": "#c2955a" | null}

`escritorio_noche` (older scripts) is the same room at night. The generic sets (estudio, mostrador, exterior) live
in sets_generic.py. A brand pack (blender/sets_marca.py, not part of the template) may add or replace sets.
"""

from __future__ import annotations

import random

import bpy
from mathutils import Vector

from lib import empty, link, material, primitive, srgb

ROOM = {
    "window": "noche", "wall": "#4f5d78", "floor": "#5b4636", "desk": "#6b4a35", "rug": "#6a4f5e", "chair": "#2e3440",
    "posters": True, "poster_colors": None, "corcho": True, "shelf": True, "plants": True, "sofa": False,
    "apuntes": True, "city": True, "curtains": "#c2955a", "pantalla": "apuntes",
}
SKY = {"noche": "#1c2a4c", "dia": "#9fc6e6"}


def _opts(timeline: dict | None, defaults: dict) -> dict:
    return {**defaults, **((timeline or {}).get("set_options") or {})}


def _world(color: str, strength: float) -> None:
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = srgb(color)
    bg.inputs["Strength"].default_value = strength


def _box(name: str, center, half, mat, parent):
    return primitive("cube", name, center, half, parent, mat)


def _facade_material(night: bool) -> bpy.types.Material:
    """Blocks of flats: a grid of windows in world metres (0.45 m x 0.6 m cells). By night a random third of them
    are lit (warm or cold); by day the facade is light and the glass reflects the sky."""
    mat = bpy.data.materials.new("city_facade_" + ("night" if night else "day"))
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    geo = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Position"], sep.inputs[0])

    def math_node(op, a, b=None):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    u = math_node("MULTIPLY", sep.outputs["X"], 1 / 0.45)
    v = math_node("MULTIPLY", sep.outputs["Z"], 1 / 0.6)
    # Inside each cell: a window where 0.18 < frac < 0.82 in both directions.
    fu, fv = math_node("FRACT", u), math_node("FRACT", v)
    inside = math_node("MULTIPLY",
                       math_node("MULTIPLY", math_node("GREATER_THAN", fu, 0.2), math_node("LESS_THAN", fu, 0.8)),
                       math_node("MULTIPLY", math_node("GREATER_THAN", fv, 0.22), math_node("LESS_THAN", fv, 0.8)))
    cell = nodes.new("ShaderNodeCombineXYZ")
    links.new(math_node("FLOOR", u), cell.inputs[0])
    links.new(math_node("FLOOR", v), cell.inputs[1])
    links.new(math_node("FLOOR", math_node("MULTIPLY", sep.outputs["Y"], 3.0)), cell.inputs[2])
    noise = nodes.new("ShaderNodeTexWhiteNoise")
    noise.noise_dimensions = "3D"
    links.new(cell.outputs[0], noise.inputs["Vector"])
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    links.new(inside, mix.inputs["Factor"])
    mix.inputs["A"].default_value = srgb("#34405c" if night else "#d8ccb6")
    mix.inputs["B"].default_value = srgb("#46557a" if night else "#7f9cbc")
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    if night:
        lit = math_node("MULTIPLY", inside, math_node("GREATER_THAN", noise.outputs["Value"], 0.62))
        warm = nodes.new("ShaderNodeMix")
        warm.data_type = "RGBA"
        links.new(math_node("GREATER_THAN", noise.outputs["Value"], 0.9), warm.inputs["Factor"])
        warm.inputs["A"].default_value = srgb("#ffc77a")
        warm.inputs["B"].default_value = srgb("#a9c6ff")
        links.new(warm.outputs["Result"], bsdf.inputs["Emission Color"])
        links.new(math_node("MULTIPLY", lit, 1.6), bsdf.inputs["Emission Strength"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _city(root, wall_y: float, night: bool) -> None:
    """A few blocks of flats across the street, seen through the window (lit windows at night)."""
    mat = _facade_material(night)
    rng = random.Random(7)
    x = -4.6
    while x < 4.6:
        w = rng.uniform(1.1, 1.9)
        h = rng.uniform(3.2, 7.5)
        d = wall_y + rng.uniform(5.0, 8.0)
        b = _box("city_block", (x + w / 2, d, h / 2 - 0.6), (w / 2 - 0.05, 0.6, h / 2), mat, root)
        b.name = f"city_block_{x:.1f}"
        x += w
    # The street far below: a dark band so the buildings don't float.
    _box("city_street", (0, wall_y + 4.2, -0.75), (6, 1.6, 0.05), material("city_street", "#1a1d26" if night else "#6f6a63", 0.9), root)


def furnish_desk(root, timeline: dict | None, wall_y: float, o: dict) -> dict:
    """Desk, chair, laptop, lamp (unless a lamp is in the cast), mug and clutter: the layout every desk set shares."""
    import props
    from lib import character_meta

    K = props.kenney
    w = props.KENNEY_SCALE
    desk_top = 0.384 * w
    K("desk", (0.715, 0.935, 0), 180, root, tint={"wood": o["desk"], "metal": "#2a2d33"})
    K("chairDesk", (0.01, 1.62, 0), 180, root, tint={"carpet": o["chair"]})
    lap = props.laptop((-0.32, 0.62, desk_top), 180, root, screen=o.get("pantalla", "apuntes"))
    lamp_x = -0.98 if (timeline or {}).get("ai_visits_laptop") else -0.72
    # A desk lamp in the cast (rigs/thing.py form "lampara") IS the lamp: the prop goes (its light stays).
    lamp_in_cast = any((character_meta(c).get("object") or {}).get("form") == "lampara"
                       for c in (timeline or {}).get("characters", []) if not character_meta(c).get("offscreen"))
    if not lamp_in_cast:
        K("lampSquareTable", (lamp_x, 0.2 if lamp_x == -0.72 else 0.35, desk_top), 0, root, tint={"lamp": "#f2d6a8"})
    props.mug((0.02, 0.8, desk_top), root)
    crowded = any((b.get("ai_copies") or 1) > 1 for b in (timeline or {}).get("beats", []))
    if not crowded:
        K("plantSmall1", (0.62, 0.33, desk_top), 0, root, scale=1.6)
        K("books", (0.18, 0.78, desk_top), 160, root, scale=1.4)
    if o.get("apuntes") and not crowded:
        _notes(root, desk_top, lamp_in_cast)
    K("cardboardBoxClosed", (1.0, 0.85, 0), 15, root)
    return {"desk_top": desk_top, "laptop": lap, "lamp_in_cast": lamp_in_cast}


def _notes(root, desk_top: float, lamp_in_cast: bool) -> None:
    """Study notes on the desk: loose sheets with lines of 'handwriting', a notebook, a highlighter."""
    import math

    paper = material("set_paper", "#f1ead8", 0.9)
    ink = material("set_ink", "#3b4a6b", 0.9)
    mark = material("set_highlight", "#f2d64b", 0.6)
    rng = random.Random(11)
    for i, (x, y, yaw) in enumerate(((0.12, 0.98, 8), (0.3, 0.95, -14), (-0.72, 0.98, 20))):
        z = desk_top + 0.002 + i * 0.0012
        sheet = _box(f"apunte_{i}", (x, y, z), (0.075, 0.105, 0.0008), paper, root)
        a = math.radians(yaw)
        sheet.rotation_euler = (0, 0, a)
        ca, sa = math.cos(a), math.sin(a)
        for r in range(7):
            ln = rng.uniform(0.05, 0.12)
            lx, ly = -0.06 + ln / 2, 0.08 - r * 0.025
            line = _box(f"apunte_{i}_l{r}", (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z + 0.0011),
                        (ln / 2, 0.003, 0.0003), mark if (i == 1 and r == 2) else ink, root)
            line.rotation_euler = (0, 0, a)
    nb = _box("libreta", (-0.9, 0.7, desk_top + 0.012), (0.09, 0.12, 0.012), material("set_libreta", "#2f6b5a", 0.7), root)
    nb.rotation_euler = (0, 0, 0.3)
    hl = primitive("cylinder", "subrayador", (0.22, 1.08, desk_top + 0.008), (0.008, 0.008, 0.06), root, mark, vertices=8)
    hl.rotation_euler = (1.5708, 0, 0.9)


def habitacion(timeline: dict | None = None, defaults: dict | None = None) -> dict:
    """A bedroom-office: the human at the desk facing camera, the window (a city at night or by day) behind, warm
    desk lamp vs cold screen. Same furniture and anchors as every desk set, so screens, phone and gestures work."""
    import props

    o = _opts(timeline, {**ROOM, **(defaults or {})})
    night = str(o.get("window", "noche")).lower() != "dia"
    root = empty("SET_habitacion")
    K = props.kenney
    w = props.KENNEY_SCALE
    wall_y = 1.75
    wall_h = 1.29 * w
    wall_col = o["wall"]
    plaster = material(f"k__defaultMat_{wall_col}", wall_col, 0.8)  # same material the Kenney window module gets
    trim = material("set_trim", "#e9e1d2", 0.7)

    # Floor (wooden boards), back wall with the window in the middle, side walls, skirting.
    floor = material("set_floor_boards", o["floor"], 0.7)
    _box("room_floor", (0, -0.6, -0.01), (4.6, 2.4, 0.01), floor, root)
    for i in range(-11, 12):  # board seams
        _box(f"floor_seam_{i}", (i * 0.4, -0.6, 0.0005), (0.004, 2.4, 0.0006), material("set_floor_seam", "#3a2c22", 0.9), root)
    K("wallWindow", (-0.5 * w, wall_y, 0), 0, root, tint={"_defaultMat": wall_col, "wood": "#e9e1d2", "metalDark": "#1a1d24"})
    back = wall_y + 0.04
    _box("wall_back_L", (-0.5 * w - 1.9, back + 0.05, wall_h / 2), (1.9, 0.05, wall_h / 2), plaster, root)
    _box("wall_back_R", (0.5 * w + 1.9, back + 0.05, wall_h / 2), (1.9, 0.05, wall_h / 2), plaster, root)
    _box("wall_side_L", (-2.95, wall_y - 2.2, wall_h / 2), (0.05, 2.25, wall_h / 2), plaster, root)
    _box("wall_side_R", (2.75, wall_y - 2.2, wall_h / 2), (0.05, 2.25, wall_h / 2), plaster, root)
    _box("ceiling", (0, wall_y - 2.2, wall_h + 0.03), (3.0, 2.3, 0.03), material("set_ceiling", "#d9d2c4", 0.9), root)
    for name, c, h in (("skirt_back", (0, back - 0.005, 0.04), (4.6, 0.012, 0.04)),
                       ("skirt_L", (-2.89, wall_y - 2.2, 0.04), (0.012, 2.25, 0.04)),
                       ("skirt_R", (2.69, wall_y - 2.2, 0.04), (0.012, 2.25, 0.04))):
        _box(name, c, h, trim, root)
    # Window glass: hidden (a pane between camera and city only adds reflections that read as smudges).
    for obj in bpy.data.objects:
        if obj.type == "MESH" and any(sl.material and sl.material.name.split(".")[0] == "glass" for sl in obj.material_slots):
            obj.hide_render = True
    if o.get("city", True):
        _city(root, wall_y, night)
    if o.get("curtains"):
        cur = material("set_curtain", o["curtains"], 0.95)
        for sx in (-1, 1):  # gathered at each side of the window: a few pleats, not a plank
            for i in range(5):
                x = sx * (0.92 + i * 0.05)
                pl = primitive("cylinder", f"curtain_{'L' if sx < 0 else 'R'}_{i}", (x, wall_y - 0.08 - (i % 2) * 0.025, 1.18),
                               (0.032, 0.03, 1.04), root, cur, vertices=8)
                pl.rotation_euler = (0, 0, 0.3 * i)
        _box("curtain_rod", (0, wall_y - 0.1, 2.24), (1.25, 0.012, 0.012), material("set_rod", "#2a2a2e", 0.5), root)

    rng = random.Random(3)
    desk = furnish_desk(root, timeline, wall_y, o)
    desk_top = desk["desk_top"]
    K("rugRectangle", (-1.4, 0.15, 0.002), 0, root, tint={"carpet": o["rug"], "carpetDarker": o["rug"]})
    if o.get("shelf", True):
        K("bookcaseOpen", (1.35, wall_y - 0.5, 0), 0, root, tint={"wood": o["desk"]})
        for i, z in enumerate((0.05, 0.47, 0.9, 1.32)):
            K("books", (1.42 + (i % 2) * 0.22, wall_y - 0.47, z), rng.uniform(-10, 10), root, scale=1.6)
    if o.get("plants", True):
        K("pottedPlant", (-1.75, 1.35, 0), 30, root)
    if o.get("sofa"):
        K("loungeSofa", (-2.8, -0.157, 0), 25, root, tint={"carpet": "#5a4a6a", "carpetDarker": "#463a54", "wood": "#3b2b24"})
    if o.get("posters", True):
        cols = o.get("poster_colors") or ["#e9dcc0", "#d9774f", "#3f6f8f", "#2f2a28"]
        props.poster("poster_a", (-1.55, wall_y - 0.03 + 0.05, 1.65), (0.5, 0.7), cols, root)
        props.poster("poster_b", (-2.25, wall_y - 0.03 + 0.05, 1.5), (0.35, 0.45), ["#f0e6d0", "#6aa58a", "#e8c25a"], root)
    if o.get("corcho", True):
        _cork_board(root, (1.62, wall_y + 0.03, 1.95))

    # Lights. Names are shared with moods.py (lamp_key, lamp_light, moon_rim, room_fill, screen_light, ai_rim).
    props.point_light("lamp_light", (-0.6, 0.32, desk_top + 0.48), "#ffb066", 70, 0.07)
    props.area_light("lamp_key", (-1.3, -0.5, 1.7), (0.0, 0.85, 1.05), "#ffb47a", 85, 1.2)
    props.area_light("screen_light", (-0.32, 0.66, desk_top + 0.3), (-0.32, 1.12, desk_top + 0.62), "#9cc0ff", 2.5, 0.3, 0.18)
    if night:
        props.area_light("moon_rim", (0.8, 3.6, 3.0), (-0.2, 1.0, 1.2), "#7fa2ff", 300, 1.5)
        props.area_light("room_fill", (1.6, -2.4, 1.8), (0, 0.8, 1.0), "#5a6f9a", 110, 3.0)
        props.area_light("wall_wash", (0.0, -1.0, 2.3), (0.0, wall_y, 1.3), "#ffcf9a", 60, 2.5)
        _world(SKY["noche"], 1.0)
    else:
        sun = bpy.data.lights.new("sun_window", "SUN")
        sun.energy = 1.1
        sun.color = srgb("#fff1dc")[:3]
        so = bpy.data.objects.new("sun_window", sun)
        link(so)
        so.rotation_euler = (0.95, 0.0, 3.0)
        props.area_light("moon_rim", (0.8, 3.6, 3.0), (-0.2, 1.0, 1.2), "#fff4e0", 160, 1.5)
        props.area_light("room_fill", (1.6, -2.4, 1.8), (0, 0.8, 1.0), "#dfe8ff", 120, 3.0)
        props.area_light("wall_wash", (0.0, -1.0, 2.3), (0.0, wall_y, 1.3), "#fff6ea", 50, 2.5)
        _world(SKY["dia"], 0.55)
    props.area_light("ai_rim", (0.9, 1.5, 1.5), (0.32, 0.62, 1.0), "#8fb4ff", 50, 0.6)
    if timeline and any(b.get("away") for b in timeline["beats"]):
        timeline.setdefault("_gaze_points", {})["_door"] = (-3.2, -0.6, 1.5)

    anchors = desk_anchors(desk_top, desk["laptop"], wall_y)
    anchors["cameras"] = lambda heads, ais: _room_cameras(heads, ais)
    return anchors


def _cork_board(root, at) -> None:
    """A cork board with sticky notes and a calendar sheet (study, plans): colour, no words."""
    x, y, z = at
    _box("corcho_frame", (x, y - 0.012, z), (0.36, 0.01, 0.25), material("corcho_frame", "#c9b48f", 0.7), root)
    _box("corcho", (x, y - 0.024, z), (0.33, 0.006, 0.22), material("corcho", "#b0814f", 1.0), root)
    rng = random.Random(5)
    colors = ["#f2d64b", "#f29b7a", "#9fd3c7", "#f1ead8", "#c6b3e6", "#f2d64b"]
    for i, c in enumerate(colors):
        nx = x - 0.25 + (i % 3) * 0.24 + rng.uniform(-0.03, 0.03)
        nz = z + 0.09 - (i // 3) * 0.19 + rng.uniform(-0.02, 0.02)
        s = 0.05 if c != "#f1ead8" else 0.07
        n = _box(f"postit_{i}", (nx, y - 0.032, nz), (s, 0.002, s * (1.25 if c == "#f1ead8" else 1)), material(f"postit_{c}", c, 0.9), root)
        n.rotation_euler = (0, rng.uniform(-0.15, 0.15), 0)


def desk_anchors(desk_top: float, lap: dict, wall_y: float) -> dict:
    """Anchors of the desk layout (furnish_desk): slots, the laptop, the phone, copies of the thing, the band."""
    SILL = 0.766  # the window's sill (measured in Blender)
    return {
        "slots": {
            "left": (-0.32, 1.12, -0.06),
            "right": (0.32, 0.62, desk_top),
            "right_a": (0.2, 0.58, desk_top),
            "right_b": (0.62, 0.66, desk_top),
            "laptop": (0.0, 0.47, desk_top),
            "sofa": (-1.668, 0.736, 0.0),
            "front": (0.02, 0.3, desk_top),
        },
        "facing": {"left": 22, "right": -40, "right_a": -40, "right_b": -55, "laptop": -60, "sofa": 25, "front": -15},
        "ai_scale": 0.72,
        "seated": ["novato"],
        "laptop": lap,
        "phone_spot": (-0.6, 0.74, desk_top),
        "copy_spots": [
            (0.64, 0.8, desk_top), (0.6, 0.33, desk_top), (0.95, -0.15, 0.0), (-0.42, -0.2, 0.0),
            (1.15, 1.1, 0.49), (1.6, 1.45, 1.657), (1.9, 1.45, 0.9), (1.35, 0.4, 0.0),
            (0.15, 1.8, SILL), (-0.95, 0.05, 0.0), (1.3, -0.45, 0.0),
        ],
        "band_spots": [(-0.01, 0.08, 0.0), (0.71, 0.08, 0.0), (-0.37, 0.36, 0.0), (1.07, 0.36, 0.0)],
        "band_lead": (0.35, -0.2, 0.0),
        "band_target": (0.35, -3.5, 0.4),
        "mini_spot": ((0.09, 0.87, desk_top), -25),
        "desk_top": desk_top,
        "island_center": (0.0, 0.35, 0.0),
    }


def _room_cameras(heads: dict, ais: list[str]) -> dict:
    """A closed room: the opening shot arrives through the open fourth wall (no flying in from space), and the
    'alone in the dark' wide is the whole room from the corner, slowly pulling back."""
    pts = list(heads.values())
    mid = sum(pts, Vector()) / len(pts)
    room = mid + Vector((0, 0.1, -0.55))
    top = max(p.z for p in pts)  # frame from the tallest head down: a small thing must not push the human out
    h = heads.get("novato")
    human = {}
    if h is not None:
        # The human at the desk, from the lamp's side and a little above the laptop lid: the face centred and lit by
        # the lamp, the lid low in the frame (from the front and low it filled a third of the shot).
        human = {
            "closeup_novato": dict(loc=h + Vector((0.28, -1.3, 0.1)), target=h + Vector((-0.06, 0, -0.17)), lens=38, fstop=2.2,
                                   follow="novato"),
            "medium_novato_low": dict(loc=h + Vector((0.35, -1.55, -0.1)), target=h + Vector((0.0, 0, -0.32)), lens=32, fstop=2.8,
                                      follow="novato"),
        }
    return {
        **human,
        # A little above the desk: its top (notes, phone, laptop) reads, and both faces are bigger than from the front.
        "two_shot": dict(loc=Vector((mid.x + 0.2, mid.y - 1.6, top + 0.5)), target=Vector((mid.x, mid.y + 0.05, top - 0.4)),
                         lens=30, fstop=4.0),
        "establishing": dict(loc=mid + Vector((0.15, -2.3, -0.05)), start=mid + Vector((0.9, -4.6, 0.7)),
                             target=mid + Vector((0, 0, -0.2)), lens=30, fstop=None),
        "wide_space": dict(loc=room + Vector((1.2, -3.0, 1.0)), end=room + Vector((1.35, -3.6, 1.1)),
                           target=room + Vector((-0.2, 0.4, -0.05)), lens=24, fstop=None),
    }


def escritorio_noche(timeline: dict | None = None) -> dict:
    """Older scripts: the room at night (the floating-island version lives in the brand pack)."""
    return habitacion(timeline, {"window": "noche"})


def estudio(timeline: dict | None = None) -> dict:
    import sets_generic

    return sets_generic.estudio(timeline)


def mostrador(timeline: dict | None = None) -> dict:
    import sets_generic

    return sets_generic.mostrador(timeline)


def exterior(timeline: dict | None = None) -> dict:
    import sets_generic

    return sets_generic.exterior(timeline)


SETS = {"habitacion": habitacion, "escritorio_noche": escritorio_noche, "estudio": estudio, "mostrador": mostrador,
        "exterior": exterior}

try:  # a brand pack copied over the template (blender/sets_marca.py) adds its own sets
    import sets_marca

    SETS.update(sets_marca.SETS)
except ImportError:
    pass
