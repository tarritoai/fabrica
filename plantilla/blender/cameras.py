"""Camera presets. Each beat activates one preset with a slow dolly-in and subtle handheld."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from lib import bake, empty, link

DOLLY = 0.03  # fraction of the subject distance covered per beat
DOLLY_COMEDY = 0.05  # comedy pushes in harder: the frame is always going somewhere
DOLLY_SILENCE = 0.07  # silent reaction shots creep in on the face (the moment sinks in)
PUNCH = 0.09  # impact shots (a jolt, panic, a shouted line) open with a quick push-in
PUNCH_FRAMES = 5


def _camera(name: str, lens: float, fstop: float | None, focus=None, clip: float = 0.02) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_fit = "VERTICAL"
    data.sensor_height = 36
    data.clip_start = clip
    if fstop:
        data.dof.use_dof = True
        data.dof.aperture_fstop = fstop
        data.dof.focus_object = focus
    return link(bpy.data.objects.new(name, data))


def _facing(offset: Vector, yaw_deg: float, follow: float = 0.75) -> Vector:
    """Rotate a camera offset (authored for a character facing -Y) towards where it faces."""
    a = math.radians(yaw_deg * follow)
    x, y, z = offset
    return Vector((x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z))


def presets(heads: dict[str, Vector], ais: list[str], phone_root, yaws: dict | None = None, scales: dict | None = None,
            screen: tuple[Vector, Vector] | None = None, ai_visits_laptop: bool = False,
            ai_front_head: Vector | None = None) -> dict[str, dict]:
    """Framing for each camera: location, target, lens, fstop, follow (head key or None).

    There is one closeup camera per AI ("closeup_claude", …); the script's "closeup_ai"
    resolves per beat to the AI that is speaking.
    """
    yaws, scales = yaws or {}, scales or {}
    if "novato" not in heads:  # a generic set with only things: frame them
        lone = next(iter(heads.values()))
        heads = {**heads, "novato": lone}
    nov = heads["novato"]
    ai_heads = [heads[a] for a in ais] or [nov + Vector((1.7, 0.15, -0.6))]
    ai_mid = sum(ai_heads, Vector()) / len(ai_heads)
    mid = (nov + ai_mid) / 2
    out = {
        "two_shot": dict(loc=mid + Vector((0.15, -2.3, -0.05)), target=mid + Vector((0, 0, -0.2)), lens=30, fstop=4.0),
        "medium_novato_low": dict(loc=nov + _facing(Vector((-0.3, -1.6, -0.45)), yaws.get("novato", 0)), target=nov + Vector((0, 0, -0.2)), lens=32, fstop=2.8, follow="novato"),
        "closeup_novato": dict(loc=nov + _facing(Vector((-0.4, -1.2, -0.18)), yaws.get("novato", 0)), target=nov + Vector((-0.2, 0, -0.2)), lens=40, fstop=2.0, follow="novato"),
    }
    # Space shots (floating-island set): arrive from the galaxy into the two-shot; see the island alone.
    room = mid + Vector((0, 0.1, -0.55))
    two = out["two_shot"]
    out["establishing"] = dict(loc=two["loc"], start=mid + Vector((3.2, -8.5, 2.6)), target=two["target"], lens=30, fstop=None)
    # The whole room from the front (the copies of the AI on the desk, the bookcase and the floor).
    out["wide_room"] = dict(loc=room + Vector((0.45, -3.2, 1.2)), target=room + Vector((0.4, 0.3, -0.1)), lens=24, fstop=None)
    out["wide_space"] = dict(loc=room + Vector((-2.6, -7.4, 0.15)), end=room + Vector((-3.4, -10.2, 0.05)), target=room + Vector((0, 0, -0.35)), lens=32, fstop=None)
    for a in ais:
        h, k = heads[a], scales.get(a, 1.0)
        out[f"closeup_{a}"] = dict(loc=h + _facing(Vector((-0.2, -1.75, 0.0)) * max(k, 0.6), yaws.get(a, 0)), target=h + Vector((0, 0, -0.12 * k)), lens=55, fstop=2.0, follow=a)
    # The giant robot of the future (blender/future.py): looking up at it from behind the novato,
    # and its own point of view down onto the tiny room.
    from future import ROBOT_HEAD

    out["robot_reveal"] = dict(loc=nov + Vector((-0.2, 0.62, 0.32)), target=ROBOT_HEAD + Vector((0, 0, -2.6)), lens=18, fstop=None)
    # The last shot: far and to the side, the island and the giant together (it sinks as the dawn rises).
    out["wide_epic"] = dict(loc=Vector((15.0, -12.0, 6.0)), end=Vector((17.0, -14.5, 6.6)), target=Vector((-0.6, -2.6, 2.2)), lens=30, fstop=None)
    out["robot_pov"] = dict(loc=ROBOT_HEAD + Vector((1.0, 2.8, 0.4)), target=mid + Vector((0, 0.05, -0.35)), lens=38, fstop=None)
    # The standoff: low behind the AI once it stands in front of the novato, looking up at the giant.
    if ais and ai_front_head is not None:
        front = ai_front_head  # where its head is once it stands in front of the novato
        out["standoff"] = dict(loc=front + Vector((0.12, 1.05, 0.15)), target=ROBOT_HEAD + Vector((0, 0, -2.6)), lens=20, fstop=None)
    # Other humans (the flatmate on the sofa): a close-up and a medium shot each, framed from where they face.
    for c, h in heads.items():
        if c == "novato" or c in ais:
            continue
        y = yaws.get(c, 0)
        # From their own side, away from the desk (the lamp would block a line towards the novato).
        out[f"closeup_{c}"] = dict(loc=h + _facing(Vector((0.3, -1.25, -0.12)), y, 1.0), target=h + Vector((0.05, 0, -0.18)), lens=40, fstop=2.0, follow=c)
        out[f"medium_{c}"] = dict(loc=h + _facing(Vector((-0.3, -2.5, -0.3)), y, 1.0), target=h + Vector((0.15, 0, -0.45)), lens=30, fstop=2.8, follow=c)
    if screen is not None:
        center, normal = screen
        # His point of view on the laptop: the screen fills the width of the vertical frame.
        # The camera sits where his eyes are: clip_start cuts his own head out of the shot.
        # Slightly to the side the AI stands on, so its hands on the keyboard read too.
        side = Vector((0.07, 0, 0)) if ai_visits_laptop else Vector()
        out["screen_closeup"] = dict(loc=center + normal * 0.6 + Vector((0, 0, 0.1)) + side, target=center + Vector((0, 0, -0.05)) + side,
                                     lens=30, fstop=2.8, clip=0.3)
        # Behind his shoulder: the back of his head, the lit screen and the AI beside it, the galaxy beyond.
        ai_h = ai_heads[0]
        out["over_shoulder"] = dict(loc=nov + Vector((0.42, 0.85, 0.42)), target=center.lerp(ai_h, 0.3) + Vector((0, 0, -0.03)),
                                    lens=42, fstop=2.8, focus_at=center)
    if phone_root is not None:
        # phone_root is the over-the-shoulder pose itself; the focus sits on the phone.
        out["phone_closeup"] = dict(local=True, parent=phone_root, loc=Vector((0.0, 0.0, 0.0)), target=Vector((0, 0, -1.0)), lens=45, fstop=3.2)
        # Square on to the phone's glass (child of the phone itself: follows the hand), the screen fills the frame.
        phone = bpy.data.objects.get("PHONE")
        if phone is not None:
            out["phone_screen"] = dict(local=True, parent=phone, loc=Vector((0.0, 0.03, 0.105)), target=Vector((0, 0.03, 0.0)),
                                       lens=24, fstop=8.0, clip=0.1)
    return out


def resolve(beat: dict, ais: list[str], cams: dict) -> str:
    name = beat["camera"]
    if name == "closeup_ai" and ais:
        who = beat["speaker"] or beat.get("reactor")
        name = f"closeup_{who}" if who in ais else f"closeup_{ais[0]}"
    if name in ("closeup_other", "medium_other"):
        kind = name.split("_")[0]
        others = sorted({k.split("_", 1)[1] for k in cams if k.startswith("closeup_")} - set(ais) - {"novato", "ai"})
        who = beat["speaker"] or beat.get("reactor")
        if others:
            name = f"{kind}_{who if who in others else others[0]}"
    return name if name in cams else "two_shot"


def setup(timeline: dict, heads: dict[str, Vector], ais: list[str], phone_root, head_ctrls: dict,
          yaws: dict | None = None, scales: dict | None = None, screen: tuple[Vector, Vector] | None = None,
          ai_path: dict | None = None, ai_front_head: Vector | None = None, extra: dict | None = None) -> None:
    scene = bpy.context.scene
    fps, total = timeline["fps"], timeline["total_frames"]
    specs = presets(heads, ais, phone_root, yaws, scales, screen, bool(timeline.get("ai_visits_laptop")), ai_front_head)
    specs.update(extra or {})  # set-specific framings (e.g. the miniseries world)
    cams = {}
    for name, spec in specs.items():
        follow = head_ctrls.get(spec.get("follow"))
        if spec.get("local"):
            focus = empty(f"focus_{name}", tuple(spec["target"]), spec["parent"])
        elif follow is not None:
            # Child of the head control: framing follows leans, slumps and nods.
            focus = empty(f"focus_{name}", tuple(follow.matrix_world.inverted() @ Vector(spec["target"])), follow)
        else:
            focus = empty(f"focus_{name}", tuple(spec["target"]))
        if spec.get("focus_at") is not None:
            # Aim at the target but focus somewhere else (e.g. the screen in an over-the-shoulder).
            aim, focus = focus, empty(f"dof_{name}", tuple(spec["focus_at"]))
        else:
            aim = focus
        cam = _camera(f"CAM_{name}", spec["lens"], spec["fstop"], focus, spec.get("clip", 0.02))
        if spec.get("local"):
            # Looks straight down local -Z at the screen, up = local +Y (no constraint: avoids a degenerate roll).
            cam.parent = spec["parent"]
        else:
            track = cam.constraints.new("TRACK_TO")
            track.target = aim
            track.track_axis = "TRACK_NEGATIVE_Z"
            track.up_axis = "UP_Y"
        cams[name] = (cam, spec)

    # Consecutive beats on the same camera are ONE continuous shot: the dolly keeps going
    # instead of snapping back at every line (that snap reads as a jump cut).
    # A beat with cut_camera is two shots: its own camera until cut_at, then the second one.
    segments = []
    for b in timeline["beats"]:
        if b.get("cut_camera") and b.get("cut_at") is not None:
            cut = min(b["end_frame"] - 1, b["start_frame"] + round(b["cut_at"] * fps))
            segments += [(b, b["start_frame"], cut), ({**b, "camera": b["cut_camera"]}, cut, b["end_frame"])]
        else:
            segments.append((b, b["start_frame"], b["end_frame"]))
    shots: list[dict] = []
    for b, start, end in segments:
        name = resolve(b, ais, cams)
        if shots and shots[-1]["camera"] == name:
            shots[-1]["end"] = end
        else:
            shots.append({"camera": name, "start": start, "end": end, "beat": b["id"], "first": b, "n": len(shots)})

    # Baked per-frame motion: dolly-in across each shot + gentle handheld.
    tracks = {name: {"f": [], "loc": [], "rot": []} for name in cams}
    for shot in shots:
        name = shot["camera"]
        cam, spec = cams[name]
        length = max(1, shot["end"] - shot["start"])
        loc0, target = Vector(spec["loc"]), Vector(spec["target"])
        # Same total push for long and short shots, capped so long holds don't crawl into the face.
        first = shot["first"]
        rate = DOLLY_SILENCE if first["speaker"] is None else DOLLY_COMEDY if timeline.get("tone") == "comedia" else DOLLY
        push = rate * min(2.0, length / (2.5 * fps))
        delivery = first.get("delivery") or {}
        impact = (first["action"] == "recoil" or first["emotion"] in ("alarma", "panico")
                  or delivery.get("intensity") == "alta") and not spec.get("local") and spec.get("start") is None
        for f in range(shot["start"], shot["end"]):
            k = (f - shot["start"]) / length
            if spec.get("start") is not None:  # fly-in that lands exactly on the framing
                e = k * k * k * (k * (6 * k - 15) + 10)  # smootherstep
                loc = Vector(spec["start"]).lerp(loc0, e)
            elif spec.get("end") is not None:  # slow drift away
                loc = loc0.lerp(Vector(spec["end"]), k)
            else:
                punch = PUNCH * (1 - math.exp(-(f - shot["start"]) / (PUNCH_FRAMES / 2))) if impact else 0.0
                loc = loc0.lerp(target, push * k + punch)
            if ai_path is not None and spec.get("follow") in ais:
                # The AI moves on the desk: its close-up travels (and turns) with it, no hops.
                h0 = Vector(spec["target"])
                turn = math.radians(ai_path["yaw"][f] - ai_path["home_yaw"]) * 0.75
                off = loc - h0
                off = Vector((off.x * math.cos(turn) - off.y * math.sin(turn), off.x * math.sin(turn) + off.y * math.cos(turn), off.z))
                d = ai_path["loc"][f] - ai_path["home"]
                loc = h0 + off + Vector((d.x, d.y, 0))
            elif ai_path is not None and spec.get("follow") == "novato" and ai_path.get("front") is not None \
                    and (ai_path["loc"][f] - ai_path["front"]).length < 0.05:
                # The AI stands right in front of him: look over its lid, not through it.
                loc = loc + Vector((0, 0, 0.24))
            t = f / fps
            shake = Vector((0.004 * math.sin(t * 1.3), 0, 0.003 * math.sin(t * 1.7 + 1)))
            if spec.get("local"):
                shake = Vector((0.002 * math.sin(t * 1.3), 0.002 * math.sin(t * 1.7 + 1), 0))
            tr = tracks[name]
            tr["f"].append(f)
            tr["loc"].append(loc + shake)
            tr["rot"].append((0.0, 0.0, 0.0))
        marker = scene.timeline_markers.new(f"shot_{shot['beat']}_{shot['n']}", frame=shot["start"])
        marker.camera = cam

    for name, (cam, spec) in cams.items():
        tr = tracks[name]
        if not tr["f"]:
            cam.location = spec["loc"]
            continue
        for i in range(3):
            bake(cam, "location", i, tr["f"], [v[i] for v in tr["loc"]])
    scene.camera = cams[resolve(timeline["beats"][0], ais, cams)][0]
