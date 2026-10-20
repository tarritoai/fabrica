"""The girl's room (miniseries part 2, tres-tokens): the real place behind the lonely light.

3 a.m., dark: she sits on the edge of her bed, the phone lighting her face, the city through the window
behind her, a few warm fairy lights. Built far away from the room and the world (ROOM_AT) so nothing leaks;
mundo.py dims the sky and the sun while the camera is in here.

Romance seed: on her bedside table, the same mug the lead has on his desk.
"""

from __future__ import annotations

import bpy
from mathutils import Vector

import props
from lib import empty, material, primitive, rad

ROOM_AT = Vector((0.0, 6000.0, 0.0))
SEAT = Vector((0.0, 0.25, 0.0))  # her slot (local): on the edge of the bed, facing -Y (the camera)
W, D, H = 3.2, 2.6, 2.5  # room width (x), depth (y, from the front edge to the back wall), height


def _w(v) -> Vector:
    return ROOM_AT + Vector(v)


def build() -> dict:
    """Build the room; returns {"slot": world position for her, "facing": yaw, "face": where her face is}."""
    root = empty("CUARTO_CHICA", tuple(ROOM_AT))
    wall = material("chica_wall", "#3a3550", 0.95)
    floor = material("chica_floor", "#2b2433", 0.9)
    back_y = 1.45
    # Floor, back wall (with a window), side walls and ceiling: closed, so the world's sun and sky stay out.
    primitive("cube", "chica_floor", (0, 0, -0.02), (W / 2, D / 2 + 0.6, 0.02), root, floor)
    primitive("cube", "chica_ceiling", (0, 0, H), (W / 2, D / 2 + 0.6, 0.02), root, wall)
    win_x, win_z, win_w, win_h = -0.55, 1.55, 0.9, 0.75
    # Back wall in four pieces around the window opening.
    primitive("cube", "chica_wall_left", ((-W / 2 + win_x - win_w / 2) / 2, back_y, H / 2),
              ((win_x - win_w / 2 + W / 2) / 2, 0.05, H / 2), root, wall)
    primitive("cube", "chica_wall_right", ((W / 2 + win_x + win_w / 2) / 2, back_y, H / 2),
              ((W / 2 - win_x - win_w / 2) / 2, 0.05, H / 2), root, wall)
    primitive("cube", "chica_wall_low", (win_x, back_y, (win_z - win_h / 2) / 2), (win_w / 2, 0.05, (win_z - win_h / 2) / 2), root, wall)
    top0 = win_z + win_h / 2
    primitive("cube", "chica_wall_high", (win_x, back_y, (top0 + H) / 2), (win_w / 2, 0.05, (H - top0) / 2), root, wall)
    for side, x in (("L", -W / 2), ("R", W / 2)):
        primitive("cube", f"chica_wall_{side}", (x, 0, H / 2), (0.05, D / 2 + 0.6, H / 2), root, wall)
    # The city at night beyond the window (a lit plane a little behind the glass), and a cool rim through it.
    city = primitive("plane", "chica_city", (win_x, back_y + 0.9, win_z), (1.4, 1.0, 1), root, props.city_material())
    city.rotation_euler = (rad(90), 0, 0)
    frame_mat = material("chica_window_frame", "#1c1a24", 0.8)
    for name, loc, sc in (("top", (win_x, back_y - 0.02, win_z + win_h / 2), (win_w / 2 + 0.03, 0.04, 0.03)),
                          ("bot", (win_x, back_y - 0.02, win_z - win_h / 2), (win_w / 2 + 0.03, 0.06, 0.03)),
                          ("mid", (win_x, back_y - 0.02, win_z), (0.015, 0.03, win_h / 2))):
        primitive("cube", f"chica_window_{name}", loc, sc, root, frame_mat)

    # Bed along the back wall, her on its edge; bedside table with the mug (same as the lead's) and a dark lamp.
    # Kenney bedSingle at yaw 90 spans x [-2.19, 0], y [0.75, 1.86] from its origin: long side along the wall,
    # its front edge just behind her hips (she sits on it), her near its left end so the bedside table is in shot.
    props.kenney("bedSingle", (1.495, SEAT.y - 0.05 - 0.75, 0), 90, root, tint={"wood": "#3d2c35", "carpet": "#c9b8e6",
                                                                       "carpetDarker": "#9e8cc4", "carpetWhite": "#e8e2f2"})
    props.kenney("cabinetBedDrawerTable", (-0.78, SEAT.y + 0.55, 0), 180, root, tint={"wood": "#3d2c35"})
    props.mug((-0.95, SEAT.y + 0.32, 0.47), root)
    props.kenney("lampRoundTable", (-1.1, SEAT.y + 0.42, 0.45), 0, root, tint={"lamp": "#e8d2b0"})
    props.fairy_lights((-1.45, back_y - 0.06, 2.05), (1.45, back_y - 0.06, 2.0), 0.18, 16, root)
    props.poster("chica_poster", (1.0, back_y - 0.06, 1.6), (0.32, 0.42), ["#6cc3a6", "#f09a90", "#2a2440"], root)

    # Light: almost dark. The phone's cold glow on her face is the key; the window a cool rim behind her.
    props.area_light("chica_window_rim", tuple(_w((win_x, back_y - 0.1, win_z))), tuple(_w((0.0, 0.2, 1.1))), "#7fa0ff", 12, 0.8)
    props.point_light("chica_fairy_warm", tuple(_w((0.0, back_y - 0.3, 1.9))), "#ffb36b", 6, 0.3)
    face = _w((0.0, SEAT.y - 0.05, 1.5))
    # The phone's glow from a little below (soft, not a torch), and a gentle warm key from the fairy-light side so
    # her face reads soft and pretty rather than lit from under the chin.
    props.point_light("chica_phone_glow", tuple(face + Vector((0.0, -0.35, -0.2))), "#cfe0ff", 1.2, 0.12)
    props.area_light("chica_key", tuple(face + Vector((-0.9, -1.0, 0.45))), tuple(face), "#ffcaa0", 9, 1.0)
    return {"slot": _w(SEAT), "facing": 0.0, "face": face, "root": root}


def cameras(face: Vector) -> dict:
    """Her shots: a medium one (the room, the phone light) and her face close."""
    return {
        "cuarto_chica": dict(loc=face + Vector((0.35, -1.75, -0.2)), end=face + Vector((0.3, -1.55, -0.2)),
                             target=face + Vector((-0.05, 0, -0.25)), lens=35, fstop=2.2),
        "cuarto_chica_cerca": dict(loc=face + Vector((0.18, -1.6, -0.15)), end=face + Vector((0.15, -1.42, -0.13)),
                                   target=face + Vector((0, 0, -0.14)), lens=50, fstop=2.0),
    }
