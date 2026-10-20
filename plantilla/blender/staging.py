"""AI moves around the desk (`beat.ai_move`): it waddles to the laptop and back with little hops.

plan() returns the per-frame root path; cameras use it so the AI close-up follows the walk,
and animate/arms use the intervals to know when the AI stands at the keyboard.
"""

from __future__ import annotations

import math

from mathutils import Vector

from lib import bake, rad, smoothstep

WALK = 1.3  # s
HOPS = 4
HOP_H = 0.018  # m
ROCK = 7.0  # deg of side-to-side rock per hop


def plan(timeline: dict, home, home_yaw: float, laptop, laptop_yaw: float, front=None, front_yaw: float = 0.0) -> dict | None:
    beats, fps, total = timeline["beats"], timeline["fps"], timeline["total_frames"]
    moves = [(b["start_frame"] + int(b.get("ai_move_at", 0.0) * fps), b["ai_move"], bool(b.get("ai_move_instant")))
             for b in beats if b.get("ai_move")]
    if not moves:
        return None
    home, laptop = Vector(home), Vector(laptop)
    spots = {"back": (home, home_yaw), "laptop": (laptop, laptop_yaw)}
    if front is not None:
        spots["front"] = (Vector(front), front_yaw)
    loc, yaw, rock = [], [], []
    cur, cur_yaw = home, home_yaw
    pending = sorted(moves)
    walk = int(WALK * fps)
    active = None  # (start, from_loc, from_yaw, to_loc, to_yaw)
    for f in range(total):
        if pending and f >= pending[0][0]:
            start, where, instant = pending.pop(0)
            to, to_yaw = spots[where]
            active = (start, cur, cur_yaw, to, to_yaw, instant)
        if active:
            start, a, ay, b, by, instant = active
            k = 1.0 if instant else min(1.0, (f - start) / walk)
            e = smoothstep(k)
            p = a.lerp(b, e)
            hop = abs(math.sin(math.pi * HOPS * k)) * HOP_H * (1.0 if k < 1 else 0.0)
            loc.append(p + Vector((0, 0, hop)))
            yaw.append(ay + (by - ay) * e)
            rock.append(ROCK * math.sin(math.pi * HOPS * k) if k < 1 else 0.0)
            if k >= 1:
                cur, cur_yaw, active = b, by, None
        else:
            loc.append(cur.copy())
            yaw.append(cur_yaw)
            rock.append(0.0)
    # Frames where it stands at the laptop: from arrival until it sets off again.
    at_laptop, arrive = [], None
    for start, where, instant in sorted(moves):
        if where == "laptop":
            arrive = start + (0 if instant else walk)
        elif arrive is not None:
            at_laptop.append([arrive, start])
            arrive = None
    if arrive is not None:
        at_laptop.append([arrive, total])
    return {"loc": loc, "yaw": yaw, "rock": rock, "home": home, "home_yaw": home_yaw, "at_laptop": at_laptop,
            "front": spots["front"][0] if "front" in spots else None}


def bake_root(root, path: dict) -> None:
    import bpy

    # Props that only sit next to it (the tiny cup) stay on the desk.
    bpy.context.view_layer.update()
    for child in list(root.children):
        if child.name.split(".")[0] == "claude_cup":
            mw = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = mw
    frames = list(range(len(path["loc"])))
    for i in range(3):
        bake(root, "location", i, frames, [v[i] for v in path["loc"]])
    bake(root, "rotation_euler", 2, frames, [rad(y) for y in path["yaw"]])
    bake(root, "rotation_euler", 1, frames, [rad(r) for r in path["rock"]])
