"""timeline.json -> scene.blend. Run: blender -b -P blender/build_scene.py -- <timeline.json> <out.blend>"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import cameras  # noqa: E402
from lib import ROOT, character_meta, empty, link, load_json, material, primitive, rad, bake  # noqa: E402
from rigs import animate, placeholders  # noqa: E402
from sets import SETS  # noqa: E402

PHONE_COMPONENTS = {"PhoneNotifications", "PhoneCall", "PhoneChat"}  # mirrors reels/schema.py (screen_movies filters by owner)
LAPTOP_COMPONENTS = {"MemorySave", "DateGlitch", "SystemNotice", "LaptopChat", "StreamProfiles", "LoginScreen"}
FACING = {"left": 18, "right": -18, "right_a": -12, "right_b": -26}  # yaw so characters half-face each other


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_character(char_id: str) -> bpy.types.Object:
    """Append CHAR_<id> from the character's folder (<player>.blend), or build it by code (placeholders.BUILDERS)."""
    from lib import character_dir

    folder = character_dir(char_id)
    blend = folder / f"{folder.name}.blend"
    meta = character_meta(char_id)
    if blend.exists():
        with bpy.data.libraries.load(str(blend)) as (src, dst):
            dst.objects = [n for n in src.objects]
        for obj in dst.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
        root = bpy.data.objects.get(f"CHAR_{folder.name}") or bpy.data.objects[f"CHAR_{char_id}"]
        root.name = f"CHAR_{char_id}"  # the slot's name: cameras and sets look it up by slot
        return root
    return placeholders.build(char_id, meta)


def head_world(root) -> Vector:
    from lib import find

    bpy.context.view_layer.update()
    head = find(root, "ctrl_head") or root
    eye = find(root, "eye_L")
    return eye.matrix_world.translation.copy() if eye else head.matrix_world.translation.copy()


def screen_movies(timeline: dict, episode_dir: Path, components: set, parent, loc, scale, rotation=(0, 0, 0),
                  step=(0, 0, 0.0005), strength: float = 1.4, owner: str = "novato", visible: list[float] | None = None) -> None:
    """One emissive plane per screen-event beat, stacked in front of the device's glass.

    Each plane is lit from its beat until the next one of the same device (the last one stays on).
    """
    beats = [b for b in timeline["beats"] if b["event"] and b["event"]["component"] in components
             and b["event"]["props"].get("owner", "novato") == owner]
    for n, b in enumerate(beats):
        movie = episode_dir / "screens" / f"beat_{b['id']:02d}_{b['event']['component']}.mp4"
        img = bpy.data.images.load(str(movie))
        img.source = "MOVIE"
        mat = bpy.data.materials.new(f"screen_{b['id']}")
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.image_user.frame_duration = b["end_frame"] - b["start_frame"]
        tex.image_user.frame_start = b["start_frame"]
        tex.image_user.use_auto_refresh = True
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Strength"].default_value = strength
        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(tex.outputs["Color"], emit.inputs["Color"])
        links.new(emit.outputs["Emission"], out.inputs["Surface"])
        offset = tuple(l + d * (n + 1) for l, d in zip(loc, step))
        screen = primitive("plane", f"{parent.name}_screen_{b['id']}", offset, scale, parent, mat)
        screen.rotation_euler = rotation
        nxt = beats[n + 1]["start_frame"] if n + 1 < len(beats) else None
        if visible is not None:
            # Only while its beat is current AND the device is out (a phone that comes and goes).
            end = nxt if nxt is not None else len(visible)
            vals = [0.0 if b["start_frame"] <= f < end and visible[f] > 0.5 else 1.0 for f in range(len(visible))]
            bake(screen, "hide_render", -1, list(range(len(vals))), vals, interp="CONSTANT")
            continue
        frames, values = [0, b["start_frame"]], [1.0, 0.0]
        if nxt is not None:
            frames.append(nxt)
            values.append(1.0)
        bake(screen, "hide_render", -1, frames, values, interp="CONSTANT")


def hide_during(timeline: dict, objs, beats: list[dict]) -> None:
    """Hide these meshes during these beats, keeping any visibility already animated (mouth shapes, tears)."""
    frames = list(range(timeline["total_frames"]))
    mask = [False] * len(frames)
    for b in beats:
        for f in range(b["start_frame"], min(b["end_frame"], len(frames))):
            mask[f] = True
    for obj in objs:
        if obj.type != "MESH":
            continue
        fc = None
        if obj.animation_data and obj.animation_data.action:
            from bpy_extras import anim_utils

            cb = anim_utils.action_get_channelbag_for_slot(obj.animation_data.action, obj.animation_data.action_slot)
            fc = cb.fcurves.find("hide_render") if cb else None
        base = [fc.evaluate(f) if fc else float(obj.hide_render) for f in frames]
        bake(obj, "hide_render", -1, frames, [1.0 if m else v for m, v in zip(mask, base)], interp="CONSTANT")


def build_phone(timeline: dict, episode_dir: Path, anchors: dict):
    """The novato's phone (rigs/arms.py moves it); one screen texture per phone event beat."""
    import props

    phone_root = props.phone()
    phone_root.location = anchors.get("phone_spot", (0, 0, 0))
    screen_movies(timeline, episode_dir, PHONE_COMPONENTS, phone_root, (0, 0, 0), (0.035, 0.073, 1))
    phone_glow(timeline, phone_root)
    return phone_root


def phone_glow(timeline: dict, phone_root) -> None:
    """In a dark room a lit phone is the light: a cold glow off its screen (on the desk it reads from afar; in his
    hands it lights his face from below). From a notification until it goes face down."""
    from lib import link, srgb

    fps, total = timeline["fps"], timeline["total_frames"]
    mood = ["noche"] * total
    for b in timeline["beats"]:
        if b.get("light"):
            for f in range(min(total, b["start_frame"] + round((b.get("light_at") or 0.0) * fps)), total):
                mood[f] = b["light"]
    on = [False] * total
    lit = False
    for b in timeline["beats"]:
        if (b.get("event") or {}).get("component") in PHONE_COMPONENTS:
            lit = True
        if b["action"] == "phone_down":
            for f in range(b["start_frame"], min(total, b["start_frame"] + 12)):  # dims as it turns over
                on[f] = lit
            lit = False
            continue
        for f in range(b["start_frame"], min(total, b["end_frame"])):
            on[f] = lit
    values = [1.0 if o and mood[f] in ("oscuro", "apagon") else 0.0 for f, o in enumerate(on)]
    if not any(values):
        return
    data = bpy.data.lights.new("phone_glow", "POINT")
    data.color = srgb("#9fbcff")[:3]
    data.shadow_soft_size = 0.05
    obj = bpy.data.objects.new("phone_glow", data)
    link(obj, phone_root)
    obj.location = (0, 0, 0.015)  # just off the glass (further out it grazes his chest: a dark blot)
    energy = 4.0
    bake(data, "energy", -1, list(range(total)), [energy * v for v in values], interp="CONSTANT")


def phone_pov(novato_root):
    """Over-the-shoulder view of the phone in its 'look' pose (the phone rises into this shot).

    The empty IS the camera pose: it looks down its local -Z at the phone.
    """
    from rigs import arms
    from lib import find

    body = find(novato_root, "ctrl_body") or novato_root
    phone_loc, _ = arms.phone_poses(Vector())["look"]
    cam = Vector((-0.5, 0.2, 1.85))  # above and behind the right shoulder: clears the head and the arm
    pov = empty("PHONE_POV", tuple(cam), body)
    pov.rotation_mode = "QUATERNION"
    pov.rotation_quaternion = arms._frame(cam - phone_loc, Vector((0, 0, 1)))
    return pov


def render_settings(timeline: dict) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = timeline["width"]
    scene.render.resolution_y = timeline["height"]
    scene.render.fps = timeline["fps"]
    scene.frame_start = 0
    scene.frame_end = timeline["total_frames"] - 1
    scene.eevee.taa_render_samples = 32
    scene.eevee.use_shadows = True
    # Every glowing jar is a shadow-casting light: at full res 512 MB overflows ("Shadow buffer full")
    # and EEVEE silently drops shadows (floating jars, flat props). Previews at half res never show it.
    scene.eevee.shadow_pool_size = "2048"
    scene.view_settings.exposure = 0.3
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [
        i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items
    ] else "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_motion_blur = False
    scene.render.motion_blur_shutter = 0.35


def main(timeline_path: str, out_blend: str) -> None:
    timeline = load_json(timeline_path)
    episode_dir = Path(timeline_path).parent
    from lib import set_cast

    set_cast(timeline.get("cast"))
    reset()
    timeline["_episode_dir"] = str(episode_dir)
    anchors = SETS[timeline["set"]](timeline)
    band = bool(timeline.get("score") and anchors.get("band_spots"))
    if band:
        # A musical episode: the AI's copies are a band in a row on the floor facing the camera, the AI itself
        # leading from the middle (blender/notes.py plays them).
        anchors = {**anchors, "copy_spots": anchors["band_spots"], "copy_target": anchors["band_target"],
                   "slots": {**anchors["slots"], "right": anchors["band_lead"]}, "facing": {**anchors.get("facing", {}), "right": -4}}

    # Off-screen characters (a voice on the phone) have no body in the scene.
    chars = [c for c in timeline["characters"] if not character_meta(c).get("offscreen")]

    def is_human(c: str) -> bool:
        meta = character_meta(c)
        return meta.get("role") == "human" or meta.get("placeholder", {}).get("shape") == "human"

    # Other humans (the flatmate) get their own spots in the set; AIs share the desk.
    extras = [c for c in chars if c != "novato" and is_human(c)]
    ais = [c for c in chars if c != "novato" and not is_human(c)]
    ai = ais[0] if ais else None
    roots = {}
    slots = {"novato": "left"}
    if len(ais) == 1:
        slots[ais[0]] = "right"
    else:
        slots.update(zip(ais, ("right_a", "right_b")))
    slots.update(zip(extras, ("sofa",)))
    facing = {**FACING, **anchors.get("facing", {})}
    for c in chars:
        root = load_character(c)
        slot = slots[c]
        root.location = anchors["slots"][slot]
        root.rotation_euler = (0, 0, rad(facing[slot]))
        if c in ais and anchors.get("ai_scale"):
            root.scale = (anchors["ai_scale"],) * 3
        if c in anchors.get("seated", []):
            # Seated behind the desk: the legs would only poke through the chair.
            for obj in root.children_recursive:
                if obj.name.split(".")[0].startswith("leg_"):
                    obj.hide_render = obj.hide_viewport = True
        roots[c] = root

    # Copies of the AI (each regenerate click is one more jar): built now so the cameras know where the mini is.
    import copies

    n_copies, want_mini = copies.wanted(timeline) if ai else (0, False)
    copy_roots, mini_root = copies.place(anchors, roots[ai], n_copies, want_mini, load_character) if n_copies or want_mini else ([], None)
    if band:
        roots[ai].scale = tuple(v * 1.18 for v in roots[ai].scale)  # the lead: a size up on the rest of the band

    phone = build_phone(timeline, episode_dir, anchors) if "novato" in roots else None
    lap = anchors.get("laptop")
    if lap:
        # Same placement as the code screen in props.laptop, a hair closer to the viewer.
        # A light chat (LaptopChat theme "tarro") at full strength blows out to plain white in the dark room.
        light_ui = any((b.get("event") or {}).get("props", {}).get("theme") == "tarro" for b in timeline["beats"])
        screen_movies(timeline, episode_dir, LAPTOP_COMPONENTS, lap["lid"], (0, -0.0066, 0.118), (0.158, 0.104, 1),
                      rotation=(rad(90), 0, 0), step=(0, -0.0002, 0), strength=1.2 if light_ui else 2.2)
    pov = phone_pov(roots["novato"]) if phone is not None else None
    from lib import find

    # Cameras first: follow targets are placed relative to the rest pose.
    heads = {c: head_world(r) for c, r in roots.items()}
    head_ctrls = {c: find(r, "ctrl_head") or r for c, r in roots.items()}
    yaws = {c: facing[slots[c]] for c in roots}
    scales = {c: r.scale[0] for c, r in roots.items()}
    screen = None
    if lap:
        bpy.context.view_layer.update()
        mw = lap["screen"].matrix_world
        screen = (mw.translation.copy(), (mw.to_3x3() @ Vector((0, 0, 1))).normalized())
    import staging

    ai_path = None
    if ai and "laptop" in anchors["slots"]:
        ai_path = staging.plan(timeline, anchors["slots"][slots[ai]], facing[slots[ai]], anchors["slots"]["laptop"], facing["laptop"],
                               anchors["slots"].get("front"), facing.get("front", 0.0))
        if ai_path:
            timeline["ai_at_laptop"] = ai_path["at_laptop"]
    front_head = None
    if ai and anchors["slots"].get("front"):
        front_head = Vector(anchors["slots"]["front"]) + (heads[ai] - Vector(anchors["slots"][slots[ai]]))
    # Sets that move the characters around (the miniseries world) animate them here and bring their own cameras.
    extra_cams = anchors["on_characters"](timeline, roots, anchors, heads) if anchors.get("on_characters") else None
    if timeline.get("score") and copy_roots:
        import notes

        extra_cams = {**(extra_cams or {}), **notes.cameras(copy_roots)}
    mini_head = head_world(mini_root) if mini_root is not None else None
    if mini_head is not None:
        extra_cams = {**(extra_cams or {}), **copies.cameras(anchors, mini_head, anchors["mini_spot"][1])}
    if anchors.get("cameras"):  # set-specific framings (generic sets: no galaxy to fly in from, standing humans)
        extra_cams = {**(extra_cams or {}), **anchors["cameras"](heads, ais)}
    bpy.context.scene.frame_set(0)
    cameras.setup(timeline, heads, ais, pov, head_ctrls, yaws, scales, screen, ai_path, front_head, extra_cams)
    # Gaze targets where they are at frame 0 (a set may have moved them since the cameras were placed).
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    heads_now = {c: head_world(r) for c, r in roots.items()}
    if copy_roots or mini_root is not None:
        # Each jar sees whose mouth says each line (chorus: all of them; mini: only the tiny one).
        if mini_head is not None:
            heads_now[copies.MINI] = mini_head
        for c, r in roots.items():
            animate.animate(c, r, copies.voiced(timeline, ai, "main" if c == ai else "other"), heads_now, screen[0] if screen else None)
        jar_heads = {**{c: h for c, h in heads_now.items() if c != ai}, copies.MAIN: heads_now[ai]}
        for i, r in enumerate(copy_roots):
            animate.animate(ai, r, copies.voiced(timeline, ai, "copy"), jar_heads, screen[0] if screen else None, seed_id=f"{ai}_copy{i}")
        if mini_root is not None:
            mini_heads = {c: h for c, h in jar_heads.items() if c != copies.MINI}
            animate.animate(ai, mini_root, copies.voiced(timeline, ai, "mini"), mini_heads, screen[0] if screen else None, seed_id=f"{ai}_mini")
        copies.park(timeline, copy_roots, mini_root)
        copies.glow([roots[ai], *copy_roots, *([mini_root] if mini_root is not None else [])])
    else:
        for c, r in roots.items():
            animate.animate(c, r, timeline, heads_now, screen[0] if screen else None)
    if ai_path:
        staging.bake_root(roots[ai], ai_path)
    # Secondary humans: gaze towards the novato, hand poses and their own phone.
    from rigs import extras as extras_rig
    import props as props_mod

    for c in extras:
        own = props_mod.phone(f"PHONE_{c}")
        vis = extras_rig.animate(roots[c], c, timeline, heads.get("novato"), own)
        screen_movies(timeline, episode_dir, {"PhoneChat"}, own, (0, 0, 0), (0.035, 0.073, 1), owner=c, visible=vis)
    if "novato" in roots:
        from rigs import arms

        lap = anchors.get("laptop")
        standing = bool(anchors.get("standing"))
        if lap:
            keyboard = lap["root"].matrix_world @ Vector((0, -0.01, 0.02))
        elif standing:  # hands on the counter, or down by the sides
            keyboard = Vector(anchors["hands_spot"]) if anchors.get("hands_spot") else None
        else:
            keyboard = head_world(roots["novato"]) + Vector((0, -0.5, -0.6))
        spot = Vector(anchors.get("phone_spot", keyboard if keyboard is not None else (0, 0, 0)))
        arms.animate(roots["novato"], timeline, phone, spot, keyboard, [heads[a] for a in ais], lap["lid"] if lap else None,
                     standing=standing, typing_ok=anchors.get("typing", True))
        if anchors.get("phone_optional") and phone is not None and all(st == "desk" for _, st in arms.phone_states(timeline)):
            for obj in [phone, *phone.children_recursive]:  # nowhere to lay a phone in this set: no phone unless used
                obj.hide_render = obj.hide_viewport = True
        arms.close_lid(timeline, lap["lid"] if lap else None)
        # phone_screen sits a few cm from the glass: the forearm holding the phone passes between them and the
        # near clip slices it into stray wedges. Only the phone belongs in that shot, so the arms leave it.
        fps = timeline["fps"]
        shots = [(b["start_frame"], b["end_frame"]) for b in timeline["beats"] if b["camera"] == "phone_screen"]
        shots += [(b["start_frame"] + round(b["cut_at"] * fps), b["end_frame"]) for b in timeline["beats"]
                  if b.get("cut_camera") == "phone_screen" and b.get("cut_at") is not None]
        if shots:
            frames = list(range(timeline["total_frames"]))
            hidden = [0.0] * len(frames)
            for a, z in shots:
                for f in range(a, min(z, len(frames))):
                    hidden[f] = 1.0
            for side in ("L", "R"):
                arm = find(roots["novato"], f"ctrl_arm_{side}")
                for obj in [arm, *arm.children_recursive] if arm else []:
                    if obj.type == "MESH":
                        bake(obj, "hide_render", -1, frames, hidden, interp="CONSTANT")
        # screen_closeup looks over his head at the laptop: when he slumps or leans in, his head and chest swing
        # into the lens (a giant eye across the screen on the cut). The screen is the shot: only his hands stay.
        pov = [b for b in timeline["beats"] if b["camera"] == "screen_closeup"]
        arm_parts = {o for side in ("L", "R") for a in [find(roots["novato"], f"ctrl_arm_{side}")] if a for o in [a, *a.children_recursive]}
        if pov:
            hide_during(timeline, [o for o in roots["novato"].children_recursive if o not in arm_parts], pov)
        # Gone to the bathroom with the laptop (beat.novato_away): an empty chair, no laptop, no screen glow on the desk.
        away = [b for b in timeline["beats"] if b.get("away")]
        if away:
            gone = list(roots["novato"].children_recursive)
            if lap:
                gone += [lap["root"], *lap["root"].children_recursive]
            hide_during(timeline, gone, away)
    # The AI's cold rim stands right in front of the back wall and grazes it (a hard blue wedge by the window):
    # it only exists to light the AI, so only the AIs (and their copies) receive it.
    rim = bpy.data.objects.get("ai_rim")
    if rim is not None and ais:
        receivers = bpy.data.collections.new("ai_rim_receivers")
        for r in [*(roots[a] for a in ais), *copy_roots, *([mini_root] if mini_root is not None else [])]:
            for obj in [r, *r.children_recursive]:
                if obj.type == "MESH":
                    receivers.objects.link(obj)
        rim.light_linking.receiver_collection = receivers

    import mementos
    import moods

    moods.apply(timeline)
    if timeline.get("score") and ai:
        import notes

        notes.apply(timeline, [roots[ai], *copy_roots], roots.get("novato"))
    slit = None
    if ai:
        bpy.context.view_layer.update()
        think = find(roots[ai], "think_light")
        slit = think.matrix_world.translation.copy() if think else heads[ai]
    if "novato" in heads:
        mementos.build(timeline, heads["novato"], slit)
    import future

    ai_head_at = None
    if ai_path and ai:
        lift = heads[ai] - Vector(anchors["slots"][slots[ai]])
        ai_head_at = lambda f: ai_path["loc"][f] + lift  # noqa: E731
    future.build(timeline, anchors, heads, roots, ai, ai_head_at)
    if anchors.get("after_cameras"):
        anchors["after_cameras"](timeline, roots)
    render_settings(timeline)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print(f"[build_scene] saved {out_blend}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :]
    main(*argv)
