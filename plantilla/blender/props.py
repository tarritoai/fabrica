"""Set dressing: Kenney CC0 furniture, plus props built by code (laptop, phone, window, city, fairy lights).

Kenney models (assets/vendor/kenney_furniture, CC0) are authored at ~1 unit = 0.5 m, so they are
imported at KENNEY_SCALE. Props that animate (laptop lid, phone) are built here so their pivots
are known.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from lib import ROOT, bake, empty, link, material, primitive, rad, srgb

KENNEY_DIR = ROOT / "assets/vendor/kenney_furniture/Models/GLTF format"
KENNEY_SCALE = 1.95


def kenney(name: str, location, yaw: float = 0.0, parent=None, scale: float = KENNEY_SCALE, tint: dict | None = None):
    """Import a Kenney model under an empty at `location` (floor contact), rotated `yaw` degrees.

    `tint` maps Kenney material names ("wood", "carpet"…) to our hex colours.
    """
    holder = empty(f"K_{name}", location, parent)
    holder.rotation_euler = (0, 0, rad(yaw))
    holder.scale = (scale, scale, scale)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(KENNEY_DIR / f"{name}.glb"))
    objs = [o for o in bpy.data.objects if o not in before]
    for obj in objs:
        if obj.parent is None:
            link(obj)
            obj.parent = holder
        if obj.type == "MESH" and tint:
            for slot in obj.material_slots:
                base = slot.material.name.split(".")[0] if slot.material else None
                if base in tint:
                    slot.material = material(f"k_{base}_{tint[base]}", tint[base], 0.8)
    return holder


# --- procedural textures -----------------------------------------------------------


def code_image(name: str = "code_screen", w: int = 320, h: int = 200, seed: int = 4) -> bpy.types.Image:
    """Dark editor with coloured fake code lines and a red error underline (a bug)."""
    img = bpy.data.images.new(name, w, h)
    rng = random.Random(seed)
    bg = (0.012, 0.016, 0.03, 1.0)
    px = [bg] * (w * h)
    palette = [srgb("#c792ea"), srgb("#82aaff"), srgb("#c3e88d"), srgb("#f78c6c"), srgb("#a6accd"), srgb("#89ddff")]
    line_h, y = 9, h - 14
    indent = 0
    n = 0
    while y > 6:
        if rng.random() < 0.12:
            y -= line_h
            n += 1
            continue
        indent = max(0, min(4, indent + rng.choice((-1, 0, 0, 1))))
        x = 10 + indent * 10
        for _ in range(rng.randint(1, 5)):
            tw = rng.randint(6, 34)
            col = rng.choice(palette)
            for yy in range(y, y + 3):
                for xx in range(x, min(w - 6, x + tw)):
                    px[yy * w + xx] = col
            x += tw + 5
            if x > w - 20:
                break
        if n == 9:  # the bug: red squiggle under this line
            for xx in range(10 + indent * 10, min(w - 10, x)):
                px[(y - 2) * w + xx] = srgb("#ff4d4d")
        # line number gutter
        for yy in range(y, y + 3):
            for xx in range(2, 6):
                px[yy * w + xx] = (0.08, 0.09, 0.12, 1.0)
        y -= line_h
        n += 1
    img.pixels.foreach_set([c for p in px for c in p])
    img.pack()
    return img


def notes_image(name: str = "notes_screen", w: int = 320, h: int = 200, seed: int = 7) -> bpy.types.Image:
    """Study notes open on the laptop: a warm-white page, a title bar, grey 'text' lines, one highlighted line and a
    small diagram box (no words, no app, no brand)."""
    img = bpy.data.images.new(name, w, h)
    rng = random.Random(seed)
    paper = srgb("#e9e4d8")
    px = [paper] * (w * h)

    def rect(x0, y0, x1, y1, col):
        for yy in range(max(0, y0), min(h, y1)):
            for xx in range(max(0, x0), min(w, x1)):
                px[yy * w + xx] = col

    rect(0, h - 14, w, h, srgb("#3d4a63"))  # the viewer's bar
    rect(24, h - 34, 150, h - 26, srgb("#2b2f3a"))  # the heading
    y = h - 48
    n = 0
    while y > 12:
        if n == 5:
            rect(200, y - 40, 296, y + 4, srgb("#d6dbe6"))  # a diagram box on the right
        right = 180 if 5 <= n <= 9 else 296
        x = 24
        while x < right - 20:
            tw = rng.randint(10, 40)
            rect(x, y, min(right, x + tw), y + 3, srgb("#7d8494"))
            x += tw + 4
        if n == 3:
            rect(22, y - 2, right, y + 5, srgb("#f2d64b"))
            x = 24
            while x < right - 20:
                tw = rng.randint(10, 40)
                rect(x, y, min(right, x + tw), y + 3, srgb("#5d6474"))
                x += tw + 4
        y -= 10
        n += 1
    img.pixels.foreach_set([c for p in px for c in p])
    img.pack()
    return img


def emissive_image_material(name: str, image: bpy.types.Image, strength: float) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = strength
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def city_material() -> bpy.types.Material:
    """Building facades: a brick grid becomes windows, a noise mask switches some on."""
    mat = bpy.data.materials.new("city_facade")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    coord = nodes.new("ShaderNodeTexCoord")
    brick = nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 5.0
    brick.inputs["Mortar Size"].default_value = 0.18
    brick.offset = 0.0
    brick.inputs["Brick Width"].default_value = 0.5
    brick.inputs["Row Height"].default_value = 0.45
    brick.inputs["Color1"].default_value = srgb("#ffcf8a")
    brick.inputs["Color2"].default_value = srgb("#9fc0ff")
    brick.inputs["Mortar"].default_value = (0, 0, 0, 1)
    noise = nodes.new("ShaderNodeTexWhiteNoise")
    noise.noise_dimensions = "3D"
    snap = nodes.new("ShaderNodeVectorMath")
    snap.operation = "SNAP"
    snap.inputs[1].default_value = (0.11, 0.11, 0.1)
    ramp = nodes.new("ShaderNodeMath")
    ramp.operation = "GREATER_THAN"
    ramp.inputs[1].default_value = 0.78
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul2 = nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 9.0
    emit = nodes.new("ShaderNodeEmission")
    base = nodes.new("ShaderNodeBsdfPrincipled")
    base.inputs["Base Color"].default_value = srgb("#0a0e1a")
    add = nodes.new("ShaderNodeAddShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(coord.outputs["Object"], brick.inputs["Vector"])
    links.new(coord.outputs["Object"], snap.inputs[0])
    links.new(snap.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Value"], ramp.inputs[0])
    links.new(ramp.outputs["Value"], mul.inputs[0])
    links.new(brick.outputs["Fac"], mul.inputs[1])
    # brick Fac is 1 in mortar: invert by using (1 - fac)
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(brick.outputs["Fac"], inv.inputs[1])
    links.new(inv.outputs["Value"], mul.inputs[1])
    links.new(mul.outputs["Value"], mul2.inputs[0])
    links.new(brick.outputs["Color"], emit.inputs["Color"])
    links.new(mul2.outputs["Value"], emit.inputs["Strength"])
    links.new(base.outputs["BSDF"], add.inputs[0])
    links.new(emit.outputs["Emission"], add.inputs[1])
    links.new(add.outputs["Shader"], out.inputs["Surface"])
    return mat


def rain_glass_material(total_frames: int, fps: int) -> bpy.types.Material:
    """Mostly clear glass with bright droplets that slide down (mapping offset animated)."""
    mat = bpy.data.materials.new("rain_glass")
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 0.35, 1.0)
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 26.0
    vor.feature = "F1"
    drop = nodes.new("ShaderNodeMapRange")
    drop.inputs["From Min"].default_value = 0.0
    drop.inputs["From Max"].default_value = 0.07
    drop.inputs["To Min"].default_value = 1.0
    drop.inputs["To Max"].default_value = 0.0
    drop.clamp = True
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = srgb("#bcd4ff")
    emit.inputs["Strength"].default_value = 1.6
    transp = nodes.new("ShaderNodeBsdfTransparent")
    tint = nodes.new("ShaderNodeBsdfPrincipled")
    tint.inputs["Base Color"].default_value = srgb("#22324f")
    tint.inputs["Roughness"].default_value = 0.35
    mix_glass = nodes.new("ShaderNodeMixShader")
    mix_glass.inputs["Fac"].default_value = 0.05
    mix = nodes.new("ShaderNodeMixShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], vor.inputs["Vector"])
    links.new(vor.outputs["Distance"], drop.inputs["Value"])
    links.new(transp.outputs["BSDF"], mix_glass.inputs[1])
    links.new(tint.outputs["BSDF"], mix_glass.inputs[2])
    links.new(drop.outputs["Result"], mix.inputs["Fac"])
    links.new(mix_glass.outputs["Shader"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    # Droplets slide down slowly (simple-expression driver: no Python needed at render time).
    drv = mapping.inputs["Location"].driver_add("default_value", 2).driver
    drv.type = "SCRIPTED"
    drv.expression = f"frame * {0.035 / fps:.6f}"
    return mat


# --- props built by code -----------------------------------------------------------


def laptop(location, yaw: float, parent=None, screen: str = "codigo") -> dict:
    """Laptop with a hinged lid (`laptop_lid` pivot at the hinge) and a screen: code ("codigo") or study notes ("apuntes")."""
    root = empty("LAPTOP", location, parent)
    root.rotation_euler = (0, 0, rad(yaw))
    body_mat = material("laptop_alu", "#8b9099", 0.45)
    dark = material("laptop_dark", "#1a1c21", 0.6)
    base = primitive("cube", "laptop_base", (0, 0, 0.009), (0.17, 0.115, 0.009), root, body_mat)
    base.modifiers.new("bevel", "BEVEL").width = 0.004
    primitive("cube", "laptop_keys", (0, -0.01, 0.0185), (0.15, 0.06, 0.0008), root, dark)
    # Hinge at the back edge (+Y); the lid's screen faces -Y (towards whoever sits in front).
    hinge = empty("laptop_lid", (0, 0.112, 0.018), root)
    hinge.rotation_euler = (rad(-15), 0, 0)
    lid = primitive("cube", "laptop_lid_shell", (0, 0, 0.115), (0.17, 0.006, 0.115), hinge, body_mat)
    lid.modifiers.new("bevel", "BEVEL").width = 0.004
    image = notes_image() if screen == "apuntes" else code_image()
    screen_mat = emissive_image_material("laptop_screen", image, 1.6 if screen == "apuntes" else 2.2)
    screen = primitive("plane", "laptop_screen", (0, -0.0065, 0.118), (0.158, 0.104, 1), hinge, screen_mat)
    screen.rotation_euler = (rad(90), 0, 0)
    return {"root": root, "lid": hinge, "screen": screen}


PHONE_SCALE = 1.6  # cartoon proportions: the heads are big, a real-size phone disappears


def phone(name: str = "PHONE") -> bpy.types.Object:
    """Phone root: local +Z = screen normal, +Y = top of the phone. Screens are added by build_scene."""
    root = empty(name)
    root.scale = (PHONE_SCALE,) * 3
    case = primitive("cube", "phone_case", (0, 0, -0.006), (0.038, 0.078, 0.005), root, material("phone_case", "#111216", 0.4))
    case.modifiers.new("bevel", "BEVEL").width = 0.003
    primitive("plane", "phone_glass_off", (0, 0, 0.0002), (0.035, 0.073, 1), root, material("phone_glass_off", "#05060a", 0.15))
    return root


def mug(location, parent=None) -> None:
    m = material("mug", "#d9d3c7", 0.5)
    primitive("cylinder", "mug_body", (location[0], location[1], location[2] + 0.05), (0.04, 0.04, 0.05), parent, m, vertices=12)
    primitive("cylinder", "mug_coffee", (location[0], location[1], location[2] + 0.093), (0.035, 0.035, 0.003), parent, material("coffee", "#2a160c", 0.2), vertices=12)
    h = primitive("torus", "mug_handle", (location[0] + 0.045, location[1], location[2] + 0.05), (1, 1, 1), parent, m,
                  major_radius=0.022, minor_radius=0.006, major_segments=10, minor_segments=5)
    h.rotation_euler = (rad(90), 0, 0)


def fairy_lights(start, end, sag: float, count: int, parent=None) -> None:
    """Warm bulbs on a sagging wire: big soft bokeh when out of focus."""
    a, b = Vector(start), Vector(end)
    bulb = material("fairy_bulb", "#ffc46b", 0.4, emission=9.0)
    wire = material("fairy_wire", "#1c1a17", 0.8)
    pts = []
    for i in range(count):
        t = i / (count - 1)
        p = a.lerp(b, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
        primitive("uv_sphere", f"fairy_{i}", tuple(p), (0.018, 0.018, 0.022), parent, bulb, segments=8, ring_count=5)
    for i, (p, q) in enumerate(zip(pts, pts[1:])):
        mid = (p + q) / 2
        d = q - p
        seg = primitive("cylinder", f"fairy_wire_{i}", tuple(mid), (0.002, 0.002, d.length / 2), parent, wire, vertices=4)
        seg.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def poster(name: str, location, size, colors: list[str], parent=None) -> None:
    """Framed poster on the back wall (faces -Y): flat colour blocks, no real brand."""
    w, h = size
    primitive("cube", f"{name}_frame", location, (w / 2 + 0.015, 0.008, h / 2 + 0.015), parent, material("poster_frame", "#14161b", 0.6))
    x, y, z = location
    rng = random.Random(name)
    primitive("cube", f"{name}_bg", (x, y - 0.009, z), (w / 2, 0.001, h / 2), parent, material(f"{name}_bg", colors[0], 0.9))
    for i, c in enumerate(colors[1:]):
        bw, bh = w * rng.uniform(0.2, 0.6), h * rng.uniform(0.08, 0.3)
        bx = x + rng.uniform(-w / 2 + bw / 2, w / 2 - bw / 2)
        bz = z + rng.uniform(-h / 2 + bh / 2, h / 2 - bh / 2)
        primitive("cube", f"{name}_shape_{i}", (bx, y - 0.0105, bz), (bw / 2, 0.001, bh / 2), parent, material(f"{name}_c{i}", c, 0.9))


def point_light(name: str, location, color: str, energy: float, radius: float = 0.05):
    data = bpy.data.lights.new(name, "POINT")
    data.color = srgb(color)[:3]
    data.energy = energy
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj


def area_light(name: str, location, target, color: str, energy: float, size: float, size_y: float | None = None):
    from lib import look_at

    data = bpy.data.lights.new(name, "AREA")
    data.color = srgb(color)[:3]
    data.energy = energy
    if size_y:
        data.shape = "RECTANGLE"
        data.size, data.size_y = size, size_y
    else:
        data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def _galaxy_graph(nodes, links, vec, band_normal, band_offset: float, band_width: float,
                  neb_scale: float, warp_scale: float, star_scales: tuple[float, float]):
    """Shared node graph: nebula band + two star layers over a dark blue base. Returns a colour socket."""
    band_dir = nodes.new("ShaderNodeVectorMath")
    band_dir.operation = "DOT_PRODUCT"
    band_dir.inputs[1].default_value = band_normal
    links.new(vec, band_dir.inputs[0])
    warp = nodes.new("ShaderNodeTexNoise")
    warp.inputs["Scale"].default_value = warp_scale
    warp.inputs["Detail"].default_value = 4.0
    links.new(vec, warp.inputs["Vector"])
    shift = nodes.new("ShaderNodeMath")
    shift.operation = "MULTIPLY_ADD"
    shift.inputs[1].default_value = 0.25
    links.new(warp.outputs["Fac"], shift.inputs[0])
    links.new(band_dir.outputs["Value"], shift.inputs[2])
    off = nodes.new("ShaderNodeMath")
    off.operation = "SUBTRACT"
    off.inputs[1].default_value = band_offset
    links.new(shift.outputs["Value"], off.inputs[0])
    dist = nodes.new("ShaderNodeMath")
    dist.operation = "ABSOLUTE"
    links.new(off.outputs["Value"], dist.inputs[0])
    band = nodes.new("ShaderNodeMapRange")
    band.inputs["From Min"].default_value = 0.0
    band.inputs["From Max"].default_value = band_width
    band.inputs["To Min"].default_value = 1.0
    band.inputs["To Max"].default_value = 0.0
    links.new(dist.outputs["Value"], band.inputs["Value"])

    neb = nodes.new("ShaderNodeTexNoise")
    neb.inputs["Scale"].default_value = neb_scale
    neb.inputs["Detail"].default_value = 8.0
    neb.inputs["Distortion"].default_value = 1.2
    links.new(vec, neb.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.28, srgb("#0b0f2a")
    els[1].position, els[1].color = 0.68, srgb("#46c4e0")
    for pos, col in ((0.4, "#5a2a9a"), (0.5, "#d04aa0"), (0.59, "#ff9a7a")):
        e = els.new(pos)
        e.color = srgb(col)
    links.new(neb.outputs["Fac"], ramp.inputs["Fac"])
    neb_amt = nodes.new("ShaderNodeMath")
    neb_amt.operation = "MULTIPLY"
    neb_amt.inputs[1].default_value = 3.0
    links.new(band.outputs["Result"], neb_amt.inputs[0])
    neb_col = nodes.new("ShaderNodeVectorMath")
    neb_col.operation = "SCALE"
    links.new(ramp.outputs["Color"], neb_col.inputs[0])
    links.new(neb_amt.outputs["Value"], neb_col.inputs["Scale"])

    def stars(scale: float, size: float, gain: float):
        vor = nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        vor.inputs["Randomness"].default_value = 1.0
        links.new(vec, vor.inputs["Vector"])
        pt = nodes.new("ShaderNodeMapRange")
        pt.inputs["From Min"].default_value = 0.0
        pt.inputs["From Max"].default_value = size
        pt.inputs["To Min"].default_value = gain
        pt.inputs["To Max"].default_value = 0.0
        links.new(vor.outputs["Distance"], pt.inputs["Value"])
        return pt

    small, big = stars(star_scales[0], 0.07, 4.0), stars(star_scales[1], 0.045, 9.0)
    star_sum = nodes.new("ShaderNodeMath")
    star_sum.operation = "ADD"
    links.new(small.outputs["Result"], star_sum.inputs[0])
    links.new(big.outputs["Result"], star_sum.inputs[1])
    star_col = nodes.new("ShaderNodeVectorMath")
    star_col.operation = "SCALE"
    star_col.inputs[0].default_value = srgb("#eaf0ff")[:3]
    links.new(star_sum.outputs["Value"], star_col.inputs["Scale"])
    total = nodes.new("ShaderNodeVectorMath")
    total.operation = "ADD"
    links.new(neb_col.outputs["Vector"], total.inputs[0])
    links.new(star_col.outputs["Vector"], total.inputs[1])
    base = nodes.new("ShaderNodeVectorMath")
    base.operation = "ADD"
    base.inputs[1].default_value = srgb("#070a1c")[:3]
    links.new(total.outputs["Vector"], base.inputs[0])
    return base.outputs["Vector"]


def galaxy_material(fps: int) -> bpy.types.Material:
    """Night sky on a plane (seen through a window): galaxy band and stars, drifting sideways."""
    mat = bpy.data.materials.new("galaxy_sky")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    drv = mapping.inputs["Location"].driver_add("default_value", 0).driver
    drv.type = "SCRIPTED"
    drv.expression = f"frame * {0.004 / fps:.7f}"
    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    color = _galaxy_graph(nodes, links, mapping.outputs["Vector"], (0.55, 0.85, 0.0), 0.13, 0.16, 6.0, 3.0, (180.0, 40.0))
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.25
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(color, emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def galaxy_world(fps: int, strength: float = 1.0, ambient: str = "#141b3a", ambient_strength: float = 0.5) -> None:
    """The whole world is a layered galaxy (camera rays only), turning slowly.

    Layers: violet-navy gradient, faint large clouds, a nebula band (colour clouds x fine wisps) cut by dark
    dust lanes, a warm core glow, and three star layers (fine white, coloured, a few big bright ones).
    For lighting the scene it is just a dim blue ambient.
    """
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()

    def node(kind, **inputs):
        n = nodes.new(kind)
        for k, v in inputs.items():
            if isinstance(v, bpy.types.NodeSocket):
                links.new(v, n.inputs[k])
            else:
                n.inputs[k].default_value = v
        return n

    def math(op, a, b=None, **kw):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        for idx, val in enumerate((a, b)):
            if val is None:
                continue
            if isinstance(val, bpy.types.NodeSocket):
                links.new(val, n.inputs[idx])
            else:
                n.inputs[idx].default_value = val
        return n.outputs[0]

    def vmath(op, a, b):
        n = nodes.new("ShaderNodeVectorMath")
        n.operation = op
        for idx, val in enumerate((a, b)):
            if isinstance(val, bpy.types.NodeSocket):
                links.new(val, n.inputs[idx])
            else:
                n.inputs[idx].default_value = val
        return n.outputs["Value"] if op == "DOT_PRODUCT" else n.outputs["Vector"]

    def scale(color, amount):
        n = nodes.new("ShaderNodeVectorMath")
        n.operation = "SCALE"
        links.new(color, n.inputs[0]) if isinstance(color, bpy.types.NodeSocket) else setattr(n.inputs[0], "default_value", color)
        links.new(amount, n.inputs["Scale"]) if isinstance(amount, bpy.types.NodeSocket) else setattr(n.inputs["Scale"], "default_value", amount)
        return n.outputs["Vector"]

    def ramp(fac, stops):
        n = nodes.new("ShaderNodeValToRGB")
        els = n.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], srgb(stops[0][1])
        els[1].position, els[1].color = stops[-1][0], srgb(stops[-1][1])
        for pos, col in stops[1:-1]:
            e = els.new(pos)
            e.color = srgb(col)
        links.new(fac, n.inputs["Fac"])
        return n.outputs["Color"]

    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.vector_type = "VECTOR"
    drv = mapping.inputs["Rotation"].driver_add("default_value", 2).driver
    drv.type = "SCRIPTED"
    drv.expression = f"frame * {0.012 / fps:.7f}"  # ~0.7 deg per second
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    vec = mapping.outputs["Vector"]

    # 1. Gradient background: navy below, deep violet above.
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(vec, sep.inputs[0])
    bg = ramp(math("ADD", math("MULTIPLY", sep.outputs["Z"], 0.5), 0.5),
              [(0.0, "#04060f"), (0.55, "#0a0d24"), (1.0, "#160c2c")])

    # 2. Faint large clouds everywhere.
    big = node("ShaderNodeTexNoise", Vector=vec, Scale=1.3, Detail=3.0)
    clouds = scale(ramp(big.outputs["Fac"], [(0.35, "#000000"), (0.6, "#1d1a4a"), (0.8, "#3a1f55")]), 0.5)

    # 3. The band: distance to a great circle, warped.
    band_dot = vmath("DOT_PRODUCT", vec, (0.62, 0.0, 0.78))
    warp = node("ShaderNodeTexNoise", Vector=vec, Scale=1.8, Detail=4.0)
    off = math("ABSOLUTE", math("ADD", band_dot, math("MULTIPLY", math("SUBTRACT", warp.outputs["Fac"], 0.5), 0.35)))
    band = node("ShaderNodeMapRange", Value=off, **{"From Min": 0.0, "From Max": 0.26, "To Min": 1.0, "To Max": 0.0})
    band_soft = math("POWER", band.outputs["Result"], 1.6)
    neb = node("ShaderNodeTexNoise", Vector=vec, Scale=3.2, Detail=6.0, Distortion=0.8)
    neb_col = ramp(neb.outputs["Fac"], [(0.3, "#1a0b40"), (0.42, "#6a1fb0"), (0.52, "#e0309a"), (0.6, "#ff7a5a"), (0.7, "#20c0e0")])
    wisps = node("ShaderNodeTexNoise", Vector=vec, Scale=11.0, Detail=10.0, Roughness=0.65, Distortion=0.4)
    wisp_amt = node("ShaderNodeMapRange", Value=wisps.outputs["Fac"], **{"From Min": 0.35, "From Max": 0.75, "To Min": 0.35, "To Max": 1.4})
    # Dark dust lanes inside the band.
    dust = node("ShaderNodeTexNoise", Vector=vec, Scale=6.5, Detail=8.0, Distortion=1.5)
    dust_mask = node("ShaderNodeMapRange", Value=dust.outputs["Fac"], **{"From Min": 0.45, "From Max": 0.6, "To Min": 0.15, "To Max": 1.0})
    band_amt = math("MULTIPLY", math("MULTIPLY", math("MULTIPLY", band_soft, wisp_amt.outputs["Result"]), dust_mask.outputs["Result"]), 0.65)
    band_col = scale(neb_col, band_amt)

    # 4. Warm core glow where the band is brightest.
    core_dir = vmath("DOT_PRODUCT", vec, (-0.35, 0.85, 0.4))
    core = node("ShaderNodeMapRange", Value=core_dir, **{"From Min": 0.55, "From Max": 1.0, "To Min": 0.0, "To Max": 1.0})
    core_amt = math("MULTIPLY", math("POWER", core.outputs["Result"], 2.0), math("MULTIPLY", band_soft, 0.5))
    core_col = scale((1.0, 0.78, 0.62), core_amt)

    # 5. Stars: fine white, coloured medium, a few big bright ones.
    def stars(sc, size, gain, colored=False):
        v = node("ShaderNodeTexVoronoi", Vector=vec, Scale=sc, Randomness=1.0)
        pt = node("ShaderNodeMapRange", Value=v.outputs["Distance"], **{"From Min": 0.0, "From Max": size, "To Min": gain, "To Max": 0.0})
        twinkle = node("ShaderNodeMapRange", Value=v.outputs["Distance"], **{"From Min": 0.0, "From Max": size * 3, "To Min": gain * 0.08, "To Max": 0.0})
        amt = math("ADD", math("POWER", pt.outputs["Result"], 1.5), twinkle.outputs["Result"])
        if colored:
            mixc = nodes.new("ShaderNodeMix")
            mixc.data_type = "RGBA"
            mixc.inputs[0].default_value = 0.45
            mixc.inputs[6].default_value = (1, 1, 1, 1)
            links.new(v.outputs["Color"], mixc.inputs[7])
            return scale(mixc.outputs[2], amt)
        return scale((0.92, 0.95, 1.0), amt)

    fine = stars(320.0, 0.06, 2.2)
    mid = stars(90.0, 0.05, 5.0, colored=True)
    bright = stars(22.0, 0.025, 14.0)
    total = bg
    for layer in (clouds, band_col, core_col, fine, mid, bright):
        total = vmath("ADD", total, layer)

    sky = nodes.new("ShaderNodeBackground")
    sky.inputs["Strength"].default_value = strength
    links.new(total, sky.inputs["Color"])
    amb = nodes.new("ShaderNodeBackground")
    amb.inputs["Color"].default_value = srgb(ambient)
    amb.inputs["Strength"].default_value = ambient_strength
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(amb.outputs["Background"], mix.inputs[1])
    links.new(sky.outputs["Background"], mix.inputs[2])
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(mix.outputs["Shader"], out.inputs["Surface"])


def floating_island(root, center, half_x: float, half_y: float, depth: float, floor_mat, seed: int = 4):
    """The room's ground as a chunk of rock floating in space: flat squircle top (the floor), a dirt band,
    then rocky low-poly layers tapering to a point."""
    import bmesh

    rng = random.Random(seed)
    n_seg = 40
    rings = [  # (z, scale, jitter)
        (0.0, 1.0, 0.0),
        (-0.14, 1.0, 0.01),
        (-0.45, 0.9, 0.06),
        (-0.95, 0.66, 0.09),
        (-1.5, 0.36, 0.08),
    ]
    bm = bmesh.new()
    grid = []
    for z, k, jit in rings:
        ring = []
        for i in range(n_seg):
            a = 2 * math.pi * i / n_seg
            c, s_ = math.cos(a), math.sin(a)
            x = half_x * math.copysign(abs(c) ** 0.5, c)  # squircle: near-rectangular, rounded corners
            y = half_y * math.copysign(abs(s_) ** 0.5, s_)
            j = 1 + rng.uniform(-jit, jit)
            ring.append(bm.verts.new((center[0] + x * k * j, center[1] + y * k * j, center[2] + z * depth / 1.5 + rng.uniform(-jit, jit) * 0.3)))
        grid.append(ring)
    tip = bm.verts.new((center[0] + rng.uniform(-0.2, 0.2), center[1] + rng.uniform(-0.2, 0.2), center[2] - depth))
    top = bm.faces.new(grid[0])
    sides = []
    for r0, r1 in zip(grid, grid[1:]):
        for i in range(n_seg):
            sides.append(bm.faces.new((r0[i], r0[(i + 1) % n_seg], r1[(i + 1) % n_seg], r1[i])))
    for i in range(n_seg):
        sides.append(bm.faces.new((grid[-1][i], grid[-1][(i + 1) % n_seg], tip)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("island")
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    island = bpy.data.objects.new("island", mesh)
    link(island, root)
    dirt = material("island_dirt", "#3a2a22", 0.95)
    rock = material("island_rock", "#221d2b", 0.9)
    mesh.materials.append(floor_mat)
    mesh.materials.append(dirt)
    mesh.materials.append(rock)
    for poly in mesh.polygons:
        if poly.normal.z > 0.95 and poly.center.z > center[2] - 0.01:
            poly.material_index = 0
        elif poly.center.z > center[2] - 0.14 * depth / 1.5 - 0.01:
            poly.material_index = 1
        else:
            poly.material_index = 2
    return island


def floating_rocks(root, count: int, region, seed: int = 8):
    """Small rocks and a couple of stray books drifting around the island (they bob slowly)."""
    rng = random.Random(seed)
    rock = material("island_rock", "#221d2b", 0.9)
    (x0, x1), (y0, y1), (z0, z1) = region
    out = []
    for i in range(count):
        loc = (rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(z0, z1))
        r = rng.uniform(0.06, 0.22)
        obj = primitive("ico_sphere", f"space_rock_{i}", loc, (r, r * rng.uniform(0.7, 1.1), r * rng.uniform(0.6, 0.9)), root, rock, subdivisions=1)
        obj.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        out.append(obj)
    return out


def broken_wall(root, name: str, start, direction, length: float, height: float, profile, plaster, brick_mat,
                seed: int = 1, thickness: float = 0.12, brick=(0.24, 0.14), floaters: int = 3):
    """A plaster wall built from brick cells, its top/end crumbling along `profile(t)` (t in 0..1 along the wall,
    returns the height fraction). Cells next to the break show exposed brick; a few loose bricks float off."""
    import bmesh

    rng = random.Random(seed)
    start, direction = Vector(start), Vector(direction).normalized()
    side = Vector((-direction.y, direction.x, 0))
    bw, bh = brick
    cols, rows = max(1, round(length / bw)), max(1, round(height / bh))
    bw, bh = length / cols, height / rows
    tops = []
    for c in range(cols):
        t = (c + 0.5) / cols
        frac = max(0.0, min(1.0, profile(t) + rng.uniform(-0.07, 0.07)))
        tops.append(round(frac * rows))
    filled = [[r < tops[c] for r in range(rows)] for c in range(cols)]

    bm = bmesh.new()
    mat_index = []

    def add_cell(center, size, edge: bool):
        res = bmesh.ops.create_cube(bm, size=1.0)
        verts = res["verts"]
        for v in verts:
            local = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
            v.co = center + direction * local.x + side * local.y + Vector((0, 0, local.z))
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            mat_index.append((f, 1 if edge else 0))

    for c in range(cols):
        for r in range(rows):
            if not filled[c][r]:
                continue
            edge = any(
                not (0 <= c + dc < cols and 0 <= r + dr < rows and filled[c + dc][r + dr])
                for dc, dr in ((1, 0), (-1, 0), (0, 1))
            ) and r >= tops[c] - 2
            stagger = (bw * 0.5) if r % 2 and edge else 0.0
            center = start + direction * ((c + 0.5) * bw) + Vector((0, 0, (r + 0.5) * bh))
            add_cell(center, (bw * (1.0 if not edge else rng.uniform(0.86, 0.98)), thickness * (1 if not edge else rng.uniform(0.9, 1.1)), bh * 0.98 if edge else bh), edge)
    bm.faces.index_update()
    lookup = {f.index: m for f, m in mat_index if f.is_valid}
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(plaster)
    mesh.materials.append(brick_mat)
    for poly in mesh.polygons:
        poly.material_index = lookup.get(poly.index, 0)
        poly.use_smooth = False
    obj = bpy.data.objects.new(name, mesh)
    link(obj, root)

    # Loose bricks drifting away from the break.
    for i in range(floaters):
        c = rng.randrange(cols)
        r = tops[c] + rng.randint(1, 4)
        base = start + direction * ((c + 0.5) * bw) + Vector((0, 0, (r + 0.5) * bh)) + side * rng.uniform(-0.3, 0.3)
        b = primitive("cube", f"{name}_loose_{i}", tuple(base), (bw / 2 * 0.95, thickness / 2, bh / 2 * 0.95), root, brick_mat)
        b.rotation_euler = (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(-0.6, 0.6))
    return obj


def _emissive_shaded(name: str, color_socket_builder, light_dir=(0.6, -0.5, 0.6), strength: float = 1.2, dark: float = 0.06):
    """Self-lit sphere look for far-away bodies: emission x a soft terminator towards `light_dir`."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    geo = nodes.new("ShaderNodeNewGeometry")
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = Vector(light_dir).normalized()
    links.new(geo.outputs["Normal"], dot.inputs[0])
    term = nodes.new("ShaderNodeMapRange")
    term.inputs["From Min"].default_value = -0.15
    term.inputs["From Max"].default_value = 0.6
    term.inputs["To Min"].default_value = dark
    term.inputs["To Max"].default_value = strength
    links.new(dot.outputs["Value"], term.inputs["Value"])
    color = color_socket_builder(nodes, links)
    emit = nodes.new("ShaderNodeEmission")
    links.new(color, emit.inputs["Color"])
    links.new(term.outputs["Result"], emit.inputs["Strength"])
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def planet_with_ring(root, location, radius: float) -> None:
    """A banded gas giant with a ring, and a small moon: far away, for scale and parallax."""

    def bands(nodes, links):
        coord = nodes.new("ShaderNodeTexCoord")
        sep = nodes.new("ShaderNodeSeparateXYZ")
        links.new(coord.outputs["Object"], sep.inputs[0])
        wave = nodes.new("ShaderNodeTexNoise")
        wave.inputs["Scale"].default_value = 2.0
        wave.inputs["Detail"].default_value = 4.0
        links.new(coord.outputs["Object"], wave.inputs["Vector"])
        mix = nodes.new("ShaderNodeMath")
        mix.operation = "MULTIPLY_ADD"
        mix.inputs[1].default_value = 0.15
        links.new(wave.outputs["Fac"], mix.inputs[0])
        links.new(sep.outputs["Z"], mix.inputs[2])
        ramp = nodes.new("ShaderNodeValToRGB")
        els = ramp.color_ramp.elements
        els[0].position, els[0].color = 0.0, srgb("#2a6f8a")
        els[1].position, els[1].color = 1.0, srgb("#f2c38a")
        for pos, col in ((0.3, "#5fb6b0"), (0.45, "#e7dcc2"), (0.6, "#d9875a"), (0.75, "#8a4a6a")):
            e = els.new(pos)
            e.color = srgb(col)
        frac = nodes.new("ShaderNodeMath")
        frac.operation = "FRACT"
        mul = nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 1.6
        links.new(mix.outputs[0], mul.inputs[0])
        links.new(mul.outputs[0], frac.inputs[0])
        links.new(frac.outputs[0], ramp.inputs["Fac"])
        return ramp.outputs["Color"]

    planet = primitive("uv_sphere", "planet", location, (radius, radius, radius * 0.94), root,
                       _emissive_shaded("planet_bands", bands, strength=1.1), segments=32, ring_count=16)
    planet.rotation_euler = (rad(18), rad(-12), 0)
    planet.data.polygons.foreach_set("use_smooth", [True] * len(planet.data.polygons))
    # Ring: a few thin bands of slightly different colour (a solid donut reads as a toy).
    for i, (r, w, col, e) in enumerate(((1.45, 0.05, "#c9b18f", 0.5), (1.58, 0.07, "#e3d3b5", 0.65), (1.74, 0.04, "#a88f73", 0.4), (1.86, 0.025, "#d9c7a6", 0.5))):
        band_r = primitive("torus", f"planet_ring_{i}", location, (1.0, 1.0, 0.06), root, material(f"planet_ring_{i}", col, 0.6, emission=e),
                           major_radius=radius * r, minor_radius=radius * w, major_segments=64, minor_segments=4)
        band_r.rotation_euler = (rad(74), rad(-12), rad(10))

    def grey(nodes, links):
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 6.0
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = srgb("#6d6a78")
        ramp.color_ramp.elements[1].color = srgb("#d6d2dc")
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        return ramp.outputs["Color"]

    loc = Vector(location)
    primitive("ico_sphere", "moon", tuple(loc + Vector((radius * 3.2, -radius * 1.5, -radius * 1.1))), (radius * 0.22,) * 3, root,
              _emissive_shaded("moon_surface", grey, strength=1.4), subdivisions=2)


def _island_scale(depth: float, island_depth: float) -> float:
    """Horizontal scale of the island rock at a given depth below the floor (matches floating_island rings)."""
    pts = [(0.0, 1.0), (0.14, 1.0), (0.45, 0.9), (0.95, 0.66), (1.5, 0.36)]
    d = depth * 1.5 / island_depth
    for (z0, k0), (z1, k1) in zip(pts, pts[1:]):
        if d <= z1:
            return k0 + (k1 - k0) * (d - z0) / (z1 - z0)
    return 0.3


def crystals(root, island_center, half_x: float, half_y: float, island_depth: float = 2.4, seed: int = 12, count: int = 11) -> None:
    """Glowing crystals growing out of the island's rock (teal and violet: Claude's glaze + the galaxy)."""
    rng = random.Random(seed)
    teal = material("crystal_teal", "#3fe0d0", 0.2, emission=3.0)
    violet = material("crystal_violet", "#b07bff", 0.2, emission=3.0)
    cx, cy, cz = island_center
    for i in range(count):
        a = rng.uniform(0, 2 * math.pi)
        depth = rng.uniform(0.3, 1.5)
        k = _island_scale(depth, island_depth) * 0.97
        c_, s_ = math.cos(a), math.sin(a)
        x = half_x * math.copysign(abs(c_) ** 0.5, c_) * k
        y = half_y * math.copysign(abs(s_) ** 0.5, s_) * k
        pos = Vector((cx + x, cy + y, cz - depth))
        out = Vector((c_, s_, -0.5)).normalized()
        for j in range(rng.randint(1, 3)):
            h = rng.uniform(0.2, 0.5)
            cr = primitive("cone", f"crystal_{i}_{j}", tuple(pos + out * 0.04 * j), (0.06, 0.06, h), root,
                           teal if (i + j) % 3 else violet, vertices=5)
            tilt = out + Vector((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), rng.uniform(-0.2, 0.2)))
            cr.rotation_euler = tilt.to_track_quat("Z", "Y").to_euler()
            cr.data.polygons.foreach_set("use_smooth", [False] * len(cr.data.polygons))
