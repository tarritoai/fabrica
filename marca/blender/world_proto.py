"""Visual prototype of the miniseries world (ideas/miniserie-mundo.md): stills only, not wired into the pipeline.

Two separate places joined only by the portal:
  portal - the usual room at night; a ring of light opens on the floor and through it you see the other world.
  mundo  - the world inside: green floating meadows over a sea of clouds, low golden sun, waterfalls,
           islands (sites of the internet) joined by warm bridges of light.
The portal disc shows a render of the world (mundo writes `portal_view.png`, so render mundo first).

  cruce_mundo, cruce_room - the animated crossing (render cruce_mundo first: it writes the portal's view), frames b_/a_.

Run: blender -b --factory-startup -P blender/world_proto.py -- <out_dir> <mundo|portal|atardecer|cruce_mundo|cruce_room> [percent] [samples]
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

import props  # noqa: E402
from lib import character_meta, empty, link, material, primitive, rad, srgb  # noqa: E402
from rigs import placeholders  # noqa: E402

# Light of the world by time of day. sky: horizon -> zenith ramp; sun_dir points towards the sun.
MOODS = {
    "dia": dict(sky=((0.0, "#ffe9c4"), (0.22, "#fff4dc"), (0.4, "#bfe0ff"), (0.7, "#6fb0f2"), (1.0, "#3f8fe6")), halo="#fff0c8",
                sky_strength=1.6, ambient=("#b9d6ff", 0.45), sun=("#ffd08a", 5.5), sun_dir=(-1.0, 0.35, 0.55),
                cloud=("#ffd9a8", 0.42), exposure=0.0),  # golden light on the cloud sea
    # Dusk: the sun about to touch the cloud sea, pink-violet sky going navy overhead; the people's lights come on.
    "atardecer": dict(sky=((0.0, "#ff9a52"), (0.16, "#ffb878"), (0.3, "#e98a8a"), (0.48, "#8a6aa8"), (0.75, "#3a3f80"), (1.0, "#1a2050")),
                      halo="#ffd08a", sky_strength=1.3, ambient=("#7a6aa8", 0.35), sun=("#ff9450", 3.2), sun_dir=(-1.0, 0.6, 0.07),
                      cloud=("#ffb59a", 0.22), exposure=0.1),
}
M = MOODS["dia"]  # set by build_mundo


# --- shared ---------------------------------------------------------------------------


def _flat(obj):
    obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))
    return obj


def _smooth(obj):
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    return obj


def camera(name: str, loc, target, lens: float, fstop: float | None = None):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 1500
    cam = bpy.data.objects.new(name, data)
    link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if fstop:
        data.dof.use_dof = True
        data.dof.aperture_fstop = fstop
        data.dof.focus_distance = (Vector(target) - Vector(loc)).length
    return cam


def bloom(scene, threshold: float = 0.9, strength: float = 0.7) -> None:
    """EEVEE has no bloom of its own since 4.2: compositor glare."""
    tree = bpy.data.node_groups.new("proto_comp", "CompositorNodeTree")
    scene.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    out = tree.nodes.new("NodeGroupOutput")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    for key, val in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", threshold), ("Strength", strength), ("Size", 0.85)):
        glare.inputs[key].default_value = val
    tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], out.inputs[0])


def render_settings(scene, percent: int, samples: int, exposure: float) -> None:
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.resolution_percentage = percent
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = exposure


def shoot(scene, cam, path: Path, size=None) -> None:
    scene.camera = cam
    if size:
        scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# --- the world inside -------------------------------------------------------------------


def sky_world() -> None:
    """The scene's world is the sky of the current mood (M)."""
    world = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(sky_shader(nodes, links, M), out.inputs["Surface"])


def sky_shader(nodes, links, m: dict):
    """Sky gradient from the horizon up (mood m), a warm halo round the sun; a soft separate fill for the scene.
    Returns the shader socket (so the pipeline can mix day, dusk and the room's galaxy in one world)."""
    M = m  # noqa: N806 - same names as the mood table
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["Generated"], sep.inputs[0])
    up = nodes.new("ShaderNodeMapRange")  # view direction z: just below the horizon .. high
    up.inputs["From Min"].default_value = -0.15
    up.inputs["From Max"].default_value = 0.7
    links.new(sep.outputs["Z"], up.inputs["Value"])
    ramp = nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    stops = M["sky"]
    els[0].position, els[0].color = stops[0][0], srgb(stops[0][1])
    els[1].position, els[1].color = stops[-1][0], srgb(stops[-1][1])
    for pos, col in stops[1:-1]:
        e = els.new(pos)
        e.color = srgb(col)
    links.new(up.outputs["Result"], ramp.inputs["Fac"])
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = Vector(M["sun_dir"]).normalized()
    links.new(coord.outputs["Generated"], dot.inputs[0])
    halo = nodes.new("ShaderNodeMapRange")
    halo.inputs["From Min"].default_value = 0.8
    halo.inputs["From Max"].default_value = 1.0
    links.new(dot.outputs["Value"], halo.inputs["Value"])
    pw = nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 3.0
    links.new(halo.outputs["Result"], pw.inputs[0])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    col_in = [i for i in mix.inputs if i.type == "RGBA"]  # "A"/"B" exist once per data type: take the colour ones
    col_in[1].default_value = srgb(M["halo"])
    links.new(pw.outputs[0], mix.inputs["Factor"])
    links.new(ramp.outputs["Color"], col_in[0])
    cam_bg = nodes.new("ShaderNodeBackground")
    cam_bg.inputs["Strength"].default_value = M["sky_strength"]
    links.new(next(o for o in mix.outputs if o.type == "RGBA"), cam_bg.inputs["Color"])
    amb = nodes.new("ShaderNodeBackground")  # what lights the scene: soft sky blue
    amb.inputs["Color"].default_value = srgb(M["ambient"][0])
    amb.inputs["Strength"].default_value = M["ambient"][1]
    lp = nodes.new("ShaderNodeLightPath")
    sw = nodes.new("ShaderNodeMixShader")
    links.new(lp.outputs["Is Camera Ray"], sw.inputs["Fac"])
    links.new(amb.outputs[0], sw.inputs[1])
    links.new(cam_bg.outputs[0], sw.inputs[2])
    return sw.outputs[0]


def island_rock_materials() -> None:
    """floating_island reuses these names: pre-create them in daylight colours (sandstone, not night rock)."""
    material("island_dirt", "#8a6440", 0.95)
    material("island_rock", "#c9a27e", 0.9)


def _grass() -> bpy.types.Material:
    """Meadow green with sunny patches (noise between two greens)."""
    if "meadow" in bpy.data.materials:
        return bpy.data.materials["meadow"]
    mat = material("meadow", "#5fae4a", 0.85)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.6
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = srgb("#3f8f3e")
    ramp.color_ramp.elements[1].color = srgb("#9ad35c")
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    return mat


def tree(root, name: str, at: Vector, k: float, rng: random.Random):
    trunk = material("bark", "#7a5236", 0.9)
    leaves = [material(f"leaves_{c}", c, 0.8) for c in ("#3f9a4a", "#5cb84e", "#2f7f46", "#8fcf5a")]
    h = 1.2 * k
    primitive("cylinder", f"{name}_trunk", tuple(at + Vector((0, 0, h / 2))), (0.09 * k, 0.09 * k, h / 2), root, trunk, vertices=6)
    for j in range(rng.randint(2, 3)):
        r = rng.uniform(0.5, 0.75) * k
        off = Vector((rng.uniform(-0.25, 0.25) * k, rng.uniform(-0.25, 0.25) * k, h + rng.uniform(0.0, 0.45) * k))
        _flat(primitive("ico_sphere", f"{name}_crown_{j}", tuple(at + off), (r, r, r * 0.85), root, rng.choice(leaves), subdivisions=1))


def meadow_island(root, name: str, center, half: float, seed: int, trees: int = 6, flowers: int = 30) -> Vector:
    """A floating meadow: grassy squircle top over warm sandstone, round low-poly trees, flowers, tufts."""
    rng = random.Random(seed)
    c = Vector(center)
    props.floating_island(root, tuple(c), half, half * 0.82, half * 0.8, _grass(), seed=seed)
    for i in range(trees):
        p = c + Vector((rng.uniform(-0.75, 0.75) * half, rng.uniform(-0.65, 0.65) * half, 0))
        tree(root, f"{name}_tree_{i}", p, rng.uniform(0.8, 1.6) * min(1.0, half / 4), rng)
    petal = [material(f"flower_{col}", col, 0.5, emission=0.2) for col in ("#fff6e0", "#ffd36b", "#ff9fb2", "#c9a7ff")]
    tuft = material("tuft", "#6fc25a", 0.8)
    for i in range(flowers):
        p = c + Vector((rng.uniform(-0.85, 0.85) * half, rng.uniform(-0.75, 0.75) * half, 0.0))
        if rng.random() < 0.55:
            primitive("ico_sphere", f"{name}_flower_{i}", tuple(p + Vector((0, 0, 0.06))), (0.045,) * 3, root, rng.choice(petal), subdivisions=1)
        else:
            t = _flat(primitive("cone", f"{name}_tuft_{i}", tuple(p + Vector((0, 0, 0.08))), (0.07, 0.07, 0.09), root, tuft, vertices=4))
            t.rotation_euler.z = rng.uniform(0, 3)
    return c


def _cloud_mat() -> bpy.types.Material:
    """Soft white with a gentle glow, so the cloud sea stays bright even in shadow."""
    if "cloud" in bpy.data.materials:
        return bpy.data.materials["cloud"]
    mat = material("cloud", "#fffaf2", 1.0, emission=M["cloud"][1])
    mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = srgb(M["cloud"][0])
    return mat


def _waterfall_mat() -> bpy.types.Material:
    """Pale glowing water in vertical streaks, opaque at the lip and gone by the bottom."""
    mat = material("waterfall", "#dff4ff", 0.1, emission=1.2)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    coord = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["UV"], sep.inputs[0])
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 6.0
    wave.inputs["Distortion"].default_value = 6.0
    links.new(coord.outputs["UV"], wave.inputs["Vector"])
    fade = nodes.new("ShaderNodeMapRange")
    fade.inputs["From Max"].default_value = 0.6
    fade.inputs["To Max"].default_value = 0.85
    links.new(sep.outputs["Y"], fade.inputs["Value"])
    streak = nodes.new("ShaderNodeMapRange")
    streak.inputs["To Min"].default_value = 0.55
    links.new(wave.outputs["Fac"], streak.inputs["Value"])
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    links.new(fade.outputs["Result"], mul.inputs[0])
    links.new(streak.outputs["Result"], mul.inputs[1])
    links.new(mul.outputs[0], nodes["Principled BSDF"].inputs["Alpha"])
    mat.surface_render_method = "BLENDED"
    return mat


def waterfall(root, name: str, top: Vector, direction: Vector, width: float, drop: float):
    """A curtain of water pouring off an island edge, fading into the clouds."""
    mat = bpy.data.materials.get("waterfall") or _waterfall_mat()
    d = Vector((direction.x, direction.y, 0)).normalized()
    side = d.cross(Vector((0, 0, 1))) * width / 2
    n = 14
    bm = bmesh.new()
    rows = []
    for i in range(n + 1):
        t = i / n
        p = top + d * (0.25 + 0.9 * math.sqrt(t)) + Vector((0, 0, -drop * t))  # shoots out, then falls
        w = side * (1 + 0.6 * t)
        rows.append((bm.verts.new(p - w), bm.verts.new(p + w)))
    for r0, r1 in zip(rows, rows[1:]):
        bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    uv = mesh.uv_layers.new()
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            uv.data[li].uv = (vi % 2, 1 - (vi // 2) / n)
    link(bpy.data.objects.new(name, mesh), root, mat)
    foot = top + d * 1.15 + Vector((0, 0, -drop))  # mist where it lands
    _smooth(primitive("ico_sphere", f"{name}_mist", tuple(foot), (width * 1.2, width * 1.2, width * 0.6), root, _cloud_mat(), subdivisions=2))


def cloud_sea(root, z: float, radius: float, count: int, seed: int):
    """A floor of puffy clouds below the islands (clusters of soft spheres sharing one mesh)."""
    rng = random.Random(seed)
    src = _smooth(primitive("ico_sphere", "cloud_src", (0, 0, -900), (1, 1, 1), root, _cloud_mat(), subdivisions=2))
    for i in range(count):
        a = rng.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rng.random())
        base = Vector((math.cos(a) * r, math.sin(a) * r + radius * 0.5, z + rng.uniform(-1.5, 1.5)))
        for j in range(rng.randint(3, 6)):
            o = src.copy()
            link(o, root)
            s = rng.uniform(2.5, 6.0)
            o.location = base + Vector((rng.uniform(-5, 5), rng.uniform(-4, 4), rng.uniform(0, 2.0)))
            o.scale = (s * rng.uniform(1.0, 1.6), s, s * rng.uniform(0.45, 0.7))


def floating_clouds(root, count: int, seed: int, region):
    rng = random.Random(seed)
    (x0, x1), (y0, y1), (z0, z1) = region
    for i in range(count):
        base = Vector((rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(z0, z1)))
        for j in range(rng.randint(2, 4)):
            s = rng.uniform(0.8, 2.2)
            _smooth(primitive("ico_sphere", f"cloud_{seed}_{i}_{j}", tuple(base + Vector((j * s * 0.9, rng.uniform(-0.5, 0.5), rng.uniform(-0.3, 0.3)))),
                              (s * 1.3, s, s * 0.6), root, _cloud_mat(), subdivisions=2))


def bridge(root, name: str, a, b, arch: float, width: float = 0.6, color: str = "#ffe2a0") -> list[Vector]:
    """A walkway of warm light from a to b, arching up by `arch`: pale glowing deck, posts and soft rails.
    Returns the deck's centre line (for placing walkers)."""
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2 + Vector((0, 0, arch))
    n = max(16, int((b - a).length * 3))
    pts = [(1 - t) ** 2 * a + 2 * (1 - t) * t * mid + t ** 2 * b for t in (i / n for i in range(n + 1))]
    sides = []
    for i in range(n + 1):
        tan = (pts[min(i + 1, n)] - pts[max(i - 1, 0)]).normalized()
        sides.append(tan.cross(Vector((0, 0, 1))).normalized() * width / 2)
    bm = bmesh.new()
    down = Vector((0, 0, 0.06))
    rows = [(bm.verts.new(p - s), bm.verts.new(p + s), bm.verts.new(p - s * 0.8 - down), bm.verts.new(p + s * 0.8 - down)) for p, s in zip(pts, sides)]
    for r0, r1 in zip(rows, rows[1:]):
        bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
        bm.faces.new((r0[3], r0[2], r1[2], r1[3]))
        bm.faces.new((r0[2], r0[0], r1[0], r1[2]))
        bm.faces.new((r0[1], r0[3], r1[3], r1[1]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    link(bpy.data.objects.new(name, mesh), root, material(f"bridge_deck_{color}", color, 0.3, emission=1.6))
    rail = material("bridge_rail", "#fff6dc", 0.3, emission=5.0)
    for k in (-1, 1):
        cd = bpy.data.curves.new(f"{name}_rail_{k}", "CURVE")
        cd.dimensions = "3D"
        cd.bevel_depth = 0.025
        sp = cd.splines.new("POLY")
        sp.points.add(n)
        for i, (p, s) in enumerate(zip(pts, sides)):
            q = p + s * k + Vector((0, 0, 0.32))
            sp.points[i].co = (q.x, q.y, q.z, 1)
        cd.materials.append(rail)
        link(bpy.data.objects.new(f"{name}_rail_{k}", cd), root)
        for i in range(0, n + 1, 4):
            p = pts[i] + sides[i] * k
            primitive("cylinder", f"{name}_post_{k}_{i}", tuple(p + Vector((0, 0, 0.16))), (0.02, 0.02, 0.16), root, rail, vertices=5)
    return pts


# Sites of the internet, as places that belong in the landscape (not giant icons).


def landmark_library(root, c: Vector):
    """Encyclopedia: a huge old golden tree whose crown is full of floating open books."""
    rng = random.Random(5)
    primitive("cylinder", "lib_trunk", tuple(c + Vector((0, 0, 2.2))), (0.45, 0.45, 2.2), root, material("bark_big", "#6e4a30", 0.9), vertices=8)
    for j in range(5):
        off = Vector((rng.uniform(-1.4, 1.4), rng.uniform(-1.0, 1.0), 4.4 + rng.uniform(0, 1.6)))
        r = rng.uniform(1.4, 2.0)
        _flat(primitive("ico_sphere", f"lib_crown_{j}", tuple(c + off), (r, r, r * 0.8), root,
                        material(f"leaves_gold_{j % 2}", ("#e0b84a", "#c9a13a")[j % 2], 0.8), subdivisions=1))
    page = material("book_page", "#fff6e0", 0.5, emission=1.5)
    cover = [material(f"book_cover_{col}", col, 0.7) for col in ("#3d6fd8", "#c86a45", "#3f8f5a", "#8a4a9a")]
    for i in range(9):
        p = c + Vector((rng.uniform(-3, 3), rng.uniform(-2.2, 2.2), rng.uniform(2.5, 7.5)))
        yaw = rng.uniform(0, 3)
        for s in (-1, 1):
            leaf = primitive("cube", f"lib_book_{i}_{s}", (0, 0, 0), (0.22, 0.3, 0.012), root, page)
            leaf.rotation_euler = (0, rad(-s * 20), yaw)
            leaf.location = p + Vector((math.cos(yaw) * s * 0.2, math.sin(yaw) * s * 0.2, 0))
        primitive("cube", f"lib_book_{i}_cover", tuple(p + Vector((0, 0, -0.03))), (0.44, 0.31, 0.012), root, rng.choice(cover)).rotation_euler.z = yaw


def landmark_music(root, c: Vector):
    """Music: a round white bandstand with a golden dome, notes drifting up from it."""
    white = material("stone_white", "#f4efe6", 0.7)
    primitive("cylinder", "band_base", tuple(c + Vector((0, 0, 0.15))), (1.8, 1.8, 0.15), root, white, vertices=12)
    for i in range(8):
        a = i / 8 * 2 * math.pi
        primitive("cylinder", f"band_col_{i}", tuple(c + Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, 1.25))), (0.08, 0.08, 1.0), root, white, vertices=6)
    _smooth(primitive("uv_sphere", "band_dome", tuple(c + Vector((0, 0, 2.25))), (1.85, 1.85, 1.1), root,
                      material("dome_gold", "#e8b94a", 0.35, emission=0.3), segments=16, ring_count=8))
    note = material("note_gold", "#fff0b8", 0.4, emission=3.0)
    rng = random.Random(4)
    for i in range(7):
        p = c + Vector((rng.uniform(-1.5, 1.5), rng.uniform(-1.0, 1.0), rng.uniform(3.6, 6.0)))
        primitive("uv_sphere", f"note_head_{i}", tuple(p), (0.16, 0.11, 0.12), root, note, segments=10, ring_count=6).rotation_euler.y = rad(-25)
        primitive("cylinder", f"note_stem_{i}", tuple(p + Vector((0.13, 0, 0.3))), (0.022, 0.022, 0.3), root, note, vertices=5)


def landmark_mail(root, c: Vector):
    """Mail: a little post-office cottage, letters folded into paper birds flying off its roof."""
    primitive("cube", "post_body", tuple(c + Vector((0, 0, 0.8))), (1.2, 0.9, 0.8), root, material("cottage_wall", "#f2e6d0", 0.8))
    roof = _flat(primitive("cone", "post_roof", tuple(c + Vector((0, 0, 2.1))), (1.75, 1.3, 0.6), root, material("cottage_roof", "#c8553d", 0.7), vertices=4))
    roof.rotation_euler.z = rad(45)
    primitive("cube", "post_door", tuple(c + Vector((0, -0.91, 0.5))), (0.3, 0.02, 0.5), root, material("door", "#3d6fd8", 0.6))
    paper = material("letter", "#fffaf0", 0.6, emission=0.6)
    rng = random.Random(9)
    for i in range(9):
        p = c + Vector((rng.uniform(-2.5, 2.5), rng.uniform(-1.5, 1.5), rng.uniform(2.6, 6.0)))
        for s in (-1, 1):  # two wings
            w = primitive("cube", f"letter_{i}_{s}", tuple(p + Vector((s * 0.12, 0, 0))), (0.13, 0.09, 0.008), root, paper)
            w.rotation_euler = (0, rad(-s * rng.uniform(15, 35)), rng.uniform(-0.4, 0.4))


def landmark_maps(root, c: Vector):
    """Maps: a winding stone path to a striped lighthouse."""
    stone = material("path_stone", "#e8dcc4", 0.85)
    rng = random.Random(3)
    for i in range(14):
        t = i / 13
        p = c + Vector((math.sin(t * 5) * 1.6, -3 + t * 6, 0.02))
        primitive("cylinder", f"path_{i}", tuple(p), (0.3, 0.3, 0.02), root, stone, vertices=7).rotation_euler.z = rng.uniform(0, 3)
    white = material("tower_white", "#f6f1e8", 0.7)
    red = material("tower_red", "#d9534a", 0.6)
    base = c + Vector((1.8, 1.4, 0))
    for i in range(4):
        r = 0.55 - i * 0.06
        primitive("cylinder", f"tower_{i}", tuple(base + Vector((0, 0, 0.6 + i * 1.2))), (r, r, 0.6), root, (white, red)[i % 2], vertices=10)
    _smooth(primitive("uv_sphere", "tower_lamp", tuple(base + Vector((0, 0, 5.2))), (0.4,) * 3, root,
                      material("tower_lamp", "#fff2c0", 0.3, emission=6.0), segments=12, ring_count=8))
    _flat(primitive("cone", "tower_cap", tuple(base + Vector((0, 0, 5.85))), (0.55, 0.55, 0.45), root, red, vertices=10))


def build_mundo(mood: str = "dia", make_world: bool = True) -> dict:
    """The world inside, around the origin. make_world=False leaves the scene's world shader alone (the pipeline
    mixes the skies itself)."""
    global M
    M = MOODS[mood]
    island_rock_materials()
    if make_world:
        sky_world()
    root = empty("MUNDO")
    sun = bpy.data.lights.new("sun", "SUN")
    sun.color = srgb(M["sun"][0])[:3]
    sun.energy = M["sun"][1]
    sun.angle = rad(3)
    sun_ob = bpy.data.objects.new("sun", sun)
    link(sun_ob)
    sun_ob.rotation_euler = (-Vector(M["sun_dir"]).normalized()).to_track_quat("-Z", "Y").to_euler()

    # The arrival meadow (where the portal drops you), then islands receding towards the sun.
    centers = {"arrival": (meadow_island(root, "arrival", (0, 0, 0), 5.5, 1, trees=0, flowers=70), 5.5)}
    rng_t = random.Random(2)
    for i, p in enumerate(((-4.2, 1.5), (-3.4, 3.2), (4.6, -3.2))):  # framing the view, never in front of it
        tree(root, f"arrival_tree_{i}", Vector((p[0], p[1], 0)), rng_t.uniform(1.0, 1.4), rng_t)
    islands = {
        "mapas": ((13, 20, 3), 5.0, landmark_maps),
        "musica": ((-12, 26, 6), 4.6, landmark_music),
        "correo": ((22, 40, 10), 4.2, landmark_mail),
        "enciclopedia": ((-2, 50, 13), 6.0, landmark_library),
    }
    for i, (name, (c, half, mark)) in enumerate(islands.items()):
        cv = meadow_island(root, name, c, half, 10 + i * 7, trees=5)
        mark(root, cv)
        centers[name] = (cv, half)
    rng = random.Random(21)
    for i in range(10):  # far islands: the world goes on
        ang = rng.uniform(-1.2, 1.2)
        dist = rng.uniform(70, 150)
        meadow_island(root, f"far_{i}", (math.sin(ang) * dist, math.cos(ang) * dist + 20, rng.uniform(0, 30)), rng.uniform(4, 9), 50 + i, trees=4, flowers=0)

    def edge(name, towards):
        c, half = centers[name]
        d = Vector(towards) - c
        d.z = 0
        return c + d.normalized() * half * 0.85

    bridges = []
    for a, b, arch in (("arrival", "mapas", 3.0), ("arrival", "musica", 4.0), ("mapas", "correo", 4.0), ("musica", "enciclopedia", 5.0),
                       ("mapas", "enciclopedia", 6.0)):
        bridges.append(bridge(root, f"bridge_{a}_{b}", edge(a, centers[b][0]), edge(b, centers[a][0]), arch))

    for name, dirn, w in (("arrival", (0.9, -0.4), 1.0), ("mapas", (0.3, -1), 1.4), ("musica", (-0.6, -1), 1.2), ("enciclopedia", (0.4, -1), 1.8)):
        c, half = centers[name]
        d = Vector((dirn[0], dirn[1], 0)).normalized()
        waterfall(root, f"fall_{name}", c + Vector((d.x * half * 0.8, d.y * half * 0.66, -0.05)), d, w, 14 + c.z)

    cloud_sea(root, -16, 120, 70, 3)
    floating_clouds(root, 14, 5, ((-50, 50), (15, 110), (2, 22)))
    return {"centers": centers, "bridges": bridges, "root": root}


# --- dusk: the people's lights ---------------------------------------------------------------------------------
# Visual grammar (taught close up first): a warm light = a person, with chat bubbles rising from it; next to almost
# every light a little AI answers it. The lonely one breaks the rule: no AI, its bubbles pile up unanswered.

LONELY = Vector((8.5, 3.0, -0.6))  # a scrap of rock off on its own, below the arrival meadow, with one light
PERSON_LINES = ["no puedo dormir", "¿me ayudas con esto?", "¿estás ahí?", "hola", "¿puedo contarte algo?", "no sé qué hacer",
                "mañana tengo examen", "¿esto es normal?", "hoy ha sido un día raro", "gracias por escucharme"]
AI_LINES = ["claro, cuéntame", "aquí estoy", "te escucho", "vamos paso a paso", "¿qué ha pasado?"]
BILLBOARD = "BILLBOARD"  # bubbles copy its rotation; it copies the active camera's before each shot


def _join(objs: list, name: str):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    out = bpy.context.active_object
    out.name = name
    return out


# Other AIs are pottery too (same world as Claude) but clearly not Claude: other shapes, no gold crack, no thumbprint.
# (kind, clay, glaze). Kinds: vasija (round belly, neck, two handles), botella (tall, corked), cuenco (low pot, lid).
# Most of them are Claudes listening to other people (same jar, other clays and glazes, never our terracotta +
# turquoise) WITHOUT the gold crack and the thumbprint: that scar is what makes ours *him*. A few other pottery
# shapes are other AIs. (kind, clay, glaze); kinds: loaf / brick (Claude's shapes), vasija, botella, cuenco.
AI_KINDS = [("loaf", "#7d8c9c", "#bfe9de"), ("brick", "#8a5a7a", "#f2d3a0"), ("loaf", "#c9b18a", "#3d6fd8"),
            ("brick", "#5f7a5a", "#e8c070"), ("loaf", "#b8b0c8", "#c05a4a"), ("loaf", "#6a5a4a", "#f0ece0"),
            ("vasija", "#c8b8a0", "#4f8fd0"), ("botella", "#b07050", "#3fbfb0")]
POTTERY = {  # lathe profile (radius, height) from the base up, glaze line, eye height
    "vasija": ([(0, 0), (0.07, 0), (0.11, 0.05), (0.125, 0.12), (0.112, 0.19), (0.065, 0.235), (0.045, 0.265), (0.056, 0.29), (0, 0.29)], 0.17, 0.12),
    "botella": ([(0, 0), (0.08, 0), (0.095, 0.03), (0.095, 0.17), (0.072, 0.22), (0.036, 0.25), (0.036, 0.31), (0, 0.31)], 0.2, 0.11),
    "cuenco": ([(0, 0), (0.06, 0), (0.12, 0.05), (0.135, 0.11), (0.122, 0.16), (0.1, 0.18), (0, 0.18)], 0.15, 0.1),
}


def _lathe(name: str, profile, steps: int = 14):
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((a, b)) for a, b in zip(verts, verts[1:])]
    bmesh.ops.spin(bm, geom=verts + edges, axis=(0, 0, 1), cent=(0, 0, 0), steps=steps, angle=2 * math.pi)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    link(obj)
    return obj


def _radius_at(profile, z: float) -> float:
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return profile[1][0]


def ai_template(i: int, kind: str, body: str, accent: str):
    """A small pottery AI as one joined mesh (~0.3 m), facing -Y; copies share it."""
    if kind in ("loaf", "brick"):
        return _claude_like(i, kind, body, accent)
    profile, glaze_z, eye_z = POTTERY[kind]
    clay = material(f"pot_clay_{body}", body, 0.85)
    glaze = material(f"pot_glaze_{accent}", accent, 0.25, emission=0.25)
    eye = material("pot_eye", "#15110f", 0.3)
    shine = material("pot_eye_shine", "#ffffff", 0.3, emission=3.0)
    pot = _lathe(f"ai_body_{i}", profile)
    pot.data.materials.append(clay)
    pot.data.materials.append(glaze)
    for poly in pot.data.polygons:
        poly.material_index = 1 if poly.center.z > glaze_z else 0
        poly.use_smooth = True
    parts = [pot]
    if kind == "vasija":
        for s in (-1, 1):
            h = primitive("torus", "t", (s * 0.105, 0, 0.2), (1, 1, 1), None, glaze, major_radius=0.04, minor_radius=0.011,
                          major_segments=10, minor_segments=5)
            h.rotation_euler.x = rad(90)
            parts.append(h)
    elif kind == "botella":
        parts.append(primitive("cylinder", "t", (0, 0, 0.325), (0.032, 0.032, 0.022), None, material("cork", "#b08a5a", 0.9), vertices=10))
    else:
        parts.append(_smooth(primitive("uv_sphere", "t", (0, 0, 0.18), (0.105, 0.105, 0.045), None, glaze, segments=14, ring_count=6)))
        parts.append(_smooth(primitive("uv_sphere", "t", (0, 0, 0.23), (0.022,) * 3, None, glaze, segments=8, ring_count=5)))
    r = _radius_at(profile, eye_z)
    for x in (-0.034, 0.034):
        y = -math.sqrt(max(0.0, r * r - x * x))
        parts.append(_smooth(primitive("uv_sphere", "t", (x, y - 0.002, eye_z), (0.013, 0.008, 0.019), None, eye, segments=8, ring_count=6)))
        parts.append(primitive("ico_sphere", "t", (x + 0.004, y - 0.009, eye_z + 0.007), (0.004,) * 3, None, shine, subdivisions=1))
    t = _join(parts, f"ai_tpl_{i}")
    bpy.context.view_layer.objects.active = t
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    t.location = (0, 0, -900)
    return t


def _claude_like(i: int, variant: str, clay: str, glaze: str):
    """Claude's jar in another clay and glaze, without the gold crack, the thumbprint and the cup, joined into one mesh."""
    char_id = f"other_{i}"
    meta = dict(character_meta("claude"))
    meta["id"] = char_id
    dark = "#" + "".join(f"{max(0, int(clay[k:k + 2], 16) - 50):02x}" for k in (1, 3, 5))
    meta["ceramic"] = {**meta.get("ceramic", {}), "variant": variant, "color": clay, "dark": dark, "groove": dark, "glaze": glaze, "seed": 20 + i}
    root = placeholders.build(char_id, meta)
    bpy.context.view_layer.update()
    keep, drop = [], []
    for o in root.children_recursive:
        base = o.name.split(".")[0]
        if base.startswith(("kintsugi", "thumbprint", "claude_cup", "mouth")) or "cup" in base or o.hide_render:
            drop.append(o)
        elif o.type == "MESH":
            keep.append(o)
    for o in drop:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in keep:  # free them from the rig (keep their world placement) so the join bakes it in
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in [root, *root.children_recursive]:  # the rig's empties (the root is one)
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    for o in keep:
        bpy.context.view_layer.objects.active = o
        for mod in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    t = _join(keep, f"ai_tpl_{i}")
    bpy.context.view_layer.objects.active = t
    # The joined object inherits the first part's transform (a tiny brow): bake it before resizing.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    t.scale = (0.62,) * 3  # the same size as the other pottery (~0.3 m): their jar of light stays the subject
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    t.location = (0, 0, -900)
    return t


_JARS: list = []


def jar_template(core: bpy.types.Material | None = None, name: str = "jar_tpl"):
    """A person's light: a little glass jar with a warm glow inside and a cork (a 'tarrito' of light), centred on its
    origin, ~0.2 m tall at scale 1 (pair sizes are relative to 0.1). One joined mesh: copies share it."""
    core = core or material("jar_core", "#ffc070", 0.2, emission=7.0)
    parts = [primitive("cylinder", "t", (0, 0, 0), (0.07, 0.07, 0.095), None, _glass(), vertices=16),
             primitive("cylinder", "t", (0, 0, 0.11), (0.054, 0.054, 0.02), None, material("cork", "#b08a5a", 0.9), vertices=12),
             _smooth(primitive("uv_sphere", "t", (0, 0, -0.02), (0.029, 0.029, 0.045), None, core, segments=12, ring_count=8))]
    for i in range(5):  # sparks drifting inside
        a = i * 1.3
        parts.append(primitive("ico_sphere", "t", (math.cos(a) * 0.038, math.sin(a) * 0.038, 0.012 + 0.012 * i), (0.005,) * 3, None, core, subdivisions=1))
    t = _join(parts, name)
    bpy.context.view_layer.objects.active = t
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    t.location = (0, 0, -900)
    return t


def jar_at(root, at: Vector, size: float, rng: random.Random | None = None):
    """A copy of one of the jar templates (three glow tints) at `at`, sized like the old lights (size 0.1 = 1x)."""
    if not _JARS:
        _JARS.extend(jar_template(material(f"jar_core_{c}", c, 0.2, emission=e), f"jar_tpl_{n}")
                     for n, (c, e) in enumerate((("#ffc070", 7.0), ("#ffd890", 6.0), ("#ffa850", 7.0))))
    o = (rng.choice(_JARS) if rng else _JARS[0]).copy()
    link(o, root)
    o.name = "person_light"
    o.location = at
    k = size / 0.1
    o.scale = (k, k, k)
    if rng:
        o.rotation_euler.z = rng.uniform(0, 6.28)
    return o


def bubble(root, at: Vector, text: str | None, scale: float, ai: bool = False, fade: float = 1.0, typing: bool = False):
    """A chat bubble that always faces the camera: white for people, tinted for the AIs. No text = a blank bubble
    (far away), typing = the three dots."""
    bb = bpy.data.objects[BILLBOARD]
    holder = empty("bubble", tuple(at), root)
    holder.scale = (scale,) * 3
    con = holder.constraints.new("COPY_ROTATION")
    con.target = bb
    chars = len(text) if text else (3 if typing else 6)
    w, h = 0.065 * chars + 0.12, 0.17
    col = "#ffd9b0" if ai else "#fffaf0"
    mat = material(f"bubble_{'ai' if ai else 'p'}_{fade:.2f}", col, 0.6, emission=3.2 * fade)
    box = primitive("cube", "bubble_box", (0, 0, 0), (w / 2, h / 2, 0.012), holder, mat)
    box.modifiers.new("bevel", "BEVEL").width = 0.05
    box.modifiers["bevel"].segments = 3
    tail = _flat(primitive("cone", "bubble_tail", ((w / 2 - 0.08) * (1 if ai else -1), -h / 2 - 0.03, 0), (0.05, 0.05, 0.012), holder, mat, vertices=3))
    tail.rotation_euler.z = rad(90 if ai else -90)
    ink = material(f"bubble_ink_{fade:.2f}", "#2a2230" if not ai else "#5a2a14", 0.5)
    if text:
        cu = bpy.data.curves.new("bubble_text", "FONT")
        cu.body = text
        cu.size = 0.105
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        t = bpy.data.objects.new("bubble_text", cu)
        link(t, holder, None)
        cu.materials.append(ink)
        t.location = (0, 0.005, 0.02)
    elif typing:
        for k in (-1, 0, 1):
            primitive("uv_sphere", "bubble_dot", (k * 0.06, 0, 0.02), (0.02, 0.02, 0.006), holder, ink, segments=8, ring_count=5)
    return holder


def pair(root, tpls, at: Vector, size: float, rng: random.Random, text: bool = False, lines=None, both: bool = False,
         right: Vector | None = None, bubbles: bool = True):
    """One person's light and the AI answering it, each maybe saying something (both: the two of them, with text)."""
    jar = jar_at(root, at, size, rng)
    side = right or Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
    ai_at = at + side * size * 3.4 - Vector((0, 0, size * 1.4))
    o = rng.choice(tpls).copy()
    link(o, root)
    k = size / 0.1
    o.scale = (k, k, k)
    o.location = ai_at
    to = at - ai_at
    o.rotation_euler.z = math.atan2(to.x, -to.y)  # face the light
    p_line, a_line = lines or (rng.choice(PERSON_LINES), rng.choice(AI_LINES))
    if not bubbles:
        return jar, o
    if both:  # the person's line just above-left of the light, the answer clearly higher, above-right of the AI
        bubble(root, at + Vector((0, 0, size * 2.6)) - side * size * 3, p_line, k * 1.2)
        bubble(root, ai_at + Vector((0, 0, size * 9)) + side * size * 3, a_line, k * 1.2, ai=True)
        return
    r = rng.random()
    if r < 0.45:
        bubble(root, at + Vector((0, 0, size * 2.6)), p_line if text else None, k)
    elif r < 0.75:
        bubble(root, ai_at + Vector((0, 0, size * 4.2)), a_line if text else None, k, ai=True, typing=not text and r < 0.6)


_LIGHT_MATS: list = []


def _light_mats():
    if not _LIGHT_MATS:
        _LIGHT_MATS.extend(material(f"person_light_{c}", c, 0.2, emission=e) for c, e in (("#ffb347", 5.0), ("#ffc86b", 4.0), ("#ff9a3d", 5.0)))
    return _LIGHT_MATS


NEAR_PAIRS = [  # (light position, size, person line, AI line): big and readable in the wide shot
    (Vector((-1.9, -1.2, 2.0)), 0.17, "¿estás despierto?", "te escucho"),
    (Vector((2.9, 0.8, 2.9)), 0.17, "¿puedo contarte algo?", "claro, cuéntame"),
    (Vector((-0.6, 4.0, 5.0)), 0.16, "mañana tengo examen", "vamos paso a paso"),
    (Vector((4.6, 6.0, 1.6)), 0.15, "hoy ha sido un día raro", "¿qué ha pasado?"),
]
MID_RANGE = 40  # metres from the wide camera: closer = a light with its AI (and maybe a blank bubble); beyond = just a light


def people_lights(world: dict, tpls, avoid: list[Vector], wide_cam: Vector, seed: int = 7, near: bool = True,
                  bubbles: bool = True) -> None:
    """Hierarchy by distance so the eye has somewhere to land: a few big talking pairs up close (NEAR_PAIRS), a few
    dozen smaller pairs in the middle, hundreds of bare lights far away (by then you know what they are).
    Nothing near the lonely one or the other cameras."""
    rng = random.Random(seed)
    root = world["root"]
    look = (Vector((3, 20, 3.0)) - wide_cam).normalized()
    right = look.cross(Vector((0, 0, 1))).normalized()
    for at, size, p_line, a_line in NEAR_PAIRS if near else ():
        pair(root, tpls, at, size, rng, lines=(p_line, a_line), both=True, right=right)

    def place(at: Vector, size: float):
        if (at - LONELY).length < 9 or any((at - a).length < 4 for a in avoid) or any((at - n[0]).length < 3 for n in NEAR_PAIRS):
            return
        d = (at - wide_cam).length
        if d < 13:
            return  # the near layer is hand-placed
        if d < MID_RANGE and rng.random() < 0.8:
            pair(root, tpls, at, size, rng, bubbles=bubbles)
        else:  # a few on their own for a moment (someone typing), so the lonely one is about *time*, not just absence
            jar_at(root, at, size, rng)

    for pts in world["bridges"]:
        for i in range(2, len(pts) - 2, 6):
            if rng.random() < 0.7:
                place(pts[i] + Vector((0, 0, 0.55)), 0.09)
    for name, (c, half) in world["centers"].items():
        if name == "arrival":
            continue
        for _ in range(int(half * 3)):
            a, r = rng.uniform(0, 2 * math.pi), half * rng.uniform(0.6, 1.5)
            place(c + Vector((math.cos(a) * r, math.sin(a) * r, rng.uniform(0.8, 6))), rng.uniform(0.08, 0.14))
    for _ in range(650):
        y = rng.uniform(12, 170)
        place(Vector((rng.uniform(-30 - y * 0.6, 30 + y * 0.6), y, rng.uniform(-13, 30))), rng.uniform(0.12, 0.22) * (1 + y / 120))


def lonely_islet(root, bubbles: bool = True) -> None:
    """The one that has been waiting for hours: a small rock, a single dim light, no AI, its questions piling up."""
    props.floating_island(root, tuple(LONELY), 0.9, 0.75, 0.9, _grass(), seed=77)
    light = LONELY + Vector((0.1, 0.1, 0.2))
    lonely = jar_template(material("lonely_light", "#ffd9a8", 0.2, emission=1.8), "lonely_jar")  # same jar, a paler, weaker glow
    lonely.location, lonely.scale = LONELY + Vector((0.1, 0.1, 0.19)), (2.0, 2.0, 2.0)  # on the grass, alone
    lonely.parent = root
    props.point_light("lonely_glow", tuple(light + Vector((0, -0.1, 0.1))), "#ffd8a0", 8, 0.1)
    # Oldest at the top, fading; the newest just above the light.
    for i, (line, fade) in enumerate((("¿hay alguien?", 1.0), ("¿sigues ahí?", 0.7), ("¿hola?", 0.45)) if bubbles else ()):
        bubble(root, light + Vector((0, 0, 0.5 + i * 0.5)), line, 1.8 - 0.15 * i, fade=fade)


def atardecer(out: Path, percent: int, samples: int) -> None:
    scene = bpy.context.scene
    world = build_mundo("atardecer")
    bb = empty(BILLBOARD)
    tpls = [ai_template(i, *k) for i, k in enumerate(AI_KINDS)]
    cams = {
        # 1. The rule, close up: a light drifts past them saying something, its AI answers.
        "regla": camera("cam_regla", (-0.4, -5.6, 1.45), (0.2, -1.1, 1.0), 32, 4.0),
        # 2. Wide: the same view as by day, now thousands of them.
        "atardecer": camera("cam_atardecer", (-1.0, -10.5, 4.2), (3, 20, 3.0), 24),
        # 3. "¿Y esa?": over their shoulders, down past the edge at the one with nobody.
        "luz_sola": camera("cam_luz_sola", (2.7, -1.5, 2.5), tuple(LONELY + Vector((-1.0, 0, 1.2))), 30, 5.6),
    }
    close = Vector((0.85, -1.0, 1.35))  # the pair that teaches the rule
    people_lights(world, tpls, [c.location.copy() for n, c in cams.items() if n != "atardecer"] + [close], cams["atardecer"].location.copy())
    lonely_islet(world["root"])
    root = world["root"]
    _smooth(primitive("ico_sphere", "close_light", tuple(close), (0.12,) * 3, root, _light_mats()[0], subdivisions=2))
    props.point_light("close_glow", tuple(close + Vector((0, -0.2, 0))), "#ffb347", 10, 0.1)
    bot = tpls[2].copy()
    link(bot, root)
    bot_at = close + Vector((0.5, 0.15, -0.3))
    bot.location, bot.scale = bot_at, (1.4, 1.4, 1.4)
    bot.rotation_euler.z = rad(-37)  # towards the light, three-quarters to camera
    bubble(root, close + Vector((-0.4, 0, 0.3)), "no puedo dormir", 0.7)
    bubble(root, bot_at + Vector((-0.2, 0, 0.7)), "aquí estoy", 0.7, ai=True)

    hero = placeholders.build("novato", character_meta("novato"))
    claude = placeholders.build("claude", character_meta("claude"))
    for o in claude.children_recursive:
        if o.name.startswith("claude_cup"):
            o.hide_render = True
    bloom(scene, 0.8, 0.8)
    render_settings(scene, percent, samples, M["exposure"])
    out.mkdir(parents=True, exist_ok=True)
    staging = {
        "regla": (((-0.75, -1.1, 0), 100), ((-0.3, -1.7, 0), 95)),
        "atardecer": (((-0.6, -2.0, 0), 185), ((0.35, -1.8, 0), 165)),
        "luz_sola": (((4.6, 0.7, 0), 0), ((5.0, -0.1, 0), -8)),
    }
    face_islet = math.degrees(math.atan2(LONELY.x - 4.2, -(LONELY.y - 0)))
    for name, cam in cams.items():
        (dl, dy), (cl, cy) = staging[name]
        if name == "luz_sola":
            dy, cy = face_islet + dy, face_islet + cy
        hero.location, hero.rotation_euler.z = dl, rad(dy)
        claude.location, claude.rotation_euler.z = cl, rad(cy)
        bb.rotation_euler = cam.rotation_euler
        shoot(scene, cam, out / f"{name}.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "atardecer.blend"))


def mundo(out: Path, percent: int, samples: int) -> None:
    scene = bpy.context.scene
    build_mundo()
    # The lead and Claude, just arrived, looking out (backs to camera); the portal they came through beside them.
    hero = placeholders.build("novato", character_meta("novato"))
    hero.location = (-0.6, -2.0, 0)
    hero.rotation_euler.z = rad(185)
    claude = placeholders.build("claude", character_meta("claude"))
    claude.location = (0.35, -1.8, 0)
    claude.rotation_euler.z = rad(165)
    for o in claude.children_recursive:
        if o.name.startswith("claude_cup"):
            o.hide_render = True
    portal_ring(empty("PORTAL_OUT", (2.6, -3.6, 0)), 0, light=False)

    bloom(scene, 1.0, 0.5)
    render_settings(scene, percent, samples, 0.0)
    out.mkdir(parents=True, exist_ok=True)
    shoot(scene, camera("cam_mundo", (-1.0, -10.5, 4.2), (3, 20, 3.0), 24), out / "mundo.png")
    # What the room sees through the portal: the meadow and the islands, nobody there yet.
    for o in [claude, *claude.children_recursive, hero, *hero.children_recursive]:
        o.hide_render = True
    scene.render.resolution_percentage = 100
    shoot(scene, camera("cam_portal_view", (0.5, -6.5, 1.4), (2, 20, 5), 28), out / "portal_view.png", (720, 720))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "mundo.blend"))


# --- the room with the portal open -------------------------------------------------------


def portal_ring(holder, yaw: float, light: bool = True, view: Path | None = None):
    """A standing ring of warm light. With `view`, its disc shows that image (the world on the other side)."""
    holder.rotation_euler.z = rad(yaw)
    ring = empty("portal_ring_holder", (0, 0, 1.0), holder)
    ring.rotation_euler.x = rad(90)
    primitive("torus", "portal_ring", (0, 0, 0), (1, 1, 1), ring, material("portal_ring", "#fff0c8", 0.3, emission=7.0),
              major_radius=0.95, minor_radius=0.045, major_segments=64, minor_segments=8)
    primitive("torus", "portal_ring_outer", (0, 0, 0), (1, 1, 1), ring, material("portal_outer", "#9fe8a8", 0.3, emission=3.0),
              major_radius=1.06, minor_radius=0.014, major_segments=64, minor_segments=6)
    if view:
        disc = primitive("circle", "portal_disc", (0, 0, 0), (0.93, 0.93, 1), ring, _view_mat(view), vertices=64, fill_type="NGON")
        disc.rotation_euler.x = rad(180)  # face the room (-Y)
    if light:
        bpy.context.view_layer.update()
        m = holder.matrix_world
        props.area_light("portal_spill", tuple(m @ Vector((0, -0.25, 1.0))), tuple(m @ Vector((0, -3, 0.3))), "#fff1cf", 260, 1.8)
        props.point_light("portal_glow", tuple(m @ Vector((0, -0.6, 1.0))), "#ffe2a8", 60, 0.5)


def _view_mat(image_path: Path) -> bpy.types.Material:
    """The other world seen through the disc, brighter towards the rim where the light pours in."""
    mat = bpy.data.materials.new("portal_view")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")  # object xy (-1..1) -> image uv (0..1)
    mapping.inputs["Scale"].default_value = (0.5, -0.5, 1)  # the disc is flipped to face the room
    mapping.inputs["Location"].default_value = (0.5, 0.5, 0)
    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path))
    tex.extension = "EXTEND"
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    rim = nodes.new("ShaderNodeVectorMath")
    rim.operation = "LENGTH"
    links.new(coord.outputs["Object"], rim.inputs[0])
    strength = nodes.new("ShaderNodeMapRange")
    strength.inputs["From Min"].default_value = 0.6
    strength.inputs["To Min"].default_value = 0.9
    strength.inputs["To Max"].default_value = 2.2
    links.new(rim.outputs["Value"], strength.inputs["Value"])
    em = nodes.new("ShaderNodeEmission")
    links.new(tex.outputs["Color"], em.inputs["Color"])
    links.new(strength.outputs["Result"], em.inputs["Strength"])
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def portal(out: Path, percent: int, samples: int) -> None:
    import sets_marca as sets

    scene = bpy.context.scene
    home = sets.escritorio_noche({"fps": 30, "total_frames": 300})
    hero = placeholders.build("novato", character_meta("novato"))
    hero.location = home["slots"]["left"]
    hero.rotation_euler.z = rad(home["facing"]["left"] + 35)  # turned towards the light
    claude = placeholders.build("claude", character_meta("claude"))
    claude.location = (1.25, -1.05, 0)  # on the floor in front of the portal, looking into it
    claude.rotation_euler.z = rad(160)
    portal_ring(empty("PORTAL", tuple(ROOM_PORTAL[0])), ROOM_PORTAL[1], view=out / "portal_view.png")  # open floor by the rug

    bloom(scene, 0.9, 0.7)
    render_settings(scene, percent, samples, 0.2)
    shoot(scene, camera("cam_portal", (-0.4, -3.9, 1.05), (1.35, -0.2, 0.85), 26), out / "portal.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "portal.blend"))


# --- the crossing (animated) -------------------------------------------------------------------------------
# Room: the portal starts pulling (lid simmering, papers sucked in), Claude glances at the lead and is swallowed,
# The lead reaches for it and goes too, the camera dives after them. Flash. World: they are spat out onto the grass
# (Claude bounces, its lid flies off and lands back on; the lead stumbles), look up, and the camera rises on the world.

FPS = 30
ROOM_PORTAL = (Vector((1.55, -0.1, 0.0)), -15)  # base, yaw (shared by the still and the crossing)
ROOM_FRAMES, WORLD_FRAMES = 96, 132
WORLD_PORTAL = Vector((2.6, -1.2, 0.0))


def bake_frames(objs: list, frames: int, fn) -> None:
    """Key location/rotation/scale of `objs` on every frame from fn(frame) (which sets them)."""
    for f in range(1, frames + 1):
        fn(f)
        for o in objs:
            for path in ("location", "rotation_euler", "scale"):
                o.keyframe_insert(path, frame=f)
            if o.rotation_mode == "QUATERNION":
                o.keyframe_insert("rotation_quaternion", frame=f)


def key_value(socket, frames_values) -> None:
    for f, v in frames_values:
        socket.default_value = v
        socket.keyframe_insert("default_value", frame=f)


def ramp(f: float, f0: float, f1: float) -> float:
    return max(0.0, min(1.0, (f - f0) / (f1 - f0)))


def ease_in(t: float, p: float = 2.4) -> float:
    return t ** p


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def ripple(holder, name: str, frame: int, color: str = "#fff6dc") -> None:
    """A ring of light spreading across the disc when something goes through."""
    mat = material(f"ripple_{name}", color, 0.3, emission=0.0)
    r = primitive("torus", f"ripple_{name}", (0, 0, 0.01), (0.05, 0.05, 0.05), holder, mat, major_radius=1.0, minor_radius=0.03,
                  major_segments=48, minor_segments=5)
    for f, s in ((frame - 1, 0.05), (frame, 0.08), (frame + 12, 1.0)):
        r.scale = (s, s, s)
        r.keyframe_insert("scale", frame=f)
    key_value(mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"], ((frame - 1, 0.0), (frame, 25.0), (frame + 12, 0.0)))


def flash_ring(frames: list[int], base: float = 7.0) -> None:
    sock = bpy.data.materials["portal_ring"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    keys = [(1, base)]
    for f in frames:
        keys += [(f - 1, base), (f + 1, base * 3.5), (f + 10, base)]
    key_value(sock, sorted(keys))


def sucked(obj, start: Vector, centre: Vector, f0: int, f1: int, spin: float = 0.0, stretch: float = 0.6, base_scale: float = 1.0):
    """Returns fn(f) moving obj from start into the portal centre between f0 and f1, stretching then vanishing."""
    yaw0, s0 = obj.rotation_euler.z, obj.scale.copy()

    def at(f):
        t = ramp(f, f0, f1)
        e = ease_in(t)
        lift = Vector((0, 0, 0.25 * math.sin(math.pi * min(1.0, t * 1.3))))
        obj.location = start.lerp(centre - Vector((0, 0, 0.35 * base_scale)), e) + lift * (1 - e)
        s = base_scale * (1 - smooth(ramp(t, 0.7, 1.0)) * 0.98)
        st = 1 + stretch * math.sin(math.pi * min(1.0, t * 1.15)) if t > 0 else 1
        obj.scale = (s0.x * s / math.sqrt(st), s0.y * s / math.sqrt(st), s0.z * s * st)
        obj.rotation_euler.z = yaw0 + spin * e
    return at


def cruce_room(out: Path, percent: int, samples: int) -> None:
    import sets_marca as sets

    scene = bpy.context.scene
    sets.escritorio_noche({"fps": FPS, "total_frames": ROOM_FRAMES})
    base, yaw = ROOM_PORTAL
    holder = empty("PORTAL", tuple(base), None)
    portal_ring(holder, yaw, view=out / "portal_view.png")
    bpy.context.view_layer.update()
    m = holder.matrix_world
    centre = m @ Vector((0, 0, 1.0))
    disc_holder = bpy.data.objects["portal_ring_holder"]

    # The lead standing beside Claude, both facing the portal.
    hero = placeholders.build("novato", character_meta("novato"))
    hero_at = Vector((0.15, -1.45, 0))  # to Claude's left, so neither hides the other
    hero.location = hero_at
    hero.rotation_euler.z = rad(165)
    claude = placeholders.build("claude", character_meta("claude"))
    claude_at = Vector((1.3, -1.0, 0))
    claude.location = claude_at
    claude.rotation_euler.z = rad(165)
    for o in claude.children_recursive:
        if o.name.startswith("claude_cup"):
            o.hide_render = True
    lid = bpy.data.objects["lid.claude"]
    c_head = bpy.data.objects["ctrl_head.claude"]
    brows = [bpy.data.objects["brow_L.claude"], bpy.data.objects["brow_R.claude"]]
    d_head = bpy.data.objects["ctrl_head.novato"]
    d_body = bpy.data.objects["ctrl_body.novato"]
    d_arm = bpy.data.objects["ctrl_arm_R.novato"]
    d_fore = bpy.data.objects["ctrl_forearm_R.novato"]
    lid0, brow0 = lid.location.copy(), [b.location.copy() for b in brows]
    rng = random.Random(1)

    # Loose papers on the floor and desk, sucked in one after another.
    paper = material("loose_paper", "#f4efe4", 0.8, emission=0.15)
    papers = []
    for i in range(9):
        p0 = Vector((rng.uniform(-1.2, 1.0), rng.uniform(-1.6, 0.9), rng.choice((0.01, 0.75))))
        o = primitive("cube", f"paper_{i}", tuple(p0), (0.1, 0.075, 0.003), None, paper)
        o.rotation_euler.z = rng.uniform(0, 3)
        papers.append((o, p0, rng.randint(8, 40), rng.uniform(4, 9)))

    C_IN, C_GONE = 40, 56  # Claude swallowed
    D_IN, D_GONE = 58, 74  # The lead follows
    claude_suck = sucked(claude, claude_at, centre, C_IN, C_GONE, spin=0.6, stretch=0.7)
    hero_suck = sucked(hero, hero_at, centre, D_IN, D_GONE, spin=-0.3, stretch=0.35)
    paper_fns = [sucked(o, p0, centre + Vector((0, 0, 0.35)), f0, f0 + 22, spin=sp, stretch=0.0) for o, p0, f0, sp in papers]

    def frame(f):
        claude_suck(f)
        hero_suck(f)
        for fn in paper_fns:
            fn(f)
        # Lid simmering from the start, wilder as the pull grows.
        amp = 0.012 * (0.4 + 1.6 * ramp(f, 1, C_IN))
        lid.location = lid0 + Vector((0, 0, amp * abs(math.sin(f * 1.9)) * (1 if f < C_GONE else 0)))
        lid.rotation_euler = (rad(4 * math.sin(f * 1.3)) * ramp(f, 1, C_IN), rad(5 * math.sin(f * 1.7)) * ramp(f, 1, C_IN), 0)
        # Claude glances at the lead ("¿vamos?"), brows up, then back to the light.
        look = smooth(ramp(f, 18, 25)) - smooth(ramp(f, 33, 39))
        c_head.rotation_euler = (0, rad(-6 * look), rad(-48 * look))
        for b, b0 in zip(brows, brow0):
            b.location = b0 + Vector((0, 0, 0.03 * look))
        # The lead: looks at Claude when it glances, then lunges an arm out as it is swallowed, leaning in.
        reach = smooth(ramp(f, C_IN + 2, C_IN + 10))
        d_head.rotation_euler = (rad(10 * look), 0, rad(-25 * look))
        q_arm = Vector((rad(-85 * reach), 0, rad(15 * reach)))
        d_arm.rotation_quaternion = Euler(q_arm).to_quaternion()
        d_fore.rotation_quaternion = Euler((rad(-10 * reach), 0, 0)).to_quaternion()
        d_body.rotation_euler = (rad(14 * reach), 0, 0)

    objs = [claude, hero, lid, c_head, *brows, d_head, d_body, d_arm, d_fore, *[p[0] for p in papers]]
    bake_frames(objs, ROOM_FRAMES, frame)
    ripple(disc_holder, "claude", C_GONE - 2)
    ripple(disc_holder, "hero", D_GONE - 2)
    flash_ring([C_GONE - 2, D_GONE - 2])
    spill = bpy.data.objects["portal_spill"].data
    for f, e in ((1, 200), (C_IN, 320), (C_GONE, 700), (C_GONE + 8, 320), (D_GONE, 800), (ROOM_FRAMES, 600)):
        spill.energy = e
        spill.keyframe_insert("energy", frame=f)

    normal = (m.to_3x3() @ Vector((0, -1, 0))).normalized()  # towards the room

    def cam_pose(f):
        start, look0 = Vector((1.5, -4.5, 1.4)), Vector((1.0, -0.5, 0.7))
        hold = Vector((1.45, -3.9, 1.3))
        if f <= D_GONE:  # a slow creep while it happens
            t = smooth(ramp(f, 1, D_GONE))
            return start.lerp(hold, t), look0.lerp(centre, 0.4 * t)
        t = ease_in(ramp(f, D_GONE, ROOM_FRAMES), 2.0)  # then dives in after them
        end = centre + normal * 0.25
        return hold.lerp(end, t), (look0.lerp(centre, 0.4)).lerp(centre, min(1.0, t * 2))

    cam = camera("cam_enter", (0, 0, 0), (0, 1, 0), 26)
    cam.data.clip_start = 0.01
    scene.camera = cam

    def cam_frame(f):
        loc, target = cam_pose(f)
        cam.location = loc
        cam.rotation_euler = (Vector(target) - loc).to_track_quat("-Z", "Y").to_euler()

    bake_frames([cam], ROOM_FRAMES, cam_frame)
    bloom(scene, 0.9, 0.7)
    render_settings(scene, percent, samples, 0.2)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "cruce_room.blend"))
    render_frames(scene, out, "a", ROOM_FRAMES)


def render_frames(scene, out: Path, prefix: str, frames: int) -> None:
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.use_persistent_data = True
    scene.render.filepath = str(out / f"{prefix}_")
    bpy.ops.render.render(animation=True)


def world_life(frames: int) -> None:
    """The world breathes: clouds drift, waterfalls pour, notes and letters bob."""
    for o in bpy.data.objects:
        n = o.name
        if n.startswith("cloud_") and n != "cloud_src":
            o.keyframe_insert("location", frame=1)
            o.location.x += 0.012 * frames
            o.keyframe_insert("location", frame=frames)
        elif n.startswith(("note_", "letter_", "lib_book_")):
            z0, ph = o.location.z, hash(n) % 100 / 15
            for f in range(1, frames + 1, 6):
                o.location.z = z0 + 0.12 * math.sin(f / 18 + ph)
                o.keyframe_insert("location", index=2, frame=f)
            o.location.z = z0
    wave = next(n for n in bpy.data.materials["waterfall"].node_tree.nodes if n.bl_idname == "ShaderNodeTexWave")
    wave.bands_direction = "Y"  # streaks run down the fall
    key_value(wave.inputs["Phase Offset"], ((1, 0.0), (frames, -40.0)))
    for o in bpy.data.objects:  # linear: no ease at the ends
        ad = o.animation_data
        if ad and ad.action and o.name.startswith("cloud_"):
            _linear(ad.action)
    _linear(bpy.data.materials["waterfall"].node_tree.animation_data.action)


def _linear(action) -> None:
    fcurves = getattr(action, "fcurves", None)
    if fcurves is None:  # Blender 5 layered actions
        fcurves = [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def landing(f: float, f0: float, start: Vector, land: Vector, apex: float, bounces: list[tuple[float, float]]) -> Vector:
    """Ballistic hop from start to land (apex height above the line) in frames f0..f0+bounces[0][0]; then bounces
    (duration frames, height) in place."""
    dur = bounces[0][0]
    if f < f0:
        return start
    t = (f - f0) / dur
    if t <= 1:
        p = start.lerp(land, t)
        p.z = start.z + (land.z - start.z) * t + apex * 4 * t * (1 - t)
        return p
    g = f0 + dur
    for d, h in bounces[1:]:
        if f < g + d:
            u = (f - g) / d
            return land + Vector((0, 0, h * 4 * u * (1 - u)))
        g += d
    return land


def cruce_mundo(out: Path, percent: int, samples: int) -> None:
    scene = bpy.context.scene
    build_mundo()
    ring = empty("PORTAL_OUT", tuple(WORLD_PORTAL))
    portal_ring(ring, 0, light=False)
    bpy.context.view_layer.update()
    mouth = WORLD_PORTAL + Vector((0, 0, 1.0))
    bloom(scene, 1.0, 0.5)
    render_settings(scene, percent, samples, 0.0)
    out.mkdir(parents=True, exist_ok=True)

    def cam_pose(t):
        """Comes out just behind them, holds on the landing, then rises on the world."""
        # Off to the left of the portal (ring on the right edge), clear of it all the way up.
        # Still on the meadow, portal on the right of frame, the landing spot ahead of it.
        start, hold, end = Vector((-0.6, -4.2, 1.15)), Vector((-0.7, -4.5, 1.3)), Vector((-0.4, -4.3, 3.4))
        look0, look_hold, look1 = Vector((2.0, 0.8, 0.7)), Vector((1.8, 2.0, 0.8)), Vector((3, 20, 4.0))
        if t < 0.38:
            u = smooth(t / 0.38)
            return start.lerp(hold, u), look0.lerp(look_hold, u)
        u = smooth((t - 0.38) / 0.62)
        return hold.lerp(end, u), look_hold.lerp(look1, u)

    # The portal's view from the room = this shot's opening frame minus people, so the cut matches.
    loc, target = cam_pose(0)
    pct = scene.render.resolution_percentage
    scene.render.resolution_percentage = 100
    for o in ring.children_recursive:
        o.hide_render = True
    shoot(scene, camera("cam_view", tuple(loc), tuple(target), 24), out / "portal_view.png", (720, 720))
    for o in ring.children_recursive:
        o.hide_render = False
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1080, 1920, pct

    claude = placeholders.build("claude", character_meta("claude"))
    for o in claude.children_recursive:
        if o.name.startswith("claude_cup"):
            o.hide_render = True
    hero = placeholders.build("novato", character_meta("novato"))
    lid = bpy.data.objects["lid.claude"]
    lid0 = lid.location.copy()
    c_head = bpy.data.objects["ctrl_head.claude"]
    c_body = bpy.data.objects["ctrl_body.claude"]
    d_body = bpy.data.objects["ctrl_body.novato"]
    d_head = bpy.data.objects["ctrl_head.novato"]
    d_arms = [bpy.data.objects[f"ctrl_arm_{s}.novato"] for s in "LR"]

    C_OUT, D_OUT = 4, 14
    c_land, d_land = Vector((2.2, 2.6, 0)), Vector((1.2, 3.0, 0))
    c_bounces = [(16, 0), (9, 0.32), (6, 0.1)]
    d_bounces = [(17, 0)]
    c_hit = C_OUT + 16
    d_hit = D_OUT + 17
    LID_UP, LID_DOWN = c_hit, c_hit + 26

    def frame(f):
        # Claude: shot out of the mouth, tumbling, then bounces.
        claude.location = landing(f, C_OUT, mouth - Vector((0, 0, 0.25)), c_land, 1.0, c_bounces)
        tumble = ramp(f, C_OUT, c_hit)
        claude.rotation_euler = (rad(-360 * tumble), 0, rad(180))
        vis = 1.0 if f >= C_OUT else 0.0
        sq = 0.0  # squash on each impact
        for g in (c_hit, c_hit + 9, c_hit + 15):
            if g <= f < g + 4:
                sq = 0.25 * (1 - (f - g) / 4)
        claude.scale = (vis * (1 + sq), vis * (1 + sq), vis * (1 - sq))
        # Its lid flies off on the first impact, spins, lands back on (a little crooked, then settles).
        if LID_UP <= f < LID_DOWN:
            u = (f - LID_UP) / (LID_DOWN - LID_UP)
            lid.location = lid0 + Vector((0.05 * math.sin(u * 3), 0, 1.1 * 4 * u * (1 - u)))
            lid.rotation_euler = (rad(540 * u), rad(90 * u), 0)
        else:
            settle = math.exp(-(f - LID_DOWN) / 4) if f >= LID_DOWN else 0
            lid.location = lid0 + Vector((0, 0, 0.015 * settle * abs(math.sin(f * 2.2))))
            lid.rotation_euler = (0, rad(12 * settle), 0)
        # The lead: tumbles out after, lands on his feet with a stagger.
        hero.location = landing(f, D_OUT, mouth - Vector((0, 0, 0.9)), d_land, 0.6, d_bounces)
        dvis = 1.0 if f >= D_OUT else 0.0
        st = smooth(ramp(f, d_hit, d_hit + 5)) - smooth(ramp(f, d_hit + 8, d_hit + 22))
        hero.scale = (dvis, dvis, dvis * (1 - 0.18 * st))
        hero.rotation_euler = (rad(-25 * (1 - ramp(f, D_OUT, d_hit)) + 18 * st), 0, rad(180))
        flail = 1 - smooth(ramp(f, d_hit, d_hit + 12))
        for i, a in enumerate(d_arms):
            a.rotation_quaternion = Euler((rad(-75 * flail), 0, rad((1 if i == 0 else -1) * 30 * flail))).to_quaternion()
        # Both look up at the world.
        up = smooth(ramp(f, 62, 80))
        c_head.rotation_euler = (rad(-14 * up), 0, rad(10 * up * (1 - ramp(f, 95, 110))))
        d_head.rotation_euler = (rad(-20 * up), 0, rad(-12 * up))
        d_body.rotation_euler = (rad(-4 * up), 0, 0)
        c_body.rotation_euler = (0, 0, 0)

    bake_frames([claude, lid, c_head, c_body, hero, d_body, d_head, *d_arms], WORLD_FRAMES, frame)
    flash_ring([C_OUT, D_OUT], base=7.0)
    world_life(WORLD_FRAMES)

    cam = camera("cam_exit", (0, 0, 0), (0, 1, 0), 24)
    scene.camera = cam

    def cam_frame(f):
        loc, target = cam_pose((f - 1) / (WORLD_FRAMES - 1))
        cam.location = loc
        cam.rotation_euler = (Vector(target) - loc).to_track_quat("-Z", "Y").to_euler()

    bake_frames([cam], WORLD_FRAMES, cam_frame)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "cruce_mundo.blend"))
    render_frames(scene, out, "b", WORLD_FRAMES)


# --- design options for "a person's light + the AI listening to it" (stills) ----------------------------------------

OTHER_AIS = [  # other AIs as pottery too: same family as Claude, other clays and glazes (no brands)
    {"color": "#7d8c9c", "dark": "#4a5562", "glaze": "#bfe9de", "groove": "#5d6b78", "variant": "brick", "seed": 3},
    {"color": "#8a5a7a", "dark": "#53344a", "glaze": "#f2d3a0", "groove": "#6a4060", "variant": "loaf", "seed": 5},
    {"color": "#c9a46a", "dark": "#8a6a3a", "glaze": "#3d6fd8", "groove": "#a0804a", "variant": "loaf", "seed": 8},
]


def other_ai(char_id: str, ceramic: dict, at: Vector, yaw: float, scale: float = 0.62, look_up: float = 0.0, arm: float = 0.0):
    """A small pottery AI (not ours: other clay, other glaze), turned towards its person's light."""
    meta = dict(character_meta("claude"))
    meta["id"] = char_id
    meta["ceramic"] = {**meta.get("ceramic", {}), **ceramic}
    root = placeholders.build(char_id, meta)
    root.location, root.rotation_euler.z, root.scale = at, rad(yaw), (scale,) * 3
    for o in root.children_recursive:
        if "cup" in o.name:
            o.hide_render = True
    head = bpy.data.objects.get(f"ctrl_head.{char_id}")
    if head:
        head.rotation_euler.x = rad(-look_up)
    for side, k in (("R", 1.0), ("L", 0.35)):
        a = bpy.data.objects.get(f"ctrl_arm_{side}.{char_id}")
        if a:
            a.rotation_euler.x = rad(-arm * k)
    think = bpy.data.objects.get(f"think_light.{char_id}")
    if think:
        think.color = (0.6, 0, 0, 1)  # listening: its own little light on
    return root


def _glass() -> bpy.types.Material:
    if "jar_glass" in bpy.data.materials:
        return bpy.data.materials["jar_glass"]
    mat = material("jar_glass", "#dff3ff", 0.05)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = 0.18
    bsdf.inputs["Specular IOR Level"].default_value = 0.9
    mat.surface_render_method = "BLENDED"
    return mat


def light_lantern(root, at: Vector, k: float = 1.0):
    """A: a paper lantern (farolillo), glowing from inside, ribbed, with a little cord."""
    paper = material("lantern_paper", "#ffb860", 0.6, emission=1.6)
    wood = material("lantern_wood", "#3a2418", 0.8)
    body = _flat(primitive("cylinder", "lantern", tuple(at), (0.16 * k, 0.16 * k, 0.2 * k), root, paper, vertices=10))
    for z, r in ((0.2, 0.12), (-0.2, 0.12)):
        primitive("cylinder", "lantern_cap", tuple(at + Vector((0, 0, z * k))), (r * k, r * k, 0.02 * k), root, wood, vertices=10)
    for i in range(10):  # ribs
        a = i / 10 * 2 * math.pi
        primitive("cube", "lantern_rib", tuple(at + Vector((math.cos(a) * 0.162 * k, math.sin(a) * 0.162 * k, 0))), (0.004 * k, 0.004 * k, 0.2 * k),
                  root, wood).rotation_euler.z = a
    primitive("cylinder", "lantern_cord", tuple(at + Vector((0, 0, 0.42 * k))), (0.004, 0.004, 0.2 * k), root, wood, vertices=4)
    props.point_light("lantern_glow", tuple(at), "#ffb060", 18 * k, 0.12 * k)
    return body


def light_jar(root, at: Vector, k: float = 1.0):
    """B: a small glass jar with a warm flame-like glow inside (a 'tarrito' of light), cork lid."""
    primitive("cylinder", "jar_glass", tuple(at), (0.11 * k, 0.11 * k, 0.15 * k), root, _glass(), vertices=16)
    primitive("cylinder", "jar_cork", tuple(at + Vector((0, 0, 0.17 * k))), (0.085 * k, 0.085 * k, 0.03 * k), root,
              material("cork", "#b08a5a", 0.9), vertices=12)
    core = material("jar_core", "#ffc070", 0.2, emission=7.0)
    _smooth(primitive("uv_sphere", "jar_core", tuple(at + Vector((0, 0, -0.03 * k))), (0.045 * k, 0.045 * k, 0.07 * k), root, core, segments=12, ring_count=8))
    for i in range(5):  # a few sparks drifting inside
        a = i * 1.3
        primitive("ico_sphere", "jar_spark", tuple(at + Vector((math.cos(a) * 0.06 * k, math.sin(a) * 0.06 * k, (0.02 + 0.02 * i) * k))),
                  (0.008 * k,) * 3, root, core, subdivisions=1)
    props.point_light("jar_glow", tuple(at), "#ffb060", 30 * k, 0.06 * k)


def light_orb(root, at: Vector, k: float = 1.0):
    """C: a soul-like orb: bright core, soft halo shell, sparks orbiting it."""
    core = material("orb_core", "#ffe2a8", 0.2, emission=6.0)
    _smooth(primitive("uv_sphere", "orb_core", tuple(at), (0.05 * k,) * 3, root, core, segments=16, ring_count=10))
    halo = material("orb_halo", "#ffb050", 0.2, emission=0.8)
    halo.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.25
    halo.surface_render_method = "BLENDED"
    _smooth(primitive("uv_sphere", "orb_halo", tuple(at), (0.13 * k,) * 3, root, halo, segments=20, ring_count=12))
    spark = material("orb_spark", "#ffd080", 0.2, emission=12.0)
    for i in range(9):
        a, h = i / 9 * 2 * math.pi, math.sin(i * 1.7) * 0.08
        primitive("ico_sphere", "orb_spark", tuple(at + Vector((math.cos(a) * 0.2 * k, math.sin(a) * 0.2 * k, h * k))), (0.01 * k,) * 3, root, spark, subdivisions=1)
    props.point_light("orb_glow", tuple(at), "#ffb060", 15 * k, 0.05 * k)


def parejas(out: Path, percent: int, samples: int) -> None:
    """Three ways to show 'a person's light and the AI listening to it', side by side on the meadow at dusk."""
    scene = bpy.context.scene
    world = build_mundo("atardecer")
    people_lights(world, [ai_template(i, *k) for i, k in enumerate(AI_KINDS)], [], Vector((0, -12, 3)), near=False, bubbles=False)
    root = world["root"]
    spots = {"a_farolillo": Vector((-3.2, 1.0, 0)), "b_tarro": Vector((0.0, 1.0, 0)), "c_alma": Vector((3.2, 1.0, 0))}
    # A: the lantern hangs at its eye height, it looks up at it with a hand raised towards it.
    p = spots["a_farolillo"]
    light_lantern(root, p + Vector((0.2, -0.05, 0.58)), 0.6)
    other_ai("ai_a", OTHER_AIS[0], p + Vector((-0.1, 0, 0)), 30, look_up=16, arm=70)
    # B: it sits with the jar held against it, the glow lighting its face from below.
    p = spots["b_tarro"]
    other_ai("ai_b", OTHER_AIS[1], p, 15, look_up=-8, arm=55)
    light_jar(root, p + Vector((0.2, -0.16, 0.13)), 0.9)
    # C: the orb floats right in front of its face, sparks circling; it leans in, listening.
    p = spots["c_alma"]
    other_ai("ai_c", OTHER_AIS[2], p, -25, look_up=10, arm=25)
    light_orb(root, p + Vector((-0.22, -0.2, 0.45)))
    bloom(scene, 0.8, 0.9)
    render_settings(scene, percent, samples, MOODS["atardecer"]["exposure"])
    out.mkdir(parents=True, exist_ok=True)
    for name, p in spots.items():
        cam = camera(f"cam_{name}", tuple(p + Vector((0.4, -1.9, 0.6))), tuple(p + Vector((0.05, 0, 0.3))), 50, 2.4)
        shoot(scene, cam, out / f"{name}.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "parejas.blend"))


def main(out_dir: str, which: str, percent: str = "50", samples: str = "16") -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    {"mundo": mundo, "portal": portal, "atardecer": atardecer, "cruce_mundo": cruce_mundo, "cruce_room": cruce_room, "parejas": parejas}[which](Path(out_dir), int(percent), int(samples))


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1 :])
