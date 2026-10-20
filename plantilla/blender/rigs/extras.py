"""Secondary humans (the flatmate on the sofa): where they look and what their hands do.

Simpler than the novato (rigs/arms.py): no desk or keyboard. Per beat the hands go to a pose
(lap, showing the phone, shrug, holding the phone to read it) and the head turns towards whoever
they are talking to. Their own phone (props.phone) appears in the hand only while it is used.
"""

from __future__ import annotations

import math

from mathutils import Matrix, Vector

from lib import bake, find, smoothstep
from rigs.arms import _frame, _two_bone

BLEND = 9  # frames between hand poses
LOOK_BLEND = 10


def _pose(beat: dict, char_id: str, off: set) -> str:
    speaker = beat["speaker"] if beat["speaker"] not in off else None
    actor = speaker == char_id or (speaker is None and beat.get("reactor") == char_id)
    if not actor:
        return "lap"
    action = beat["action"]
    if action == "present_gesture":
        return "show"
    if action == "look_phone":
        return "read"
    if action == "shrug":
        return "shrug"
    return "lap"


def animate(root, char_id: str, timeline: dict, look_at: Vector | None, phone) -> list[float]:
    """Bake the pose; returns the phone's per-frame visibility (its screens are baked against it)."""
    from rigs.placeholders import FOREARM, UPPER_ARM

    import bpy

    body = find(root, "ctrl_body") or root
    head = find(root, "ctrl_head")
    arms = {s: (find(root, f"ctrl_arm_{s}"), find(root, f"ctrl_forearm_{s}")) for s in ("L", "R")}
    if not all(a and f for a, f in arms.values()):
        return []
    bpy.context.view_layer.update()
    to_local = body.matrix_world.inverted()
    shoulders = {s: arms[s][0].location.copy() for s in arms}
    target = to_local @ look_at if look_at is not None else Vector((1, -1, 1.4))
    # Yaw (about the neck) that turns the face (-Y) towards the novato.
    to_t = target - Vector((0, 0, 1.4))
    look_yaw = math.atan2(to_t.x, -to_t.y)

    face_dir = (Vector((math.sin(look_yaw), -math.cos(look_yaw), 0)) * 0.6 + Vector((0, -1, 0)) * 0.4).normalized()
    show_loc = Vector((0.2, -0.52, 1.06))  # left hand: the side the novato is on
    read_loc = Vector((-0.02, -0.4, 0.95))
    from lib import character_meta

    if character_meta(char_id).get("human", {}).get("pose") == "sofa" and char_id != "hugo":
        # Sitting on a bed at night: the phone held up near the face (the light on her face is the shot).
        read_loc = Vector((-0.02, -0.3, 1.2))
    eyes = Vector((0, -0.2, 1.42))
    phone_pose = {
        # Screen (+Z) turned towards the novato and the camera; top of the phone up.
        # Screen mostly to the camera in front of him, a little towards the novato, so the chat reads.
        "show": (show_loc, _frame(Vector((0.3, -1.0, 0.12)), Vector((0, 0, 1)))),
        "read": (read_loc, _frame(eyes - read_loc, Vector((0, 0.4, 1)))),
    }
    hands = {
        "lap": (Vector((0.15, -0.33, 0.66)), Vector((-0.15, -0.33, 0.66))),
        "shrug": (Vector((0.36, -0.28, 0.98)), Vector((-0.36, -0.28, 0.98))),
    }

    fps, total = timeline["fps"], timeline["total_frames"]
    beats = timeline["beats"]
    off = set(timeline.get("offscreen", []))
    beat_of = []
    for i, b in enumerate(beats):
        beat_of += [i] * (b["end_frame"] - b["start_frame"])
    beat_of += [len(beats) - 1] * (total - len(beat_of))
    poses = [_pose(b, char_id, off) for b in beats]

    def hand_targets(pose: str, t: float) -> tuple[Vector, Vector, float]:
        """(left hand, right hand, phone visible 0/1)."""
        if pose in phone_pose:
            loc, rot = phone_pose[pose]
            # Held by the bottom edge: the hand must not cover the messages.
            grip = loc - (rot @ Vector((0, 0, 1))) * 0.035 - (rot @ Vector((0, 1, 0))) * 0.105
            if pose == "show":
                return grip, hands["lap"][1], 1.0  # shown with the left hand, the right rests
            return grip + Vector((0.07, 0.02, -0.01)), grip, 1.0
        lft, rgt = hands[pose]
        if pose == "shrug":
            lift = 0.05 * math.sin(math.pi * min(1.0, t / 0.5))
            lft, rgt = lft + Vector((0, 0, lift)), rgt + Vector((0, 0, lift))
        return lft, rgt, 0.0

    frames = list(range(total))
    q = {(s, j): [] for s in ("L", "R") for j in ("up", "fore")}
    yaw_vals, ph_loc, ph_rot, ph_vis = [], [], [], []
    for f in frames:
        i = beat_of[f]
        b = beats[i]
        t_beat = (f - b["start_frame"]) / fps
        k = smoothstep((f - b["start_frame"]) / BLEND) if i > 0 else 1.0
        l1, r1, v1 = hand_targets(poses[i], t_beat)
        l0, r0, v0 = hand_targets(poses[i - 1], t_beat) if i > 0 else (l1, r1, v1)
        left, right = l0.lerp(l1, k), r0.lerp(r1, k)
        for side, tgt, pole in (("L", left, Vector((0.8, 0.5, -0.6))), ("R", right, Vector((-0.8, 0.5, -0.6)))):
            qu, qf = _two_bone(shoulders[side], tgt, UPPER_ARM, FOREARM + 0.02, pole)
            q[(side, "up")].append(qu)
            q[(side, "fore")].append(qf)
        # Phone: follows the right hand's pose; visible while in use.
        p_now = phone_pose.get(poses[i]) or phone_pose.get(poses[i - 1] if i > 0 else "", None)
        if p_now:
            loc, rot = p_now
            holder = left if (poses[i] == "show" or (poses[i] not in phone_pose and i > 0 and poses[i - 1] == "show")) else right
            ph_loc.append(loc if poses[i] in phone_pose else loc.lerp(holder, k))
            ph_rot.append(rot)
        else:
            ph_loc.append(right.copy())
            ph_rot.append(_frame(Vector((0, -1, 0.2)), Vector((0, 0, 1))))
        ph_vis.append(1.0 if (poses[i] in phone_pose and k > 0.3) or (i > 0 and poses[i - 1] in phone_pose and k < 0.7) else 0.0)
        # Head: towards the novato while talking/listening; down at the phone when reading it.
        y_cur = 0.0 if poses[i] == "read" else look_yaw
        y_prev = (0.0 if poses[i - 1] == "read" else look_yaw) if i > 0 else y_cur
        yaw_vals.append(y_prev + (y_cur - y_prev) * smoothstep((f - b["start_frame"]) / LOOK_BLEND))

    for side in ("L", "R"):
        for joint, obj in zip(("up", "fore"), arms[side]):
            obj.rotation_mode = "QUATERNION"
            vals = q[(side, joint)]
            for n in range(1, len(vals)):
                if vals[n].dot(vals[n - 1]) < 0:
                    vals[n] = -vals[n]
            for c in range(4):
                bake(obj, "rotation_quaternion", c, frames, [v[c] for v in vals])
    if head is not None:
        bake(head, "rotation_euler", 2, frames, [0.6 * y for y in yaw_vals])  # the eyes do the rest

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
        hidden = [1.0 - v for v in ph_vis]
        for obj in [phone, *phone.children_recursive]:
            if "_screen_" not in obj.name:  # screens are baked by build_scene against this visibility
                bake(obj, "hide_render", -1, frames, hidden, interp="CONSTANT")
    return ph_vis
