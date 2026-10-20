"""Hands and the phone: where the novato's hands are on every frame, and the phone they carry.

Everything is solved in the novato's body space (ctrl_body), so leans and slumps carry the
hands and the phone along. The phone has three resting poses (desk, look, ear); between them
the hand reaches for the phone first and then both travel together (and the reverse when
putting it down). Arms are two-bone chains solved analytically (shoulder -> elbow -> hand).
"""

from __future__ import annotations

import math

from mathutils import Matrix, Quaternion, Vector

from lib import bake, character_meta, find, smoothstep

PHONE_EVENTS = {"PhoneNotifications", "PhoneCall"}
MOVE = 20  # frames for a phone move (reach + carry)
LID_CLOSE = 12  # frames for the laptop lid to come down
LID_OPEN, LID_SHUT = -15.0, 90.0  # deg on the hinge
LID_LIFT = 0.0078  # m the hinge rises as it shuts, so the closed shell rests on the keys instead of sinking into them
LID_REACH = 8  # frames for the hand to get to the lid's top edge (and to leave it)
TAP_LIFT = 0.035  # m the finger lifts before each regenerate click (it has to read in a close-up, over the lid)
TAP_FRAMES = 4  # frames of lift before a click lands
POSE_BLEND = 8  # frames to blend hand poses between beats
TYPING_EMOTIONS = {"neutral", "orgulloso", "confuso", "juzgando"}


def _frame(z_axis: Vector, up_hint: Vector) -> Quaternion:
    """Orientation whose local +Z is `z_axis` and local +Y points as close as possible to `up_hint`."""
    z = z_axis.normalized()
    y = (up_hint - z * up_hint.dot(z)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_quaternion()


def phone_poses(desk_local: Vector, down_local: Vector | None = None) -> dict[str, tuple[Vector, Quaternion]]:
    eyes = Vector((0.0, -0.17, 1.46))
    look_loc = Vector((-0.08, -0.42, 1.18))
    ear_loc = Vector((-0.28, -0.05, 1.4))
    low_loc = Vector((-0.06, -0.38, 1.05))
    return {
        "desk": (desk_local, _frame(Vector((0, 0, 1)), Vector((0.25, -1, 0)))),
        # Face down, right in front of him (on the shut laptop when there is one, so the close-up sees it land):
        # the glass down, the case up (origin = glass).
        "down": (down_local if down_local is not None else desk_local - Vector((0, 0, 0.016)),
                 _frame(Vector((0, 0, -1)), Vector((0.25, -1, 0)))),
        "look": (look_loc, _frame(eyes - look_loc, Vector((0, 0.3, 1)))),
        "ear": (ear_loc, _frame(Vector((1, 0.05, 0.05)), Vector((0, -0.25, 1)))),
        # Lowered to the belly, still in hand and lit, the glass tilted up at him: the face is free again.
        "low": (low_loc, _frame(eyes - low_loc, Vector((0, 0.3, 1)))),
    }


def _novato_acts(b: dict, off: set) -> bool:
    speaker = b["speaker"]
    return speaker == "novato" or (speaker is None and (b.get("reactor") or "novato") == "novato") or speaker in off


def lid_span(timeline: dict) -> tuple[int, int] | None:
    """(start, shut) frames of the novato closing the laptop (`action: close_laptop`): the lid lands when the light
    changes (`light_at`), or as his line ends."""
    fps = timeline["fps"]
    for b in timeline["beats"]:
        if b["action"] == "close_laptop" and _novato_acts(b, set(timeline.get("offscreen", []))):
            if b.get("light_at") is not None:
                shut = b["start_frame"] + round(b["light_at"] * fps)
            else:
                shut = b["end_frame"] - round((b.get("hold") or 0.0) * fps)
            shut = max(b["start_frame"] + LID_CLOSE, min(shut, b["end_frame"]))
            return shut - LID_CLOSE, shut
    return None


def lid_angle(span: tuple[int, int] | None, f: int) -> float:
    """Hinge angle (deg) at frame f: open, then down with a little speed at the end (it lands, it doesn't float)."""
    if span is None or f <= span[0]:
        return LID_OPEN
    k = min(1.0, (f - span[0]) / (span[1] - span[0]))
    return LID_OPEN + (LID_SHUT - LID_OPEN) * smoothstep(k) ** 1.5


def close_lid(timeline: dict, hinge) -> None:
    span = lid_span(timeline)
    if span is None or hinge is None:
        return
    frames = list(range(timeline["total_frames"]))
    angles = [lid_angle(span, f) for f in frames]
    z0 = hinge.location.z
    bake(hinge, "rotation_euler", 0, frames, [math.radians(a) for a in angles])
    bake(hinge, "location", 2, frames, [z0 + LID_LIFT * (a - LID_OPEN) / (LID_SHUT - LID_OPEN) for a in angles])


def phone_states(timeline: dict) -> list[tuple[int, str]]:
    """(frame, state) changes for the phone, from the script's events and actions."""
    # Off-screen voices heard through his phone (a call); not the people's voices from the lights (on_phone: false).
    off = {c for c in timeline.get("offscreen", []) if character_meta(c).get("on_phone", True)}
    changes: list[tuple[int, str]] = []
    state, call = None, False

    def go(frame: int, new: str) -> None:
        nonlocal state
        if new != state:
            changes.append((frame, new))
            state = new

    fps = timeline["fps"]
    for b in timeline["beats"]:
        ev = b.get("event") or {}
        comp = ev.get("component")
        speaker = b["speaker"]
        novato_acts = speaker == "novato" or (speaker is None and (b.get("reactor") or "novato") == "novato") or speaker in off
        if comp == "PhoneCall":
            go(b["start_frame"], "look")
            after = ev["props"].get("connect_after")
            if after is not None:
                go(b["start_frame"] + round(after * fps), "ear")
                call = True
        elif comp == "PhoneNotifications":
            # Opening on the room and cutting to the screen: it lights up on the desk first, and he picks it up
            # so it is in his hands (still) right on the cut.
            pick = b["start_frame"]
            if b.get("cut_camera") == "phone_screen" and b.get("cut_at") is not None:
                pick = max(pick, b["start_frame"] + round(b["cut_at"] * fps) - MOVE)
            go(pick, "look")
        elif call or speaker in off:
            go(b["start_frame"], "ear")
        elif novato_acts and b["action"] == "phone_ear":
            go(b["start_frame"], "ear")
        elif novato_acts and b["action"] == "look_phone":
            go(b["start_frame"], "look")
        elif novato_acts and b["action"] == "phone_down":
            go(b["start_frame"], "down")
        elif novato_acts and b["action"] == "phone_lower":
            go(b["start_frame"], "low")
        elif state == "low":
            pass  # stays in hand until something else happens to it
        elif state == "look" and not novato_acts:
            pass  # still reading while someone else talks
        else:
            go(b["start_frame"], "down" if state == "down" else "desk")  # face down it stays face down
    return changes


def _two_bone(shoulder: Vector, target: Vector, a: float, b: float, pole: Vector) -> tuple[Quaternion, Quaternion]:
    """Rotations for shoulder and elbow pivots (rest: both segments hang along -Z)."""
    d = target - shoulder
    dist = max(abs(a - b) + 1e-3, min(a + b - 1e-3, d.length))
    direction = d.normalized()
    cos_a = (a * a + dist * dist - b * b) / (2 * a * dist)
    ang = math.acos(max(-1.0, min(1.0, cos_a)))
    side = pole - direction * pole.dot(direction)
    side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
    elbow = shoulder + a * (math.cos(ang) * direction + math.sin(ang) * side)
    hand = elbow + (shoulder + direction * dist - elbow).normalized() * b
    down = Vector((0, 0, -1))
    q_upper = down.rotation_difference((elbow - shoulder).normalized())
    fore_world = (hand - elbow).normalized()
    q_fore = down.rotation_difference(q_upper.inverted() @ fore_world)
    return q_upper, q_fore


def animate(root, timeline: dict, phone, desk_world: Vector, keyboard_world: Vector | None, ai_heads: list[Vector], hinge=None,
            standing: bool = False, typing_ok: bool = True) -> None:
    """standing: no chair (a counter, a studio): the hands rest by the sides, or on `keyboard_world` (the counter)
    if given. typing_ok: False where there is nothing to type on (the hands rest instead of typing)."""
    from rigs.placeholders import FOREARM, UPPER_ARM

    body = find(root, "ctrl_body") or root
    arms = {s: (find(root, f"ctrl_arm_{s}"), find(root, f"ctrl_forearm_{s}")) for s in ("L", "R")}
    if not all(a and f for a, f in arms.values()):
        return
    import bpy

    bpy.context.view_layer.update()
    to_local = body.matrix_world.inverted()
    desk_local = to_local @ desk_world
    kb = to_local @ keyboard_world if keyboard_world is not None else to_local @ desk_world
    ai_local = [to_local @ h for h in ai_heads]
    shoulders = {s: arms[s][0].location.copy() for s in arms}
    poses = phone_poses(desk_local + Vector((0, 0, 0.019)), kb + Vector((-0.04, -0.02, 0.02)) if hinge is not None else None)

    fps, total = timeline["fps"], timeline["total_frames"]
    beats = timeline["beats"]
    off = set(timeline.get("offscreen", []))
    changes = phone_states(timeline)
    if not changes:
        changes = [(0, "desk")]
    first_state = changes[0][1]
    changes[0] = (0, first_state)  # already in place at the first frame

    # Hand base poses (no phone): keyboard, gestures, resting.
    kb_l, kb_r = kb + Vector((0.09, 0.04, 0.03)), kb + Vector((-0.09, 0.04, 0.03))
    rest_l, rest_r = Vector((0.17, -0.34, desk_local.z + 0.03)), Vector((-0.17, -0.34, desk_local.z + 0.03))
    if standing:  # arms down by the sides, elbows soft
        rest_l, rest_r = Vector((0.29, -0.09, 0.62)), Vector((-0.29, -0.09, 0.62))
        if keyboard_world is None:
            kb_l, kb_r = rest_l, rest_r
    ai = ai_local[0] if ai_local else Vector((0.6, -0.5, 1.0))

    # While the AI writes on his laptop (MemorySave) or stands at it (staging.plan), his hands go to his lap:
    # nobody should think he is the one typing.
    ai_spans = list(timeline.get("ai_at_laptop") or [])
    writes = [b["start_frame"] for b in beats if (b.get("event") or {}).get("component") == "MemorySave"]
    if writes:
        ai_spans.append([min(writes), total])

    span = lid_span(timeline) if hinge is not None else None
    if span:
        # The lid's top edge in body space for any hinge angle (the right hand rides it down).
        h_mat = to_local @ hinge.parent.matrix_world
        h_loc = hinge.location.copy()

        def lid_edge(f: int) -> Vector:
            a = lid_angle(span, f)
            lift = LID_LIFT * (a - LID_OPEN) / (LID_SHUT - LID_OPEN)
            m = Matrix.Translation(h_loc + Vector((0, 0, lift))) @ Matrix.Rotation(math.radians(a), 4, "X")
            return h_mat @ m @ Vector((0.03, -0.03, 0.235))

    def base_pose(b: dict, call: bool) -> tuple[Vector, Vector, bool]:
        if span and b["start_frame"] >= span[1]:
            return rest_l, rest_r, False  # the laptop is shut: nothing to type on
        if any(a <= b["start_frame"] < z for a, z in ai_spans):
            return rest_l + Vector((0, 0.05, -0.22)), rest_r + Vector((0, 0.05, -0.22)), False
        speaker = b["speaker"]
        actor = speaker == "novato" or (speaker is None and (b.get("reactor") or "novato") == "novato") or speaker in off
        emotion = b["emotion"] if actor else b["listener_emotion"]
        action = b["action"] if actor else "idle"
        if action == "close_laptop":
            return rest_l, rest_r, False
        if action == "shrug":
            return Vector((0.3, -0.3, 0.98)), Vector((-0.3, -0.3, 0.98)), False
        if action == "stretch":  # both arms up over the head (3 a.m.)
            return Vector((0.24, -0.04, 1.64)), Vector((-0.24, -0.04, 1.64)), False
        if action == "present_gesture":
            reach = shoulders["R"] + (ai - shoulders["R"]).normalized() * 0.5
            return kb_l, reach, False
        if action == "talk_gesture":
            return kb_l, Vector((-0.2, -0.42, 1.0)), False
        if action == "facepalm":
            return rest_l, Vector((-0.04, -0.24, 1.42)), False
        if action == "slump" or emotion in ("hundido",):
            return rest_l, rest_r, False
        if call:
            return rest_l, rest_r, False
        return kb_l, kb_r, typing_ok and emotion in TYPING_EMOTIONS

    # Per-beat base poses, with the call state at each beat.
    beat_of = []
    for i, b in enumerate(beats):
        beat_of += [i] * (b["end_frame"] - b["start_frame"])
    beat_of += [len(beats) - 1] * (total - len(beat_of))
    call_from = next((f for f, s in changes if s == "ear" and f > 0), None)
    call_from = call_from if any(b.get("event") and b["event"]["component"] == "PhoneCall" for b in beats) else None
    base = [base_pose(b, call_from is not None and b["start_frame"] >= call_from) for b in beats]

    def phone_at(f: int) -> tuple[Vector, Quaternion, float]:
        """Phone pose and how much the right hand holds it (0 = hand free, 1 = holding)."""
        prev_state, start, state = first_state, 0, first_state
        for cf, s in changes:
            if cf <= f:
                prev_state, start, state = state, cf, s
        k = (f - start) / MOVE if start > 0 else 1.0
        if k >= 1.0 or prev_state == state:
            loc, rot = poses[state]
            return loc, rot, 0.0 if state in ("desk", "down") else 1.0
        a_loc, a_rot = poses[prev_state]
        b_loc, b_rot = poses[state]
        if prev_state == "desk":  # reach (hand travels), then carry
            if k < 0.4:
                return a_loc, a_rot, smoothstep(k / 0.4)
            t = smoothstep((k - 0.4) / 0.6)
        elif state in ("desk", "down"):  # carry down (turning it over if face down), then let go
            if k > 0.6:
                return b_loc, b_rot, 1 - smoothstep((k - 0.6) / 0.4)
            t = smoothstep(k / 0.6)
        else:
            t = smoothstep(k)
        loc = a_loc.lerp(b_loc, t)
        loc.z += 0.06 * math.sin(math.pi * t)  # small arc
        return loc, a_rot.slerp(b_rot, t), 1.0

    # Regenerate clicks (LaptopChat regen_at): the right hand sits on the trackpad and taps on every press.
    pad = kb + Vector((-0.02, 0.085, 0.025))
    clicks = [(b, [b["start_frame"] + round(t * fps) for t in b["event"]["props"].get("regen_at") or []]) for b in beats
              if (b.get("event") or {}).get("component") == "LaptopChat" and b["event"]["props"].get("regen_at")]

    # Regenerate run: from the first chat with a variant counter to the last click the right hand stays on the
    # trackpad and nothing types, so each click reads as one press (not a hand sliding over from typing).
    chats = [b for b in beats if (b.get("event") or {}).get("component") == "LaptopChat"
             and b["event"]["props"].get("variant")]
    regen_run = (chats[0]["start_frame"], clicks[-1][0]["end_frame"]) if chats and clicks else None

    def tap(f: int) -> tuple[float, float]:
        """(how much the hand is on the trackpad, finger lift) at frame f."""
        if regen_run and regen_run[0] <= f < regen_run[1] + POSE_BLEND:
            on = 1.0 - smoothstep((f - regen_run[1]) / POSE_BLEND) if f >= regen_run[1] else 1.0
            lift = 0.0
            for _, presses in clicks:
                for p in presses:
                    if p - TAP_FRAMES <= f < p:
                        lift = max(lift, math.sin(math.pi / 2 * (f - (p - TAP_FRAMES)) / TAP_FRAMES))
            return on, lift
        for b, presses in clicks:
            a, z = b["start_frame"], b["end_frame"]
            if a - POSE_BLEND <= f < z + POSE_BLEND:
                on = smoothstep((f - (a - POSE_BLEND)) / POSE_BLEND) if f < a else (1 - smoothstep((f - z) / POSE_BLEND) if f >= z else 1.0)
                lift = 0.0
                for p in presses:
                    if p - TAP_FRAMES <= f < p:
                        lift = max(lift, math.sin(math.pi / 2 * (f - (p - TAP_FRAMES)) / TAP_FRAMES))
                    elif p <= f < p + 2:
                        lift = max(lift, 0.0)  # pressed: down on the pad
                return on, lift
        return 0.0, 0.0

    if regen_run:  # hands stay put through the whole run (no dropping to the lap on a listener beat)
        base = [(kb_l, kb_r, False) if regen_run[0] <= b["start_frame"] < regen_run[1] else p for b, p in zip(beats, base)]

    frames = list(range(total))
    ph_loc, ph_rot = [], []
    q = {(s, j): [] for s in ("L", "R") for j in ("up", "fore")}
    for f in frames:
        i = beat_of[f]
        b = beats[i]
        cur_l, cur_r, typing = base[i]
        if i > 0:
            pl, pr, _ = base[i - 1]
            k = smoothstep((f - b["start_frame"]) / POSE_BLEND)
            cur_l, cur_r = pl.lerp(cur_l, k), pr.lerp(cur_r, k)
        t = f / fps
        if regen_run and regen_run[0] <= f < regen_run[1]:
            # Waiting on the answer: slow restless drift, never the fast typing jitter.
            cur_l = cur_l + Vector((0.008 * math.sin(t * 1.7), 0.005 * math.sin(t * 1.1 + 0.5), 0.006 * math.sin(t * 2.3 + 1)))
        elif typing:
            cur_l = cur_l + Vector((0.01 * math.sin(t * 5.3), 0, 0.012 * max(0.0, math.sin(t * 19.0))))
            cur_r = cur_r + Vector((0.01 * math.sin(t * 4.1 + 1), 0, 0.012 * max(0.0, math.sin(t * 17.0 + 2))))
        on, lift = tap(f)
        if on:
            cur_r = cur_r.lerp(pad + Vector((0, -0.01 * lift, TAP_LIFT * lift)), on)
        if regen_run and regen_run[0] <= f < regen_run[1]:  # the resting hand on the pad drifts a little too
            cur_r = cur_r + Vector((0.006 * math.sin(t * 1.3 + 2), 0.004 * math.sin(t * 0.9), 0.0))
        loc, rot, hold = phone_at(f)
        ph_loc.append(loc)
        ph_rot.append(rot)
        # Grip: the hand sits behind the phone, a bit below its centre.
        grip = loc - (rot @ Vector((0, 0, 1))) * 0.04 - (rot @ Vector((0, 1, 0))) * 0.05
        hand_r = cur_r.lerp(grip, hold)
        if span and span[0] - LID_REACH <= f <= span[1] + LID_REACH:
            # Closing the laptop: reach the top edge, ride it down, let go once it lands.
            w = smoothstep((f - (span[0] - LID_REACH)) / LID_REACH) if f < span[0] else (
                1.0 - smoothstep((f - span[1]) / LID_REACH) if f > span[1] else 1.0)
            hand_r = hand_r.lerp(lid_edge(min(f, span[1])) + Vector((0, -0.02, 0.03)), w)
        if typing_ok and first_state == "ear" and changes[0][1] == "ear" and f < (changes[1][0] if len(changes) > 1 else total):
            # On the phone at the start: the free hand keeps typing (busy, half-listening).
            cur_l = kb_l + Vector((0.01 * math.sin(t * 5.3), 0, 0.012 * max(0.0, math.sin(t * 19.0))))
        for side, target, pole in (("L", cur_l, Vector((0.8, 0.5, -0.6))), ("R", hand_r, Vector((-0.8, 0.5, -0.6)))):
            qu, qf = _two_bone(shoulders[side], target, UPPER_ARM, FOREARM + 0.02, pole)
            q[(side, "up")].append(qu)
            q[(side, "fore")].append(qf)

    for side in ("L", "R"):
        for joint, obj in zip(("up", "fore"), arms[side]):
            obj.rotation_mode = "QUATERNION"
            vals = q[(side, joint)]
            # keep quaternions in one hemisphere so interpolation never flips
            for n in range(1, len(vals)):
                if vals[n].dot(vals[n - 1]) < 0:
                    vals[n] = -vals[n]
            for c in range(4):
                bake(obj, "rotation_quaternion", c, frames, [v[c] for v in vals])

    if phone is not None:
        phone.parent = body
        phone.matrix_parent_inverse = Matrix.Identity(4)
        phone.rotation_mode = "QUATERNION"
        for c in range(3):
            bake(phone, "location", c, frames, [v[c] for v in ph_loc])
        for n in range(1, len(ph_rot)):
            if ph_rot[n].dot(ph_rot[n - 1]) < 0:
                ph_rot[n] = -ph_rot[n]
        for c in range(4):
            bake(phone, "rotation_quaternion", c, frames, [v[c] for v in ph_rot])
