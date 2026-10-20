"""Set `mundo` (miniseries "El mundo de dentro"): the night room AND the world inside, in one scene, joined only by
the portal. The world (built by world_proto.py around its own origin) sits far away at WORLD_AT, so neither can see
the other; one world shader mixes the room's galaxy with the world's day and dusk skies, keyed per beat.

Beats are recognised by their camera (see reels/schema.py Camera): `portal_open` opens the portal, `cruce` is the
crossing (sucked in, flash, spat out onto the meadow), the first `mundo_wide` after it brings the dusk and the
people's lights, `luz_sola` turns them towards the lonely islet, `negro` cuts to black.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bpy
from mathutils import Euler, Vector

import props
import world_proto as wp
from lib import bake, empty, find, material, rad

WORLD_AT = Vector((3000.0, 0.0, 0.0))
ROOM_PORTAL, ROOM_PORTAL_YAW = Vector((1.55, -0.1, 0.0)), -15.0
WORLD_PORTAL = Vector((2.6, -1.2, 0.0))  # local to the world
LAND = {"claude": Vector((2.2, 2.6, 0.0)), "novato": Vector((1.15, 3.0, 0.0))}  # where they end up on the meadow
YAW = {"claude": 170.0, "novato": 186.0}  # looking out at the islands (figures face -Y at yaw 0)
CLOSE_PAIRS = {  # the pairs whose voices we hear (no text: they talk out loud), local
    "luces_cerca": (Vector((-0.8, 6.0, 1.4)), "voz_mx"),
    "luces_cerca_b": (Vector((2.6, 8.6, 3.2)), "voz_co"),
}
# The crossing, in frames from the start of the `cruce` beat (~7 s): they reach for each other, are dragged in,
# the camera dives into the disc, flies down a tunnel of lights and bursts out into the sky over the world.
REACH = (0, 22)
REACH_SIGN = 1  # which way Claude's right arm swings out to the lead
PULL = (20, 56)
HANDS = 26  # frames on the close-up of their hands
DIVE = (52, 72)
FLASH_AT = 134  # out of the tunnel (2 s of it), into the world's sky


def _w(v) -> Vector:
    return WORLD_AT + Vector(v)


def _beats(timeline: dict, camera: str) -> list[dict]:
    return [b for b in timeline["beats"] if b["camera"] == camera]


def _first(timeline: dict, camera: str) -> dict | None:
    bs = _beats(timeline, camera)
    return bs[0] if bs else None


def build(timeline: dict) -> dict:
    """Room + world + portal. Returns the room's anchors, plus the hooks build_scene calls later."""
    import sets_marca as sets

    anchors = sets.escritorio_noche(timeline)
    for o in bpy.data.objects:  # the mug and the desk books sit right where their hands meet
        near_desk = (o.matrix_world.translation - Vector((0.1, 0.8, 0.75))).length < 0.3
        if o.name.startswith(("mug_body", "mug_coffee", "mug_handle")) or (o.name.startswith("K_books") and near_desk):
            o.hide_render = True
            for c in o.children_recursive:
                c.hide_render = True
    episode_dir = Path(timeline["_episode_dir"])

    # The world, built at the origin and moved out to WORLD_AT.
    bb = empty(wp.BILLBOARD)  # bubbles (even the lonely one's) face whichever camera is live
    before = set(bpy.data.objects)
    world = wp.build_mundo("dia", make_world=False)
    wp.lonely_islet(world["root"], bubbles=False)  # the voices are heard; no text over the lights
    holder = empty("WORLD_AT", tuple(WORLD_AT))
    _adopt(before, holder)
    _skies(timeline)
    view = episode_dir / "portal_view.png"
    if not view.exists() and not _direct(timeline):
        _render_view(view, _flash_frame(timeline) + 2)

    before = set(bpy.data.objects)
    tpls = [wp.ai_template(i, *k) for i, k in enumerate(wp.AI_KINDS)]
    wide_cam = Vector((-1.2, -4.8, 3.2))
    # The near layer is ours (CLOSE_PAIRS, heard not read): no hand-placed talking pairs with text.
    wp.people_lights(world, tpls, [p for p, _ in CLOSE_PAIRS.values()] + [LAND["novato"], LAND["claude"]], wide_cam, near=False, bubbles=False)
    rng = random.Random(5)
    for name, (at, _) in CLOSE_PAIRS.items():
        _close_pair(world["root"], tpls, name, at, rng)
    _adopt(before, holder)
    anchors["world"] = {"root": world["root"], "billboard": bb}

    if any(b["camera"].startswith("cuarto_chica") for b in timeline["beats"]):
        import cuarto_chica

        room = cuarto_chica.build()
        anchors.setdefault("slots", {})["sofa"] = tuple(room["slot"])
        anchors.setdefault("facing", {})["sofa"] = room["facing"]
        anchors["chica_face"] = room["face"]
        bpy.context.scene["chica_face"] = list(room["face"])
    if _direct(timeline):  # part 2 starts in the world: no portal, no tunnel
        anchors["on_characters"] = on_characters
        anchors["after_cameras"] = after_cameras
        return anchors
    # The door in the room (its disc shows the world).
    portal = empty("PORTAL", tuple(ROOM_PORTAL))
    wp.portal_ring(portal, ROOM_PORTAL_YAW, view=view)
    for img in bpy.data.images:  # inside the .blend: the cloud machine only gets the scene file
        if img.filepath and Path(bpy.path.abspath(img.filepath)).name == view.name:
            img.pack()
    _tunnel()
    anchors["on_characters"] = on_characters
    anchors["after_cameras"] = after_cameras
    return anchors


def _adopt(before: set, holder, skip=()) -> None:
    """Parent every new top-level object to holder (keeps their world-space layout, shifted by holder)."""
    for o in set(bpy.data.objects) - before - {holder} - set(skip):
        if o.parent is None:
            o.parent = holder


CLOSE = {}  # camera name -> (jar, its AI, glow light): animated while that person is heard


def _close_pair(root, tpls, name: str, at: Vector, rng) -> None:
    """A big jar of light with its AI close to camera (the words are heard, not read)."""
    # The second pair is mirrored (its AI on the jar's left) so its camera, from the other side, still sees its face.
    side = Vector((-1, 0, 0)) if name == "luces_cerca_b" else Vector((1, 0, 0))
    jar, ai = wp.pair(root, tpls, at, 0.16, rng, right=side, bubbles=False)
    # The light lights its own AI (and reads from the camera side).
    light = props.point_light(f"close_glow_{name}", tuple(at + Vector((-0.2, -0.4, 0.1))), "#ffb347", 25, 0.1)
    light.parent = root
    CLOSE[name] = (jar, ai, light)


def _close_pairs_act(timeline: dict) -> None:
    """While its person talks, the jar's light beats with the words and its AI turns to it and leans in to listen."""
    for name, (jar, ai, light) in CLOSE.items():
        beats = [b for b in timeline["beats"] if b["camera"] == name and b.get("audio")]
        if not beats:
            continue
        yaw, tilt = ai.rotation_euler.z, ai.rotation_euler.x
        s0 = beats[0]["start_frame"]
        # Before: half turned away (it was looking out at the world); as the voice starts it turns to the jar.
        for f, k in ((0, 0.0), (s0 - 2, 0.0), (s0 + 14, 1.0)):
            ai.rotation_euler.z = yaw - rad(35) * (1 - k) * (1 if name == "luces_cerca" else -1)
            ai.rotation_euler.x = tilt + rad(9) * k
            ai.keyframe_insert("rotation_euler", frame=f)
        keys = [(0, 25.0)]
        for b in beats:
            a = b["audio"]
            t0 = b["start_frame"] + round(a["offset"] * timeline["fps"])
            for w in a.get("words", []):
                ws, we = t0 + round(w["start"] * timeline["fps"]), t0 + round(w["end"] * timeline["fps"])
                keys += [(ws, 25.0), (ws + 3, 60.0), (max(ws + 4, we), 35.0), (we + 3, 25.0)]
        keys.sort()
        _key_prop(light.data, "energy", keys)


# --- one world shader for both places ---------------------------------------------------------------------------


def _skies(timeline: dict) -> None:
    """Room galaxy <-> world sky (cut at the flash), and day -> dusk inside the world (over the dusk beat)."""
    tree = bpy.context.scene.world.node_tree
    nodes, links = tree.nodes, tree.links
    out = next(n for n in nodes if n.bl_idname == "ShaderNodeOutputWorld")
    galaxy = out.inputs["Surface"].links[0].from_socket
    day = wp.sky_shader(nodes, links, wp.MOODS["dia"])
    dusk = wp.sky_shader(nodes, links, wp.MOODS["atardecer"])
    mix_sky = nodes.new("ShaderNodeMixShader")
    mix_sky.name = "dusk"
    links.new(day, mix_sky.inputs[1])
    links.new(dusk, mix_sky.inputs[2])
    inside = nodes.new("ShaderNodeMixShader")
    inside.name = "inside"
    links.new(galaxy, inside.inputs[1])
    links.new(mix_sky.outputs[0], inside.inputs[2])
    links.new(inside.outputs[0], out.inputs["Surface"])

    if _direct(timeline):  # already there, already dusk
        inside.inputs["Fac"].default_value = 1.0
        mix_sky.inputs["Fac"].default_value = 1.0
        sun = bpy.data.objects["sun"]
        d1, e1 = wp.MOODS["atardecer"]["sun"]
        sun.data.energy, sun.data.color = e1, wp.srgb(d1)[:3]
        sun.rotation_euler = (-Vector(wp.MOODS["atardecer"]["sun_dir"]).normalized()).to_track_quat("-Z", "Y").to_euler()
        return
    flash, dusk_span = _flash_frame(timeline), _dusk_span(timeline)
    _key(inside.inputs["Fac"], [(0, 0.0), (flash - 1, 0.0), (flash, 1.0)], constant=True)
    _key(mix_sky.inputs["Fac"], [(0, 0.0), (dusk_span[0], 0.0), (dusk_span[1], 1.0)])
    sun = bpy.data.objects["sun"]
    (d0, e0), (d1, e1) = (wp.MOODS["dia"]["sun"], wp.MOODS["atardecer"]["sun"])
    _key_prop(sun.data, "energy", [(0, 0.0), (flash - 1, 0.0), (flash, e0), (dusk_span[0], e0), (dusk_span[1], e1)])
    for i, (a, b) in enumerate(zip(wp.srgb(d0)[:3], wp.srgb(d1)[:3])):
        _key_prop(sun.data, "color", [(dusk_span[0], a), (dusk_span[1], b)], index=i)
    q0 = (-Vector(wp.MOODS["dia"]["sun_dir"]).normalized()).to_track_quat("-Z", "Y").to_euler()
    q1 = (-Vector(wp.MOODS["atardecer"]["sun_dir"]).normalized()).to_track_quat("-Z", "Y").to_euler()
    for i in range(3):
        _key_prop(sun, "rotation_euler", [(dusk_span[0], q0[i]), (dusk_span[1], q1[i])], index=i)


def _key(socket, frames_values, constant: bool = False) -> None:
    for f, v in frames_values:
        socket.default_value = v
        socket.keyframe_insert("default_value", frame=f)
    if constant:
        _interp(socket.id_data, "CONSTANT")


def _key_prop(owner, prop: str, frames_values, index: int = -1) -> None:
    for f, v in frames_values:
        if index < 0:
            setattr(owner, prop, v)
        else:
            getattr(owner, prop)[index] = v
        owner.keyframe_insert(prop, index=index, frame=f)


def _interp(id_data, mode: str) -> None:
    ad = id_data.animation_data
    if not (ad and ad.action):
        return
    action = ad.action
    curves = getattr(action, "fcurves", None)
    if curves is None:
        curves = [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        if "inside" in fc.data_path:
            for k in fc.keyframe_points:
                k.interpolation = mode


def _flash_frame(timeline: dict) -> int:
    b = _first(timeline, "cruce")
    return b["start_frame"] + FLASH_AT if b else 0


def _dusk_span(timeline: dict) -> tuple[int, int]:
    """The first wide shot after arriving is where the evening falls."""
    flash = _flash_frame(timeline)
    b = next((b for b in timeline["beats"] if b["camera"] == "mundo_wide" and b["start_frame"] > flash), None)
    if not b:
        return (timeline["total_frames"], timeline["total_frames"] + 1)
    return (b["start_frame"], b["end_frame"])


def _render_view(path: Path, frame: int) -> None:
    """What the room sees through the portal: the meadow from the world-side portal, by day, nobody there yet."""
    scene = bpy.context.scene
    keep = (scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    scene.frame_set(frame)  # inside the world, still daytime (the skies are keyed)
    loc, target = _exit_pose(0.0)
    cam = wp.camera("cam_portal_view", tuple(loc), tuple(target), 24)
    scene.camera = cam
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = keep
    bpy.data.objects.remove(cam)
    scene.frame_set(0)


def _exit_pose(t: float) -> tuple[Vector, Vector]:
    """World side of the crossing: beside the portal, holding on the landing, then rising on the world."""
    start, hold, end = Vector((-0.6, -4.2, 1.15)), Vector((-0.7, -4.5, 1.3)), Vector((-0.4, -4.3, 3.0))
    look0, look_hold, look1 = Vector((2.0, 0.8, 0.7)), Vector((1.8, 2.4, 0.8)), Vector((3, 20, 4.0))
    if t < 0.45:
        u = wp.smooth(t / 0.45)
        return _w(start.lerp(hold, u)), _w(look0.lerp(look_hold, u))
    u = wp.smooth((t - 0.45) / 0.55)
    return _w(hold.lerp(end, u)), _w(look_hold.lerp(look1, u))


# --- characters: the crossing, staging in the world, extra cameras ------------------------------------------------


def on_characters(timeline: dict, roots: dict, anchors: dict, heads: dict) -> dict:
    """Animate the crossing and the world staging on the character roots; return the world's camera presets."""
    if _direct(timeline):
        _place_direct(timeline, roots)
        return _world_cameras(timeline, roots)
    cross = _first(timeline, "cruce")
    portal_open = _first(timeline, "portal_open")
    if portal_open:
        _open_portal(portal_open)
        _levitate(portal_open, cross)
    if cross:
        _crossing(timeline, roots, cross)
    return _world_cameras(timeline, roots)


def _open_portal(beat: dict) -> None:
    holder = bpy.data.objects["PORTAL"]
    s0 = beat["start_frame"]
    for f, s in ((0, 0.001), (s0, 0.001), (s0 + 24, 1.0)):
        holder.scale = (s, s, s)
        holder.keyframe_insert("scale", frame=f)
    spill = bpy.data.objects["portal_spill"].data
    _key_prop(spill, "energy", [(0, 0.0), (s0, 0.0), (s0 + 24, 260.0)])
    glow = bpy.data.objects["portal_glow"].data
    _key_prop(glow, "energy", [(0, 0.0), (s0, 0.0), (s0 + 24, 60.0)])
    # Loose papers on the floor start to slide towards it, and are swallowed during the crossing.
    rng = random.Random(1)
    centre = ROOM_PORTAL + Vector((0, 0, 1.0))
    paper = material("loose_paper", "#f4efe4", 0.8, emission=0.15)
    for i in range(7):
        p0 = Vector((rng.uniform(-1.0, 1.4), rng.uniform(-1.4, 0.5), 0.01))
        o = wp.primitive("cube", f"paper_{i}", tuple(p0), (0.1, 0.075, 0.003), None, paper)
        o.rotation_euler.z = rng.uniform(0, 3)
        f0, f1 = s0 + rng.randint(10, 40), s0 + 90 + rng.randint(0, 30)
        fn = wp.sucked(o, p0, centre + Vector((0, 0, 0.35)), f0, f1, spin=rng.uniform(4, 9), stretch=0.0)
        frames = list(range(0, f1 + 2))
        for f in frames:
            fn(f)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)
            o.keyframe_insert("scale", frame=f)


def _crossing(timeline: dict, roots: dict, beat: dict) -> None:
    """They reach for each other, the portal drags them in together (slow, then a rush); after the tunnel they fall
    out of the sky over the world and land on the meadow (Claude bounces, its lid flies off and lands back on)."""
    S = beat["start_frame"]
    F = S + FLASH_AT
    centre = ROOM_PORTAL + Vector((0, 0, 1.0))
    total = timeline["total_frames"]
    turn = _islet_turn(timeline)
    plans = {  # pulled in (from, to), dropped from the sky at, lands at, bounces (frames, height)
        "claude": (S + PULL[0], S + PULL[1] - 4, _w((0.6, -11.0, 17.0)), F + 48, [(9, 0.32), (6, 0.1)]),
        "novato": (S + PULL[0] + 3, S + PULL[1], _w((-0.4, -10.0, 18.0)), F + 56, []),  # lands on his feet, no hop
    }
    for c, root in roots.items():
        if c not in plans:
            continue
        in0, in1, sky, hit, bounces = plans[c]
        start = root.location.copy()
        yaw0 = root.rotation_euler.z
        s0 = root.scale[0]
        land = _w(LAND[c])
        if c == "novato":
            # He sits behind the desk with his legs hidden: they come back as he is pulled out.
            for o in root.children_recursive:
                if o.name.split(".")[0].startswith(("leg_",)):
                    o.hide_render = o.hide_viewport = False
                    bake(o, "hide_render", -1, [0, in0], [1.0, 0.0], interp="CONSTANT")
        frames = list(range(0, total))
        locs, rots, scs = [], [], []
        for f in frames:
            if f < in0:
                loc, rz, rx, sc = start, yaw0, 0.0, (s0, s0, s0)
            elif f <= in1 + 1:  # dragged in together: barely moving at first (slow motion), then a rush into the light
                t = (f - in0) / (in1 - in0)
                e = t ** 3
                mid = start.lerp(centre, 0.45) + Vector((0, 0, 0.9 if c == "novato" else 0.5))
                loc = (1 - e) ** 2 * start + 2 * (1 - e) * e * mid + e ** 2 * (centre - Vector((0, 0, 0.35 * s0)))
                k = s0 * (1 - wp.smooth(max(0.0, (t - 0.75) / 0.25)) * 0.99)
                st = 1 + (0.8 if c == "claude" else 0.4) * math.sin(math.pi * min(1.0, t * 1.1)) * t
                sc = (k / math.sqrt(st), k / math.sqrt(st), k * st)
                rz, rx = yaw0 + 0.8 * e, 0.0
            elif f < F:  # in the tunnel: nowhere to be seen
                loc, rz, rx, sc = centre, yaw0, 0.0, (0.0, 0.0, 0.0)
            elif f < hit:  # falling out of the sky over the world, tumbling
                t = (f - F) / (hit - F)
                loc = sky.lerp(land, wp.smooth(t))
                loc.z = sky.z + (land.z - sky.z) * t ** 1.7
                rx = rad(-720 * t) if c == "claude" else rad(-360 * t)
                rz = rad(YAW[c])
                sc = (s0, s0, s0)
            else:  # landed: bounces, then they stay (and later turn to the islet)
                g, loc = hit, land.copy()
                for d, h in bounces:
                    if g <= f < g + d:
                        u = (f - g) / d
                        loc = land + Vector((0, 0, h * 4 * u * (1 - u)))
                    g += d
                rx = 0.0
                rz = rad(YAW[c])
                if turn:  # "¿Y esa?": they turn towards the lonely islet
                    to = wp.LONELY - LAND[c]
                    face = math.degrees(math.atan2(to.x, -to.y)) + (8 if c == "claude" else -6)
                    rz = rad(YAW[c] + (face - YAW[c]) * wp.smooth(min(1.0, max(0.0, (f - turn) / 20))))
                # Squash on each impact, eased in and out over 6 frames (an instant squash read as a jitter).
                sq = 0.0
                for g in ([hit] + [hit + sum(b[0] for b in bounces[:i + 1]) for i in range(len(bounces))]):
                    if g <= f < g + 6:
                        sq = (0.1 if c == "claude" else 0.04) * math.sin(math.pi * (f - g) / 6)
                sc = (s0 * (1 + sq), s0 * (1 + sq), s0 * (1 - sq))
            locs.append(loc)
            rots.append((rx, 0.0, rz))
            scs.append(sc)
        for i in range(3):
            bake(root, "location", i, frames, [v[i] for v in locs])
            bake(root, "rotation_euler", i, frames, [v[i] for v in rots])
            bake(root, "scale", i, frames, [v[i] for v in scs])
        if c == "claude":
            _lid_gag(root, hit)
        _reach(root, c, S)


def _reach(root, c: str, S: int) -> None:
    """Claude holds a little arm out to the lead (on its right, behind) and he reaches back with his left hand
    (delta rotations: the rigs own the base poses)."""
    side, euler = ("R", (rad(-35), rad(REACH_SIGN * 75), 0)) if c == "claude" else ("L", (rad(-26), 0, rad(20)))
    arm = find(root, f"ctrl_arm_{side}")
    if not arm:
        return
    for f, k in ((S + REACH[0], 0.0), (S + REACH[1], 1.0), (S + PULL[1], 1.0)):
        e = Euler([v * k for v in euler])
        if arm.rotation_mode == "QUATERNION":
            arm.delta_rotation_quaternion = e.to_quaternion()
            arm.keyframe_insert("delta_rotation_quaternion", frame=f)
        else:
            arm.delta_rotation_euler = e
            arm.keyframe_insert("delta_rotation_euler", frame=f)


def _levitate(beat_open: dict, beat_cross: dict | None) -> None:
    """While the portal opens, small things in the room float up and drift towards it; then it swallows them."""
    rng = random.Random(9)
    centre = ROOM_PORTAL + Vector((0, 0, 1.0))
    s0 = beat_open["start_frame"]
    swallow = beat_cross["start_frame"] + PULL[0] - 6 if beat_cross else s0 + 200
    # Not the books on the desk: they would float right through the close-up of their hands.
    things = [o for o in bpy.data.objects if o.name.split(".")[0] in ("K_books", "K_plantSmall1", "K_speakerSmall")
              and (o.matrix_world.translation - Vector((0.0, 0.8, 0.75))).length > 0.45]
    for o in things:
        p0, r0, k0 = o.location.copy(), o.rotation_euler.copy(), o.scale.copy()
        lift = Vector((0, 0, rng.uniform(0.12, 0.35)))
        spin = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(-1, 1)))
        f_up = s0 + rng.randint(8, 30)
        f_in = swallow + rng.randint(0, 20)
        for f in range(s0, f_in + 22):
            if f < f_up:
                u = 0.0
            else:
                u = wp.smooth(min(1.0, (f - f_up) / 30))
            loc = p0 + lift * u + Vector((0, 0, 0.02 * math.sin(f / 6))) * u
            rot = Vector(r0) + spin * 0.15 * u * (1 + (f - s0) / 60)
            sc = k0.copy()
            if f >= f_in:  # pulled in
                t = min(1.0, (f - f_in) / 20) ** 2
                loc = loc.lerp(centre, t)
                sc = k0 * (1 - t * 0.999)
            o.location, o.rotation_euler, o.scale = loc, Euler(rot), sc
            for path in ("location", "rotation_euler", "scale"):
                o.keyframe_insert(path, frame=f)


TUNNEL_AT = Vector((-3000.0, 0.0, 0.0))
TUNNEL_LEN = 260.0


def _tunnel() -> None:
    """The way between: a tube of thousands of little lights rushing past (the people's lights, before we know)."""
    rng = random.Random(21)
    holder = empty("TUNNEL", tuple(TUNNEL_AT))
    mats = [material(f"tunnel_{c}", c, 0.3, emission=e) for c, e in (("#ffc070", 9.0), ("#ffe2a8", 7.0), ("#7fe0c4", 6.0), ("#a77bff", 5.0))]
    src = wp.primitive("cube", "tunnel_src", (0, 0, -900), (1, 1, 1), holder, mats[0])
    for i in range(900):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.2, 7.0)
        o = src.copy()
        wp.link(o, holder)
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = rng.choice(mats)
        o.location = (math.cos(a) * r, rng.uniform(-10, TUNNEL_LEN + 30), math.sin(a) * r)
        w = rng.uniform(0.015, 0.05)
        o.scale = (w, rng.uniform(0.4, 2.5), w)
    exit_mat = material("tunnel_exit", "#fff6e0", 0.2, emission=40.0)
    disc = wp.primitive("circle", "tunnel_exit", (0, TUNNEL_LEN + 40, 0), (9, 9, 1), holder, exit_mat, vertices=32, fill_type="NGON")
    disc.rotation_euler.x = rad(90)


def _islet_turn(timeline: dict) -> int | None:
    """Frame where they start turning to the islet: just after the lead starts asking about it."""
    if _direct(timeline):
        return None  # part 2: they face it from the first frame
    sola = _first(timeline, "luz_sola")
    if not sola:
        return None
    ask = next((b for b in timeline["beats"] if b["end_frame"] == sola["start_frame"]), sola)
    return ask["start_frame"] + 6


def _lid_gag(root, hit: int) -> None:
    """On the first impact the lid flies off, spins and lands back on (delta transforms: animate.py owns the lid)."""
    lid = find(root, "lid")
    if not lid:
        return
    up, down = hit, hit + 26
    for f in range(up - 1, down + 14):
        if up <= f < down:
            u = (f - up) / (down - up)
            lid.delta_location = (0.05 * math.sin(u * 3), 0, 1.1 * 4 * u * (1 - u))
            lid.delta_rotation_euler = (rad(540 * u), rad(90 * u), 0)
        else:
            settle = math.exp(-(f - down) / 4) if f >= down else 0
            lid.delta_location = (0, 0, 0.015 * settle * abs(math.sin(f * 2.2)))
            lid.delta_rotation_euler = (0, rad(12 * settle), 0)
        lid.keyframe_insert("delta_location", frame=f)
        lid.keyframe_insert("delta_rotation_euler", frame=f)


def _world_cameras(timeline: dict, roots: dict) -> dict:
    """Camera presets in the world (absolute coordinates), from the characters' landed pose."""
    from cameras import _facing

    # Where their heads are once they have landed (the roots are animated: evaluate at that frame).
    cross = _first(timeline, "cruce")
    scene = bpy.context.scene
    scene.frame_set(cross["end_frame"] + 10 if cross else 0)
    heads = {}
    for c, root in roots.items():
        if c in LAND:
            eye = find(root, "eye_L") or find(root, "ctrl_head")
            heads[c] = eye.matrix_world.translation.copy()
    scene.frame_set(0)
    nov, ai = heads.get("novato"), heads.get("claude")
    mid = (nov + ai) / 2
    ynov, yai = (_face_yaw("novato"), _face_yaw("claude")) if _direct(timeline) else (YAW["novato"], YAW["claude"])
    cams = {
        "cruce": dict(loc=Vector((0.6, -3.8, 1.3)), target=ROOM_PORTAL + Vector((0, 0, 1.0)), lens=26, fstop=None),
        "portal_open": dict(loc=Vector((-0.4, -3.9, 1.05)), target=Vector((1.35, -0.2, 0.85)), lens=26, fstop=None),
        "mundo_wide": dict(loc=_w((-1.2, -4.8, 3.2)), end=_w((-1.0, -5.6, 3.6)), target=_w((3, 20, 3.0)), lens=24, fstop=None),
        "mundo_two_shot": dict(loc=mid + Vector((2.6, -1.6, -0.25)), target=mid + Vector((0, 0, -0.3)), lens=32, fstop=4.0),
        "mundo_closeup_novato": dict(loc=nov + _facing(Vector((-0.4, -1.2, -0.12)), ynov), target=nov + Vector((0, 0, -0.15)), lens=40, fstop=2.0),
        # Part 2 (facing the islet): from its other side, so the lead (blurred legs and hoodie) is not right behind it.
        "mundo_closeup_ai": dict(loc=ai + _facing(Vector((0.9, -1.05, 0.12)) if _direct(timeline) else Vector((-0.2, -1.3, 0.05)), yai),
                                 target=ai + Vector((0, 0, -0.08)), lens=55, fstop=2.0),
        # Over their shoulders (from behind-left), past the meadow's edge to the islet hanging just below it.
        # Each shot on it creeps out past them towards the islet, as if drawn to it.
        "luz_sola": dict(loc=_w((-0.9, 2.1, 2.3)), end=_w((1.9, 2.5, 1.7)), target=_w(wp.LONELY + Vector((-0.3, 0, 0.5))), lens=32, fstop=4.0),
        "negro": dict(loc=mid + Vector((0, -2, 0)), target=mid, lens=30, fstop=None),
    }
    # Slow push-ins while the voice plays; the second pair from its other side, lower.
    p = _w(CLOSE_PAIRS["luces_cerca"][0])
    cams["luces_cerca"] = dict(loc=p + Vector((-1.7, -2.0, 0.15)), end=p + Vector((-0.95, -1.15, 0.12)), target=p + Vector((0.25, 0, 0.0)), lens=40, fstop=2.8)
    p = _w(CLOSE_PAIRS["luces_cerca_b"][0])
    cams["luces_cerca_b"] = dict(loc=p + Vector((2.1, -1.5, -0.35)), end=p + Vector((1.25, -0.95, -0.2)), target=p + Vector((-0.3, 0, 0.0)), lens=40, fstop=2.8)
    if _direct(timeline):
        jar = _jar()
        isle = _w(wp.LONELY + ISLE_SPOT)
        to_isle = (jar - nov).normalized()
        cams.update({
            # The opening hook: her jar alone on its rock, close, a slow creep in.
            # The opening: a wide of the whole world at dusk (the "wow"), then without a cut a swoop down to her jar,
            # alone on its rock and flickering (the story). Lands on the close framing as the shot ends.
            "luz_sola_llegada": dict(start=jar + Vector((5.0, -12.0, 5.0)), loc=jar + Vector((-0.5, -1.45, 0.3)), target=jar, lens=45, fstop=2.4),
            "luz_sola_cerca": dict(loc=jar + Vector((-0.5, -1.45, 0.3)), end=jar + Vector((-0.4, -1.2, 0.25)), target=jar, lens=45, fstop=2.4),
            # Claude beside her light, where her AI should be (both in frame).
            "claude_islote": dict(loc=isle.lerp(jar, 0.3) + Vector((-0.1, -2.6, 0.55)), end=isle.lerp(jar, 0.3) + Vector((-0.08, -2.35, 0.5)),
                                  target=isle.lerp(jar, 0.3) + Vector((0, 0, 0.35)), lens=40, fstop=2.8),
            # The lead's gaze going into the light: from over his shoulder, a dive down into the glow.
            # Ends just in front of the jar, a little high and to its right: the dive passes over Claude, not through it.
            "asomarse": dict(loc=nov + Vector((0.25, 0, 0.45)) - to_isle * 1.1, end=jar + Vector((0.2, -0.28, -0.2)), target=jar + Vector((0, 0, -0.22)), lens=35, fstop=None),
            # Reverse: the lead looking at her light, lit by it, a little smile.
            "humano_asomado": dict(loc=nov + to_isle * 1.15 + Vector((0, 0, -0.1)), end=nov + to_isle * 1.0 + Vector((0, 0, -0.08)),
                                 target=nov + Vector((0, 0, -0.12)), lens=45, fstop=2.0),
        })
        face = bpy.context.scene.get("chica_face")
        if face is not None:
            import cuarto_chica

            cams.update(cuarto_chica.cameras(Vector(face)))
    return cams


def after_cameras(timeline: dict, roots: dict) -> None:
    """Things that need the cameras: the crossing's own two cameras, bubbles facing each shot, the dusk lights,
    the lonely light going out, black at the end, a living world."""
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "CAMERA":
            o.data.clip_end = 1500
    cross = _first(timeline, "cruce")
    if cross:
        _crossing_cameras(timeline, cross)
    _billboards(timeline)
    _close_pairs_act(timeline)
    _follow_turn(timeline, roots)
    _face_fill(timeline)
    _cup_stays_home(timeline, roots)
    _dusk_lights(timeline)
    _lonely_goes_out(timeline)
    if _direct(timeline):
        _arms_down(timeline, roots)
        _face_keys(timeline, roots)
        _clear_lenses(timeline, roots)
        _tokens(timeline, roots)
        _lonely_part2(timeline)
        _away_sign(timeline, roots)
        _matchmaker(timeline, roots)
        _room_darkness(timeline)
    black = _first(timeline, "negro")
    if black:
        _key_prop(scene.view_settings, "exposure", [(0, scene.view_settings.exposure), (black["start_frame"] - 1, scene.view_settings.exposure),
                                                   (black["start_frame"], -14.0)])
        _const(scene, "view_settings.exposure")
    wp.world_life(timeline["total_frames"])


def _follow_turn(timeline: dict, roots: dict) -> None:
    """Once they turn to the islet, their close-ups swing round with them (same framing, new facing)."""
    turn = _islet_turn(timeline)
    if not turn:
        return
    scene = bpy.context.scene
    for c, cam_name in (("claude", "CAM_mundo_closeup_ai"), ("novato", "CAM_mundo_closeup_novato")):
        cam, root = bpy.data.objects.get(cam_name), roots.get(c)
        if not (cam and root and cam.animation_data and cam.animation_data.action):
            continue
        to = wp.LONELY - LAND[c]
        face = math.degrees(math.atan2(to.x, -to.y)) + (8 if c == "claude" else -6)
        delta = rad(face - YAW[c])
        pivot = _w(LAND[c])
        frames = range(turn, timeline["total_frames"])
        # Read the original (dolly + handheld) path first, then write the swung one: rewriting while reading
        # made each frame swing the previous frame's already-swung value (the shake).
        base = []
        for f in frames:
            scene.frame_set(f)
            base.append(cam.location.copy())
        aims = [con.target for con in cam.constraints if con.target is not None and con.target.parent is None]
        aim_rest = [t.location.copy() for t in aims]

        def swing(v: Vector, a: float) -> Vector:
            o = v - pivot
            return pivot + Vector((o.x * math.cos(a) - o.y * math.sin(a), o.x * math.sin(a) + o.y * math.cos(a), o.z))

        for f, loc in zip(frames, base):
            a = delta * wp.smooth(min(1.0, (f - turn) / 20))
            cam.location = swing(loc, a)
            cam.keyframe_insert("location", frame=f)
            for t, rest in zip(aims, aim_rest):
                t.location = swing(rest, a)
                t.keyframe_insert("location", frame=f)
    scene.frame_set(0)


def _face_fill(timeline: dict) -> None:
    """Facing the islet they have the setting sun behind them: a soft warm fill (the people's lights) on their faces."""
    turn = 0 if _direct(timeline) else _islet_turn(timeline)
    if turn is None:
        return
    c = "claude"
    to = (wp.LONELY - LAND[c]).normalized()
    at = _w(LAND[c] + to * 1.4 + Vector((0, 0, 0.9)))
    # A narrow spot on its face only (a wide area light lit a bright patch of grass in the islet shots).
    data = bpy.data.lights.new("face_fill", "SPOT")
    data.color, data.spot_size, data.spot_blend, data.shadow_soft_size = wp.srgb("#ffc890")[:3], rad(22), 0.6, 0.15
    light = bpy.data.objects.new("face_fill", data)
    bpy.context.scene.collection.objects.link(light)
    light.location = at
    from lib import look_at

    look_at(light, _w(LAND[c] + Vector((0, 0, 0.35))))
    _key_prop(light.data, "energy", [(0, 0.0), (turn, 0.0), (turn + 20, 18.0)])


def _cup_stays_home(timeline: dict, roots: dict) -> None:
    """Claude's tiny cup and the lead's phone belong in the room: they do not travel (the phone rides on his body rig)."""
    root = roots.get("claude")
    cross = _first(timeline, "cruce")
    gone = cross["start_frame"] + PULL[0] if cross else _flash_frame(timeline)
    things = [o for o in (root.children_recursive if root else []) if "cup" in o.name.split(".")[0]]
    phone = bpy.data.objects.get("PHONE")
    if phone:
        things += [phone, *phone.children_recursive]
    for o in things:
        bake(o, "hide_render", -1, [0, gone], [0.0, 1.0], interp="CONSTANT")


def _const(id_data, path: str) -> None:
    ad = id_data.animation_data
    curves = getattr(ad.action, "fcurves", None)
    if curves is None:
        curves = [fc for layer in ad.action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        if fc.data_path == path:
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


def _crossing_cameras(timeline: dict, beat: dict) -> None:
    """Three cameras, cut under white flashes. Room: a slow creep while they reach for each other and are dragged in,
    then a dive into the disc. Tunnel: rushing down the tube of lights, rolling. Sky: bursting out high over the
    world, diving after them as they fall, settling on the meadow where they land."""
    scene = bpy.context.scene
    S, E = beat["start_frame"], beat["end_frame"]
    F = S + FLASH_AT
    T0 = S + DIVE[1]
    cam_in = bpy.data.objects["CAM_cruce"]
    for c in list(cam_in.constraints):
        cam_in.constraints.remove(c)
    cam_in.animation_data_clear()
    cam_in.data.clip_start = 0.01
    centre = ROOM_PORTAL + Vector((0, 0, 1.0))
    normal = Vector((math.sin(rad(ROOM_PORTAL_YAW)), -math.cos(rad(ROOM_PORTAL_YAW)), 0))
    start, look0 = Vector((1.6, -4.6, 1.35)), Vector((0.9, -0.4, 0.8))
    hold = Vector((1.5, -3.8, 1.25))
    d0 = S + DIVE[0]
    for f in range(S, T0 + 1):
        if f <= d0:
            t = wp.smooth((f - S) / (d0 - S))
            loc, tgt = start.lerp(hold, t), look0.lerp(centre, 0.45 * t)
        else:
            t = ((f - d0) / (T0 - d0)) ** 2
            loc = hold.lerp(centre + normal * 0.15, t)
            tgt = look0.lerp(centre, 0.45).lerp(centre, min(1.0, t * 2))
        _key_cam(cam_in, f, loc, tgt)
    cam_t = _new_cam("CAM_cruce_tunel", 22)
    for f in range(T0, F + 1):
        t = (f - T0) / (F - T0)
        loc = TUNNEL_AT + Vector((0.3 * math.sin(t * 5), TUNNEL_LEN * t ** 1.3, 0.2 * math.cos(t * 4)))
        _key_cam(cam_t, f, loc, loc + Vector((0, 10, 0)), roll=rad(70 * t))
    cam_s = _new_cam("CAM_cruce_mundo", 24)
    sky0, sky_look0 = _w((-1.5, -21.0, 27.0)), _w((1.0, -4.0, 6.0))
    hold, look_hold = _w((-0.8, -4.6, 1.35)), _w((1.7, 2.6, 0.7))
    land_at = F + 60
    for f in range(F, E + 1):
        if f <= land_at:
            t = wp.smooth((f - F) / (land_at - F))
            loc, tgt = sky0.lerp(hold, t), sky_look0.lerp(look_hold, t)
        else:
            u = (f - land_at) / max(1, E - land_at)
            loc, tgt = hold + Vector((0, -0.3 * u, 0.15 * u)), look_hold
        _key_cam(cam_s, f, loc, tgt)
    # First: close on the two hands reaching for each other over the desk, then the room camera takes over.
    cam_h = _new_cam("CAM_cruce_manos", 45)
    cam_h.data.dof.use_dof, cam_h.data.dof.aperture_fstop = True, 2.0
    hands = Vector((0.14, 0.76, 0.98))  # between his hand and Claude's little arm, Claude in the frame
    eye = Vector((-0.55, 0.0, 1.38))  # side-on to the line between them, over the laptop's lid
    cam_h.data.dof.focus_distance = (hands - eye).length
    for f in range(S, S + HANDS + 1):
        u = (f - S) / HANDS
        _key_cam(cam_h, f, eye + (hands - eye) * 0.12 * u, hands)
    for m in scene.timeline_markers:
        if m.frame == S:
            m.camera = cam_h
    m = scene.timeline_markers.new("cruce_sala", frame=S + HANDS)
    m.camera = cam_in
    for name, cam, frame in (("cruce_tunel", cam_t, T0), ("cruce_mundo", cam_s, F)):
        m = scene.timeline_markers.new(name, frame=frame)
        m.camera = cam
    # White flashes over the cuts: into the disc, out of the tunnel into the sky.
    _flash(cam_in, [(T0 - 6, 0.0), (T0, 1.0)])
    _flash(cam_t, [(T0, 1.0), (T0 + 5, 0.0), (F - 5, 0.0), (F, 1.0)])
    _flash(cam_s, [(F, 1.0), (F + 12, 0.0)])


def _new_cam(name: str, lens: float):
    cam = wp.camera(name, (0, 0, 0), (0, 1, 0), lens)
    cam.data.sensor_fit, cam.data.sensor_height = "VERTICAL", 36
    cam.data.clip_end = 1500
    return cam


def _key_cam(cam, f: int, loc: Vector, tgt: Vector, roll: float = 0.0) -> None:
    cam.location = loc
    q = (tgt - loc).to_track_quat("-Z", "Y")
    if roll:
        from mathutils import Quaternion

        q = q @ Quaternion((0, 0, 1), roll)
    cam.rotation_euler = q.to_euler()
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)


def _flash(cam, frames) -> None:
    """A white card right in front of the lens, its opacity keyed."""
    card = wp.primitive("plane", f"flash_{cam.name}", (0, 0, -0.05), (0.2, 0.2, 1), cam, None)
    mat = bpy.data.materials.new(f"flash_{cam.name}")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 0.97, 0.9, 1)
    em.inputs["Strength"].default_value = 3.0
    tr = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(tr.outputs[0], mix.inputs[1])
    links.new(em.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    mat.surface_render_method = "BLENDED"
    card.data.materials.append(mat)
    _key(mix.inputs["Fac"], frames)


def _billboards(timeline: dict) -> None:
    """Bubbles copy the billboard's rotation: point it like the active camera at every cut."""
    bb = bpy.data.objects.get(wp.BILLBOARD)
    if not bb:
        return
    scene = bpy.context.scene
    markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
    for m in markers:
        cam = m.camera
        if cam is None:
            continue
        scene.frame_set(m.frame + 1)
        bb.rotation_euler = cam.matrix_world.to_euler()
        bb.keyframe_insert("rotation_euler", frame=m.frame)
    _const(bb, "rotation_euler")
    scene.frame_set(0)


def _dusk_lights(timeline: dict) -> None:
    """The people's lights (and their AIs and bubbles) come on one after another as the evening falls."""
    if _direct(timeline):
        return  # the evening fell in part 1: they are all on already
    d0, d1 = _dusk_span(timeline)
    rng = random.Random(11)
    world_root = bpy.data.objects.get("MUNDO")
    for o in bpy.data.objects:
        # Lights, their AIs (copies of the templates) and bubble holders hang straight off the world root.
        if o.parent != world_root or not o.name.startswith(("person_light", "bubble", "ai_tpl_")):
            continue
        s = o.scale.copy()
        on = rng.randint(d0 + (d1 - d0) // 4, d1)
        for f, k in ((0, 0.0), (on - 1, 0.0), (on + 8, 1.0)):
            o.scale = s * max(k, 0.0001)
            o.keyframe_insert("scale", frame=f)
        o.scale = s


def _lonely_goes_out(timeline: dict) -> None:
    """It flickers while Claude says it goes out, nearly dies, then holds on, weak."""
    mat = bpy.data.materials.get("lonely_light")
    glow = bpy.data.objects.get("lonely_glow")
    beat = next((b for b in timeline["beats"] if b.get("line") == "Y deja de preguntar."), None)
    if not (mat and beat):
        return
    sock = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    f0, f1 = beat["start_frame"], beat["end_frame"] + 20
    rng = random.Random(4)
    keys = [(0, 1.8), (f0, 1.8)]
    f = f0
    while f < f1:
        f += rng.randint(3, 9)
        keys.append((f, rng.choice([0.15, 0.4, 1.2, 0.05])))
    keys.append((f1 + 6, 0.6))
    _key(sock, keys)
    if glow:
        _key_prop(glow.data, "energy", [(k, 8 * v / 1.8) for k, v in keys])


# --- part 2 (tres-tokens): it starts in the world at night, and goes into the girl's room ---------------------------
# No crossing: they are already on the meadow, facing the lonely islet, the people's lights on. Claude flies over to
# the islet with the lead's last three tokens; the camera goes into the light (the lead's gaze) and comes out in her room.

ISLE_SPOT = Vector((-0.55, -0.25, 0.0))  # where Claude lands, relative to wp.LONELY (left of her jar, seen from -Y)
ISLE_YAW = 20.0  # turned a little towards her jar
TOKENS = 1.0  # s: the three little lights travel from the lead to Claude
FLIGHT = (1.0, 2.5)  # s into the beat: Claude's arc over to the islet


def _direct(timeline: dict) -> bool:
    return _first(timeline, "cruce") is None


def _face_yaw(c: str) -> float:
    to = wp.LONELY - LAND[c]
    return math.degrees(math.atan2(to.x, -to.y)) + (8 if c == "claude" else -6)


def _jar() -> Vector:
    return _w(wp.LONELY + Vector((0.1, 0.1, 0.45)))


def _flight_beat(timeline: dict) -> dict | None:
    """The silent beat right before Claude's first line on the islet: the tokens, then the flight."""
    isle = _first(timeline, "claude_islote")
    if not isle:
        return None
    return next((b for b in timeline["beats"] if b["end_frame"] == isle["start_frame"]), None)


def _place_direct(timeline: dict, roots: dict) -> None:
    """Already in the world from frame 0, facing the islet; Claude flies to the islet in the flight beat."""
    total, fps = timeline["total_frames"], timeline["fps"]
    fb = _flight_beat(timeline)
    for c, root in roots.items():
        if c not in LAND:
            continue
        s0 = root.scale[0]
        land, yaw = _w(LAND[c]), rad(_face_yaw(c))
        if c == "novato":
            for o in root.children_recursive:  # standing on the meadow: legs back (they hide behind the desk)
                if o.name.split(".")[0].startswith("leg_"):
                    o.hide_render = o.hide_viewport = False
        frames = list(range(total))
        locs, rots, scs = [], [], []
        isle = _w(wp.LONELY + ISLE_SPOT)
        f0 = fb["start_frame"] + int(FLIGHT[0] * fps) if (fb and c == "claude") else None
        f1 = fb["start_frame"] + int(FLIGHT[1] * fps) if (fb and c == "claude") else None
        for f in frames:
            loc, rz, sc = land.copy(), yaw, (s0, s0, s0)
            if f0 is not None and f >= f0:
                u = min(1.0, (f - f0) / max(1, f1 - f0))
                e = wp.smooth(u)
                loc = land.lerp(isle, e)
                loc.z += 1.4 * 4 * e * (1 - e)  # an arc through the air
                rz = yaw + (rad(ISLE_YAW) - yaw) * e
                # Stretch in the air, a squash as it lands.
                land_f = f - f1
                sq = 0.12 * math.sin(math.pi * land_f / 6) if 0 <= land_f < 6 else 0.0
                st = 0.08 * math.sin(math.pi * u) if u < 1 else 0.0
                sc = (s0 * (1 + sq - st / 2), s0 * (1 + sq - st / 2), s0 * (1 - sq + st))
            locs.append(loc)
            rots.append((0.0, 0.0, rz))
            scs.append(sc)
        for i in range(3):
            bake(root, "location", i, frames, [v[i] for v in locs])
            bake(root, "rotation_euler", i, frames, [v[i] for v in rots])
            bake(root, "scale", i, frames, [v[i] for v in scs])
    # Where people look (animate.py reads these by name in beat.gaze).
    timeline["_gaze_points"] = {"_light": _jar()}


def _tokens(timeline: dict, roots: dict) -> None:
    """Three little lights leave the lead's chest one after another and fly into Claude."""
    fb = _flight_beat(timeline)
    if not (fb and "novato" in roots and "claude" in roots):
        return
    fps = timeline["fps"]
    src = _w(LAND["novato"] + Vector((0, 0, 1.15)))
    dst = _w(LAND["claude"] + Vector((0, 0, 0.35)))
    mat = material("token_light", "#ffe2a8", 0.3, emission=14.0)
    for i in range(3):
        a = fb["start_frame"] + int((0.08 + 0.18 * i) * fps)
        b = a + int(0.55 * fps)
        dot = props.point_light(f"token_glow_{i}", tuple(src), "#ffd28a", 0.0, 0.02)
        orb = bpy.data.objects.new(f"token_{i}", None)
        bpy.context.scene.collection.objects.link(orb)
        from lib import primitive

        ball = primitive("uv_sphere", f"token_ball_{i}", (0, 0, 0), (0.035, 0.035, 0.035), orb, mat, segments=10, ring_count=6)
        dot.parent = orb
        dot.location = (0, 0, 0)
        for f in range(a - 1, b + 2):
            u = min(1.0, max(0.0, (f - a) / (b - a)))
            e = wp.smooth(u)
            p = src.lerp(dst, e) + Vector((0, 0, 0.35 * 4 * e * (1 - e)))
            orb.location = p
            orb.keyframe_insert("location", frame=f)
            vis = 1.0 if a <= f < b else 0.0
            ball.scale = (0.035 * vis,) * 3
            ball.keyframe_insert("scale", frame=f)
            dot.data.energy = 2.5 * vis
            dot.data.keyframe_insert("energy", frame=f)


def _lonely_part2(timeline: dict) -> None:
    """Weak and flickering while she waits; it nearly dies on her sad line; after "Sigo aquí" it glows warm and strong,
    and at the end it leans a little towards the lead."""
    mat = bpy.data.materials.get("lonely_light")
    glow = bpy.data.objects.get("lonely_glow")
    isle = _first(timeline, "claude_islote")
    if not (mat and isle):
        return
    sock = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    rng = random.Random(9)
    keys = [(0, 1.0)]
    f, lit = 0, isle["start_frame"] + 8
    sad = next((b for b in timeline["beats"] if b.get("line") == "Solo quería hablar con alguien."), None)
    while f < lit:
        f += rng.randint(4, 11)
        low = 0.25 if sad and sad["start_frame"] <= f < sad["end_frame"] + 30 else 0.6
        keys.append((min(f, lit), rng.choice([low, low + 0.3, 1.0, low])))
    keys += [(lit + 12, 4.5), (timeline["total_frames"], 4.5)]
    _key(sock, keys)
    if glow:
        _key_prop(glow.data, "energy", [(k, 8 * v / 1.8) for k, v in keys])
    jar = bpy.data.objects.get("lonely_jar")
    last = timeline["beats"][-1]
    lean_at = next((b for b in timeline["beats"] if b["camera"] == "humano_asomado"), last)["start_frame"]
    if jar:
        to = (_w(LAND["novato"]) - jar.matrix_world.translation).normalized()
        tilt = rad(9)
        _key_prop(jar, "rotation_euler", [(0, 0.0), (lean_at, 0.0), (lean_at + 25, -to.y * tilt)], index=0)
        _key_prop(jar, "rotation_euler", [(0, 0.0), (lean_at, 0.0), (lean_at + 25, to.x * tilt)], index=1)


def _away_sign(timeline: dict, roots: dict) -> None:
    """Over Claude, as it switches off: a small system notice card (the usage limit), not a chat bubble.
    Dark card, two clean lines, always facing the camera; it pops in just before the light goes out."""
    root = roots.get("claude")
    off = next((b for b in timeline["beats"] if b.get("ai_power") == "off"), None)
    bb = bpy.data.objects.get(wp.BILLBOARD)
    if not (root and off and bb):
        return
    from lib import primitive

    # Right on top of its lid (so it reads as Claude's own notice), small enough to sit inside the shot.
    at = _w(wp.LONELY + ISLE_SPOT + Vector((0.0, -0.05, 0.5)))
    card = empty("limit_card", tuple(at))
    card.scale = (0.6, 0.6, 0.6)
    con = card.constraints.new("COPY_ROTATION")
    con.target = bb
    lines = (("Límite semanal alcanzado", "#f3f3f7", 0.055), ("Vuelve el jueves a las 9:00", "#b9bdcc", 0.045))
    w = 0.034 * max(len(t) for t, _, _ in lines) * 0.95 + 0.1
    # Flat in the card's XY plane, like the bubbles: the billboard turns +Z towards the camera.
    box = primitive("cube", "limit_card_box", (0, 0, 0), (w / 2, 0.085, 0.008), card,
                    material("limit_card_bg", "#1d1e26", 0.6, emission=0.6))
    box.modifiers.new("bevel", "BEVEL").width = 0.03
    box.modifiers["bevel"].segments = 3
    for i, (text, col, size) in enumerate(lines):
        cu = bpy.data.curves.new(f"limit_text_{i}", "FONT")
        cu.body = text
        cu.size = size
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.materials.append(material(f"limit_ink_{i}", col, 0.5, emission=2.5))
        t = bpy.data.objects.new(f"limit_text_{i}", cu)
        bpy.context.scene.collection.objects.link(t)
        t.parent = card
        t.location = (0, 0.028 - i * 0.058, 0.012)
    s = card.scale.copy()
    f0 = off["start_frame"] + int(off.get("ai_power_at", 0.0) * timeline["fps"]) - 10
    for f, k in ((0, 0.0), (f0, 0.0), (f0 + 5, 1.1), (f0 + 9, 1.0)):
        card.scale = s * max(k, 0.0001)
        card.keyframe_insert("scale", frame=f)


def _matchmaker(timeline: dict, roots: dict) -> None:
    """Last beat, before it goes off: Claude looks at the lead (up on the meadow)… at her light… back at the lead."""
    root = roots.get("claude")
    off = next((b for b in timeline["beats"] if b.get("ai_power") == "off"), None)
    head = find(root, "ctrl_head") if root else None
    if not (head and off):
        return
    fps = timeline["fps"]
    s = off["start_frame"]
    to_hero, to_jar = rad(-38), rad(28)  # head yaw from its islet facing
    keys = [(0, 0.0), (s, 0.0), (s + int(0.15 * fps), to_hero), (s + int(0.55 * fps), to_hero),
            (s + int(0.7 * fps), to_jar), (s + int(1.0 * fps), to_jar), (s + int(1.15 * fps), to_hero),
            (s + int(1.5 * fps), to_hero), (s + int(1.9 * fps), 0.0)]
    for f, v in keys:
        head.delta_rotation_euler = (0, 0, v)
        head.keyframe_insert("delta_rotation_euler", index=2, frame=f)


def _room_darkness(timeline: dict) -> None:
    """In her room the world's dusk sky and sun must not light anything: fade the world to black there."""
    shots = [b for b in timeline["beats"] if b["camera"].startswith("cuarto_chica")]
    if not shots:
        return
    tree = bpy.context.scene.world.node_tree
    nodes, links = tree.nodes, tree.links
    out = next(n for n in nodes if n.bl_idname == "ShaderNodeOutputWorld")
    src = out.inputs["Surface"].links[0].from_socket
    black = nodes.new("ShaderNodeBackground")
    black.inputs["Color"].default_value = (0.004, 0.004, 0.008, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "room_dark"
    links.new(src, mix.inputs[1])
    links.new(black.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    # Only while the camera is in her room (it can be there more than once: a flash-forward, then the visit).
    spans = []
    for sh in shots:
        if spans and sh["start_frame"] == spans[-1][1]:
            spans[-1][1] = sh["end_frame"]
        else:
            spans.append([sh["start_frame"], sh["end_frame"]])
    keys = [(0, 0.0)]
    for a, z in spans:
        keys += [(max(0, a - 1), 0.0), (a, 1.0), (z - 1, 1.0), (z, 0.0)]
    _key(mix.inputs["Fac"], sorted(set(keys)))
    _const(tree, 'nodes["room_dark"].inputs[0].default_value')
    sun = bpy.data.objects.get("sun")
    if sun:
        e = sun.data.energy
        _key_prop(sun.data, "energy", sorted(set([(0, e)] + [(f, e * (1 - v)) for f, v in keys])))
        _const(sun.data, "energy")


def _arms_down(timeline: dict, roots: dict) -> None:
    """On the meadow there is no desk: his arms hang relaxed (the desk rig would reach for a keyboard in the air)."""
    root = roots.get("novato")
    if not root:
        return
    from mathutils import Quaternion

    frames = list(range(timeline["total_frames"]))
    for side, sx in (("L", 1), ("R", -1)):
        up, fore = find(root, f"ctrl_arm_{side}"), find(root, f"ctrl_forearm_{side}")
        for obj, q in ((up, Quaternion((0, 1, 0), rad(sx * 7)) @ Quaternion((1, 0, 0), rad(4))),
                       (fore, Quaternion((1, 0, 0), rad(-12)))):
            if obj is None:
                continue
            obj.rotation_mode = "QUATERNION"
            for c in range(4):
                bake(obj, "rotation_quaternion", c, frames, [q[c]] * len(frames))


def _face_keys(timeline: dict, roots: dict) -> None:
    """Against the dusk sky their faces went dark: a warm soft key from the islet side (her light), a cool fill."""
    to = (wp.LONELY - LAND["novato"]).normalized()
    for c, energy in (("novato", 60.0), ("claude", 30.0)):
        if c not in roots:
            continue
        head = _w(LAND[c] + Vector((0, 0, 1.45 if c == "novato" else 0.35)))
        props.area_light(f"key_{c}", tuple(head + to * 1.6 + Vector((0, -0.6, 0.5))), tuple(head), "#ffcf9a", energy, 1.2)
        props.area_light(f"fill_{c}", tuple(head + Vector((-1.2, -1.0, 0.3))), tuple(head), "#9fb8ff", energy * 0.35, 1.5)


def _clear_lenses(timeline: dict, roots: dict) -> None:
    """Floating bits of the world that sit right in front of a close-up lens (a big blurred hexagon) go away."""
    keep = {o for r in roots.values() for o in [r, *r.children_recursive]}
    # Only the face close-ups: the other shots go to things on purpose (the dive ends right at her jar).
    cams = [o for o in bpy.data.objects if o.type == "CAMERA"
            and o.name in ("CAM_mundo_closeup_ai", "CAM_mundo_closeup_novato", "CAM_humano_asomado")]
    scene = bpy.context.scene
    # Cameras move (dolly): check where each one is over the episode, against each object's bounding box.
    spots = []
    for f in range(0, timeline["total_frames"], 10):
        scene.frame_set(f)
        spots += [c.matrix_world.translation.copy() for c in cams]
    scene.frame_set(0)
    for o in bpy.data.objects:
        if o.type != "MESH" or o in keep or o.hide_render or o.name.startswith(("chica_", "CUARTO")):
            continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        if (hi - lo).length > 3.0:  # only small floating bits: never the meadow they stand on, rocks, the sky
            continue
        for c in spots:
            q = Vector((min(max(c.x, lo.x), hi.x), min(max(c.y, lo.y), hi.y), min(max(c.z, lo.z), hi.z)))
            if (q - c).length < 0.9:
                o.hide_render = True
                break
