"""Generic sets for any niche: a plain-colour studio, a shop counter (café / bakery / any business) and a park.

Each one is parametrised by `timeline["set_options"]` (script.json "set_options"): colours by name and a few
switches, so the same set dresses many niches without code. Unknown keys are ignored; every key has a default.

    estudio:   {"background": "#e8dcc8", "floor": null, "plinth": "#cbb89a", "plinth_on": true, "key": "#fff0dc"}
    mostrador: {"variant": "cafeteria" | "obrador", "wall": "#e2d2b6", "counter": "#7a4e33", "top": "#ece6da",
                "accent": "#2f6b5a", "floor": "#b79e7c", "daylight": true,
                "pizarra": "Hoy|lo de siempre", "pizarra_tiza": "#e9e4d6", "pizarra_fondo": "#26302c"}
    exterior:  {"grass": "#86b35c", "sky": "#c4e3f3", "path": "#dcc9a2", "trees": "#4f8a43", "bench": true, "stump": true}

Slots follow escritorio_noche (blender/sets.py): "left" = the human (standing here), "right" (+ "right_a"/"right_b")
= the thing(s), "sofa" = a second human. Things are scaled by "ai_scale" like on the desk.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from lib import ROOT, empty, link, material, rad, srgb


def _opts(timeline: dict | None, defaults: dict) -> dict:
    return {**defaults, **((timeline or {}).get("set_options") or {})}


def _world(color: str, strength: float) -> None:
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = srgb(color)
    bg.inputs["Strength"].default_value = strength


def _mesh(name: str, verts, faces, mat, parent=None, smooth: bool = False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", [smooth] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    link(obj, parent, mat)
    return obj


def cyclorama(name: str, mat, width: float = 12.0, back_y: float = 3.0, radius: float = 1.6, height: float = 7.0,
              front_y: float = -9.0, parent=None):
    """Infinite background: the floor curves up into the back wall (no horizon line, no corners)."""
    prof = [(front_y, 0.0), (back_y - radius, 0.0)]
    for i in range(1, 13):
        a = math.pi / 2 * i / 12
        prof.append((back_y - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((back_y, height))
    verts, faces = [], []
    for y, z in prof:
        verts += [(-width / 2, y, z), (width / 2, y, z)]
    for i in range(len(prof) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    return _mesh(name, verts, faces, mat, parent, smooth=True)


def area(name: str, loc, target, color: str, energy: float, size: float, size_y: float | None = None):
    import props

    return props.area_light(name, loc, target, color, energy, size, size_y)


# --- estudio ---------------------------------------------------------------------------------------------------

STUDIO = {"background": "#e8dcc8", "floor": None, "plinth": "#cbb89a", "plinth_on": True, "key": "#fff0dc"}


def estudio(timeline: dict | None = None) -> dict:
    """A plain studio (explainers, products): a curved backdrop in one colour, soft key/fill/rim light, and a plinth
    that lifts the thing to the human's head height."""
    o = _opts(timeline, STUDIO)
    root = empty("SET_estudio")
    bg = material("set_backdrop", o["background"], 0.9)
    cyclorama("backdrop", bg, parent=root)
    if o.get("floor"):
        floor = material("set_studio_floor", o["floor"], 0.85)
        _mesh("studio_floor", [(-6, -9, 0.001), (6, -9, 0.001), (6, 1.0, 0.001), (-6, 1.0, 0.001)], [(0, 1, 2, 3)], floor, root)
    plinth_h = 0.0
    if o.get("plinth_on", True):
        from rigs.thing import lathe_bm, to_object

        plinth_h = 0.86
        pm = material("set_plinth", o["plinth"], 0.7)
        p = to_object("plinth", lathe_bm([(0, 0), (0.3, 0), (0.3, plinth_h - 0.03), (0.285, plinth_h), (0, plinth_h)], 28, flat_front=False), pm)
        p.location = (0.42, 0.3, 0)
        p.parent = root
    _world(o["background"], 0.55)
    area("studio_key", (-2.2, -2.6, 3.0), (0.0, 0.3, 1.0), o["key"], 380, 2.2)
    area("studio_fill", (2.6, -2.2, 1.4), (0.0, 0.3, 1.0), "#e6eeff", 160, 2.5)
    area("studio_rim", (1.2, 2.4, 3.2), (0.0, 0.3, 1.2), "#ffffff", 260, 1.4)
    area("studio_top", (0.0, 0.2, 4.2), (0.0, 0.2, 0.0), "#fff6ea", 90, 3.0)
    top = plinth_h
    return {
        "slots": {"left": (-0.42, 0.25, 0.0), "right": (0.42, 0.3, top), "right_a": (0.32, 0.3, top), "right_b": (0.62, 0.36, top),
                  "sofa": (-1.25, 0.6, 0.0)},
        "facing": {"left": 16, "right": -22, "right_a": -18, "right_b": -30, "sofa": 22},
        "ai_scale": 0.85,
        "seated": [],
        "standing": True,
        "phone_spot": (-0.75, 0.35, 0.9),
        "phone_optional": True,
        "typing": False,
        "cameras": lambda heads, ais: _studio_cameras(heads, ais),
    }


def _human_cameras(heads: dict) -> dict:
    """A standing human: the close-up and the low medium shot from a little further than at the desk."""
    h = heads.get("novato")
    if h is None:
        return {}
    return {
        "closeup_novato": dict(loc=h + Vector((-0.4, -2.0, -0.1)), target=h + Vector((-0.1, 0, -0.16)), lens=40, fstop=2.2, follow="novato"),
        "medium_novato_low": dict(loc=h + Vector((-0.3, -2.1, -0.5)), target=h + Vector((0, 0, -0.3)), lens=32, fstop=2.8, follow="novato"),
    }


def _studio_cameras(heads: dict, ais: list[str]) -> dict:
    pts = list(heads.values())
    mid = sum(pts, Vector()) / len(pts)
    return {**_human_cameras(heads),
        # Arrives from further back in the studio (no galaxy here).
        "establishing": dict(loc=mid + Vector((0.12, -2.4, -0.05)), start=mid + Vector((0.6, -5.2, 0.6)), target=mid + Vector((0, 0, -0.2)),
                             lens=30, fstop=None),
        "wide_room": dict(loc=mid + Vector((0.2, -3.6, 0.6)), target=mid + Vector((0, 0.3, -0.45)), lens=26, fstop=None),
        "wide_space": dict(loc=mid + Vector((-0.4, -4.6, 0.3)), end=mid + Vector((-0.5, -5.6, 0.35)), target=mid + Vector((0, 0.2, -0.4)),
                           lens=32, fstop=None),
    }


# --- mostrador (café, bakery, shop) -------------------------------------------------------------------------

COUNTER = {"variant": "cafeteria", "wall": "#e2d2b6", "counter": "#7a4e33", "top": "#ece6da", "accent": "#2f6b5a",
           "floor": "#b79e7c", "daylight": True}


# --- the chalkboard: menu lines, or the script's own words in chalk ---------------------------------------------

CHALK_FONT = ROOT / "assets" / "fonts" / "PatrickHand-Regular.ttf"  # OFL, hand-written, with ñ, tildes, ¿ and ¡
CHALK_MAX_LINES = 4


def chalk_lines(o: dict) -> list[str]:
    """set_options "pizarra": the text of the board. Lines split by "|" or a line break; at most 4."""
    text = str(o.get("pizarra") or "").replace("\r", "")
    lines = [ln.strip() for part in text.split("|") for ln in part.split("\n")]
    return [ln for ln in lines if ln][:CHALK_MAX_LINES]


def chalkboard(root, center: tuple[float, float, float], frame_mat, o: dict, rng: random.Random) -> None:
    """A framed chalkboard on the wall at `center` (x, wall y, z). With set_options "pizarra", it says that text in
    chalk letters, as big as fits; without it, menu lines with no readable text (nothing to translate)."""
    from rigs.thing import box_bm, to_object

    x, wall_y, z = center
    w, h = 1.3, 0.8
    b = to_object("chalkboard", box_bm((w, 0.04, h), bevel=0.01), material("set_chalkboard", o.get("pizarra_fondo") or "#26302c", 0.9))
    b.location = (x, wall_y - 0.03, z)
    b.parent = root
    frame = to_object("chalk_frame", box_bm((w + 0.08, 0.035, h + 0.08), bevel=0.01), frame_mat)
    frame.location = (x, wall_y - 0.015, z)
    frame.parent = root
    chalk = material("set_chalk", o.get("pizarra_tiza") or "#e9e4d6", 0.9)
    lines = chalk_lines(o)
    if not lines:
        for r in range(4):  # menu lines in chalk (no readable text: nothing to translate)
            lw = rng.uniform(0.55, 0.9)
            ln = to_object(f"chalk_line_{r}", box_bm((lw, 0.01, 0.025)), chalk)
            ln.location = (x - (0.9 - lw) / 2 - 0.12, wall_y - 0.06, z + 0.23 - r * 0.15)
            ln.parent = root
            dot = to_object(f"chalk_price_{r}", box_bm((0.12, 0.01, 0.025)), chalk)
            dot.location = (x + 0.45, wall_y - 0.06, z + 0.23 - r * 0.15)
            dot.parent = root
        return
    # The lowest strip stays clear: on the café wall, the shelf's jars stand in front of it.
    chalk_text(lines, (x, wall_y - 0.056, z - 0.01), w - 0.16, h - 0.24, chalk, root)


def chalk_text(lines: list[str], center: tuple[float, float, float], max_w: float, max_h: float, mat, parent) -> list:
    """Flat letters (meshes, so the .blend needs no font file: the cloud machine has none), one object per line,
    centred on `center` facing the camera (-Y). Every line gets the same letter size: the largest that fits."""
    font = bpy.data.fonts.load(str(CHALK_FONT), check_existing=True) if CHALK_FONT.exists() else None
    pitch = max_h / len(lines)  # room per line
    size = pitch * 0.82
    curves = []
    for i, text in enumerate(lines):
        cu = bpy.data.curves.new(f"chalk_font_{i}", "FONT")  # temporary: becomes the mesh chalk_text_<i>
        cu.body = text
        if font:
            cu.font = font
        cu.size = size
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        ob = bpy.data.objects.new(f"chalk_font_{i}", cu)
        link(ob)
        curves.append(ob)
    bpy.context.view_layer.update()
    widest = max(ob.dimensions.x for ob in curves) or 1.0
    scale = min(1.0, max_w / widest)  # long lines shrink every line alike (a board in one hand)
    for ob in curves:
        ob.data.size = size * scale
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    out = []
    x, y, z = center
    top = z + pitch * scale * (len(lines) - 1) / 2
    for i, ob in enumerate(curves):
        mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph))
        mesh.materials.append(mat)
        me = bpy.data.objects.new(f"chalk_text_{i}", mesh)
        link(me)
        me.location = (x, y, top - i * pitch * scale)
        # Stand it on the wall facing the camera (-Y), with a slight hand-drawn tilt in its own plane.
        me.rotation_euler = (rad(90), rad(random.Random(i).uniform(-1.2, 1.2)), 0)
        me.parent = parent
        out.append(me)
        curve = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.curves.remove(curve)
    return out


def mostrador(timeline: dict | None = None) -> dict:
    """A shop counter by day, seen from the customer's side: the human works behind it, the thing stands on it.
    variant "cafeteria" (espresso machine, cups, cakes, chalkboard) or "obrador" (bakery/kitchen: oven, shelves,
    bread, flour sacks)."""
    import props
    from rigs.thing import box_bm, lathe_bm, to_object, ball_bm

    o = _opts(timeline, COUNTER)
    root = empty("SET_mostrador")
    K = props.kenney
    rng = random.Random(7)
    wall = material("set_shop_wall", o["wall"], 0.92)
    floor = material("set_shop_floor", o["floor"], 0.8)
    accent = material("set_shop_accent", o["accent"], 0.6)
    wood = material("set_shop_wood", o["counter"], 0.7)
    top_mat = material("set_shop_top", o["top"], 0.35)
    # Room: floor, back wall with a tiled lower half, side wall on the left with a big window (daylight comes in).
    _mesh("shop_floor", [(-4, -4, 0), (4, -4, 0), (4, 3.2, 0), (-4, 3.2, 0)], [(0, 1, 2, 3)], floor, root)
    back_y = 1.6
    _mesh("shop_wall", [(-4, back_y, 0), (4, back_y, 0), (4, back_y, 3.4), (-4, back_y, 3.4)], [(0, 3, 2, 1)], wall, root)
    tile = material("set_shop_tile", o["accent"], 0.35)
    tiles = []
    for i in range(-14, 15):  # a band of glossy tiles behind the counter, in rows (metro tiles)
        for j in range(5):
            x = i * 0.26 + (0.13 if j % 2 else 0.0)
            z = 0.95 + j * 0.13
            tiles.append(to_object(f"tile_{i}_{j}", box_bm((0.245, 0.02, 0.115), bevel=0.012, segments=1), tile))
            tiles[-1].location = (x, back_y - 0.012, z + 0.065)
            tiles[-1].parent = root
    side = material("set_shop_side", o["wall"], 0.92)
    _mesh("shop_side_wall", [(-2.6, -4, 0), (-2.6, 3.2, 0), (-2.6, 3.2, 3.4), (-2.6, -4, 3.4)], [(0, 1, 2, 3)], side, root)
    # Counter: a long wooden front with a pale top, across the frame; the human stands behind it.
    ch = 0.9
    to_object("counter_body", box_bm((3.6, 0.62, ch - 0.05), bevel=0.02, segments=1), wood).location = (0.2, 0.55, (ch - 0.05) / 2)
    bpy.data.objects["counter_body"].parent = root
    top = to_object("counter_top", box_bm((3.7, 0.7, 0.05), bevel=0.012, segments=1), top_mat)
    top.location = (0.2, 0.55, ch - 0.025)
    top.parent = root
    for i in range(9):  # vertical slats on the counter front
        slat = to_object(f"counter_slat_{i}", box_bm((0.06, 0.02, ch - 0.18), bevel=0.008, segments=1), accent if i % 4 == 0 else wood)
        slat.location = (-1.4 + i * 0.4, 0.235, (ch - 0.05) / 2)
        slat.parent = root
    kick = to_object("counter_kick", box_bm((3.6, 0.03, 0.09)), accent)
    kick.location = (0.2, 0.235, 0.045)
    kick.parent = root
    cafe = o.get("variant", "cafeteria") != "obrador"
    # Back: shelves, machines and goods (Kenney CC0 + simple shapes).
    if cafe:
        K("kitchenCoffeeMachine", (-0.95, 1.18, ch), 0, root, scale=1.6)
        chalkboard(root, (0.55, back_y, 2.25), wood, o, rng)
        cup = material("set_cup", "#f4efe6", 0.3)
        for i in range(5):  # stacked cups on the machine's shelf
            c = to_object(f"cup_{i}", lathe_bm([(0, 0), (0.035, 0), (0.045, 0.07), (0.04, 0.07), (0.03, 0.01), (0, 0.01)], 12), cup)
            c.location = (-1.35 + i * 0.1, 1.3, ch + 0.002)
            c.parent = root
        stand = material("set_cake_stand", "#f4efe6", 0.25)
        cake = material("set_cake", "#c98a5a", 0.8)
        icing = material("set_icing", "#f7e7da", 0.6)
        cs = to_object("cake_stand", lathe_bm([(0, 0), (0.07, 0), (0.025, 0.02), (0.02, 0.12), (0.17, 0.13), (0.17, 0.14), (0, 0.14)], 16), stand)
        cs.location = (1.25, 0.55, ch)
        cs.parent = root
        ck = to_object("cake", lathe_bm([(0, 0), (0.13, 0), (0.13, 0.09), (0, 0.09)], 16, flat_front=False), cake)
        ck.location = (1.25, 0.55, ch + 0.14)
        ck.parent = root
        ic = to_object("cake_icing", lathe_bm([(0.133, 0.06), (0.135, 0.095), (0.0, 0.1)], 16, cap_bottom=False, flat_front=False), icing)
        ic.location = (1.25, 0.55, ch + 0.14)
        ic.parent = root
    else:
        K("kitchenStove", (-1.3, 1.1, 0), 0, root, scale=1.9)
        K("hoodModern", (-1.3, 1.3, 1.65), 0, root, scale=1.9)
        if chalk_lines(o):  # the board takes the wall cupboard's place (where the café has it): it reads in two_shot
            chalkboard(root, (0.55, back_y, 2.25), wood, o, rng)
        else:
            K("kitchenCabinetUpperDouble", (0.3, 1.3, 1.6), 0, root, scale=1.9)
        bread = material("set_bread", "#c8843f", 0.85)
        crust = material("set_bread_dark", "#9a5a28", 0.85)
        for i in range(4):  # loaves on the counter's back edge
            loaf = to_object(f"loaf_{i}", ball_bm((0.12, 0.07, 0.06), 2), bread if i % 2 else crust)
            loaf.location = (0.95 + i * 0.22, 0.7, ch + 0.05)
            loaf.rotation_euler = (0, 0, rad(rng.uniform(-20, 20)))
            loaf.parent = root
        sack = material("set_sack", "#e2d6bd", 1.0)
        for i in range(2):
            s = to_object(f"flour_{i}", ball_bm((0.22, 0.16, 0.3), 2), sack)
            s.location = (1.7 + i * 0.32, 1.2, 0.28)
            s.parent = root
    # Shelf with jars/plants over the counter on the back wall.
    shelf = to_object("shelf", box_bm((1.6, 0.22, 0.04), bevel=0.008), wood)
    shelf.location = (-0.6, back_y - 0.12, 1.85)
    shelf.parent = root
    jar = material("set_jar", "#dfe9e6", 0.15)
    jam = [material("set_jar_a", "#c9542f", 0.5), material("set_jar_b", "#e2b33c", 0.5), material("set_jar_c", "#6c8f4a", 0.5)]
    for i in range(5):
        j = to_object(f"shelf_jar_{i}", lathe_bm([(0, 0), (0.06, 0), (0.065, 0.14), (0.04, 0.17), (0, 0.17)], 10), jam[i % 3] if i % 2 else jar)
        j.location = (-1.25 + i * 0.3, back_y - 0.12, 1.87)
        j.parent = root
    if not chalk_lines(o):  # its leaves would cover the board's words
        K("plantSmall2", (0.25, back_y - 0.12, 1.87), 0, root, scale=1.4)
    # Pendant lamps over the counter (warm, small: daylight does the work).
    lamps = (-0.8, 0.45, 1.6)
    if chalk_lines(o):
        lamps = (-0.8, 1.6)  # the middle one hangs in front of the board's words (wide shots)
    for i, x in enumerate(lamps):
        shade = to_object(f"pendant_{i}", lathe_bm([(0.0, 0.0), (0.2, 0.0), (0.16, 0.08), (0.06, 0.2), (0.02, 0.24), (0, 0.24)], 14, flat_front=False),
                          accent)
        shade.location = (x, 0.65, 2.25)
        shade.parent = root
        cord = to_object(f"pendant_cord_{i}", box_bm((0.01, 0.01, 1.0)), material("set_cord", "#222222", 0.8))
        cord.location = (x, 0.65, 2.98)
        cord.parent = root
        bulb = to_object(f"pendant_bulb_{i}", ball_bm((0.05, 0.05, 0.05), 2), material("set_pendant_bulb", "#ffe2b0", 0.3, emission=4.0))
        bulb.location = (x, 0.65, 2.22)
        bulb.parent = root
    # Window on the side wall: a bright opening (daylight), with a sill plant.
    win = material("set_window_light", "#fff6e0", 0.5, emission=2.2)
    _mesh("shop_window", [(-2.59, -1.2, 0.9), (-2.59, 0.9, 0.9), (-2.59, 0.9, 2.5), (-2.59, -1.2, 2.5)], [(0, 1, 2, 3)], win, root)
    K("pottedPlant", (-2.3, 1.25, 0), 0, root, scale=1.6)
    K("stoolBar", (-1.45, -0.2, 0), 0, root, scale=1.9)
    K("stoolBar", (2.0, -0.25, 0), 20, root, scale=1.9)
    # Light: sun through the window, sky fill, warm practicals. Names reuse escritorio's where it makes sense
    # (blender/moods.py multiplies lamp_key etc.).
    _world("#f3efe6" if o.get("daylight", True) else "#3b3a48", 0.38 if o.get("daylight", True) else 0.2)
    sun = bpy.data.lights.new("sun_key", "SUN")
    sun.energy = 2.2 if o.get("daylight", True) else 0.2
    sun.color = srgb("#fff1d8")[:3]
    sun.angle = rad(4)
    so = bpy.data.objects.new("sun_key", sun)
    link(so)
    so.rotation_euler = (rad(52), rad(-38), rad(-62))
    area("lamp_key", (-1.6, -2.2, 2.2), (0.0, 0.6, 1.3), "#fff2e0", 170, 2.0)
    area("room_fill", (2.4, -2.0, 1.8), (0.0, 0.6, 1.2), "#dfe8ff", 70, 3.0)
    area("window_bounce", (-2.4, -0.2, 1.7), (0.4, 0.4, 1.2), "#fff3dc", 120, 1.8)
    area("lamp_light", (0.4, 0.65, 2.1), (0.4, 0.6, 1.0), "#ffd29a", 60, 2.0)
    return {
        "slots": {"left": (-0.35, 0.98, 0.0), "right": (0.45, 0.5, ch), "right_a": (0.3, 0.48, ch), "right_b": (0.85, 0.52, ch),
                  "sofa": (1.6, -0.4, 0.0)},
        "facing": {"left": 14, "right": -28, "right_a": -20, "right_b": -40, "sofa": -30},
        "ai_scale": 0.95,
        "seated": [],
        "standing": True,
        "hands_spot": (-0.35, 0.66, ch),
        "typing": False,
        "phone_spot": (-0.05, 0.66, ch),
        "phone_optional": True,
        "desk_top": ch,
        "cameras": lambda heads, ais: _shop_cameras(heads, ais),
    }


def _shop_cameras(heads: dict, ais: list[str]) -> dict:
    pts = list(heads.values())
    mid = sum(pts, Vector()) / len(pts)
    return {**_human_cameras(heads),
        "establishing": dict(loc=mid + Vector((0.15, -2.3, -0.05)), start=mid + Vector((1.4, -5.0, 0.5)), target=mid + Vector((0, 0, -0.2)),
                             lens=30, fstop=None),
        "wide_room": dict(loc=mid + Vector((0.5, -3.6, 0.5)), target=mid + Vector((0.2, 0.5, -0.4)), lens=24, fstop=None),
        "wide_space": dict(loc=mid + Vector((0.6, -4.2, 0.2)), end=mid + Vector((0.8, -5.2, 0.3)), target=mid + Vector((0.2, 0.4, -0.3)),
                           lens=28, fstop=None),
    }


# --- exterior (park) ---------------------------------------------------------------------------------------------

PARK = {"grass": "#86b35c", "sky": "#c4e3f3", "path": "#dcc9a2", "trees": "#4f8a43", "bench": True, "stump": True}


def exterior(timeline: dict | None = None) -> dict:
    """A park by day (running, walks, outdoor niches): a grass island with a path, low-poly trees, a bench and sky."""
    import props
    from rigs.thing import ball_bm, lathe_bm, to_object

    o = _opts(timeline, PARK)
    root = empty("SET_exterior")
    rng = random.Random(11)
    grass = material("set_grass", o["grass"], 0.95)
    path = material("set_path", o["path"], 0.95)
    g = to_object("park_ground", lathe_bm([(0, -0.3), (9.0, -0.3), (9.0, 0.0), (0, 0.0)], 40, flat_front=False), grass)
    g.parent = root
    pv = []
    for i in range(24):  # a winding path from the front to the back
        t = i / 23
        x = 0.9 * math.sin(t * 3.2) - 0.1
        y = -4.0 + t * 12.0
        pv.append((x - 0.6, y, 0.004))
        pv.append((x + 0.6, y, 0.004))
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(23)]
    _mesh("park_path", pv, faces, path, root)
    leaves = [material("set_tree_a", o["trees"], 0.9), material("set_tree_b", "#6aa04c", 0.9)]
    trunk = material("set_trunk", "#6b4a33", 0.9)
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.6, 7.5)
        x, y = r * math.cos(a), abs(r * math.sin(a)) + 0.8
        h = rng.uniform(1.6, 3.0)
        t = to_object(f"tree_trunk_{i}", lathe_bm([(0, 0), (0.09, 0), (0.07, h * 0.5), (0, h * 0.5)], 6), trunk)
        t.location = (x, y, 0)
        t.parent = root
        crown = to_object(f"tree_crown_{i}", ball_bm((h * 0.33, h * 0.33, h * 0.42), 1), leaves[i % 2])
        crown.location = (x, y, h * 0.75)
        crown.parent = root
    if o.get("bench", True):
        props.kenney("bench", (-0.3, 1.3, 0), 0, root, scale=1.9)
    props.kenney("lampRoundFloor", (1.6, 1.6, 0), 0, root, scale=1.9)
    # A tree stump lifts the thing to a readable height next to the human (off with "stump": false).
    stump_h = 0.0
    if o.get("stump", True):
        stump_h = 0.62
        wood = material("set_stump", "#8a6040", 0.9)
        rings = material("set_stump_top", "#d8b98a", 0.85)
        st = to_object("stump", lathe_bm([(0, 0), (0.34, 0), (0.29, 0.08), (0.27, stump_h - 0.02), (0.26, stump_h), (0, stump_h)], 9), wood)
        st.location = (0.45, 0.35, 0)
        st.parent = root
        top = to_object("stump_top", lathe_bm([(0, stump_h + 0.001), (0.255, stump_h + 0.001)], 9, cap_bottom=False, cap_top=False), rings)
        top.location = (0.45, 0.35, 0)
        top.parent = root
    _world(o["sky"], 1.0)
    sun = bpy.data.lights.new("sun_key", "SUN")
    sun.energy = 3.6
    sun.color = srgb("#fff0d6")[:3]
    sun.angle = rad(3)
    so = bpy.data.objects.new("sun_key", sun)
    link(so)
    so.rotation_euler = (rad(48), rad(-20), rad(-35))
    area("room_fill", (2.0, -3.0, 2.0), (0.0, 0.5, 1.0), "#dfeaff", 140, 4.0)
    return {
        "slots": {"left": (-0.4, 0.4, 0.0), "right": (0.45, 0.35, stump_h), "right_a": (0.36, 0.35, stump_h), "right_b": (0.85, 0.5, 0.0),
                  "sofa": (-0.3, 1.25, 0.0)},
        "facing": {"left": 16, "right": -24, "right_a": -18, "right_b": -32, "sofa": 0},
        "ai_scale": 1.0,
        "seated": [],
        "standing": True,
        "typing": False,
        "phone_spot": (-0.75, 0.3, 0.95),
        "phone_optional": True,
        "cameras": lambda heads, ais: _studio_cameras(heads, ais),
    }
