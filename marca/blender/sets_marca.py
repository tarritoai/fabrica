"""The original series' sets (brand pack, not shipped in the student's template).

`escritorio_noche` here is the floating room on a rock in the galaxy (brick edges, fairy lights, planet with rings);
`mundo` is that room plus the world inside, joined by a portal (mundo.py, world_proto.py, cuarto_chica.py).
Copy marca/ over a template copy and blender/sets.py registers both (they replace the neutral room's
`escritorio_noche` alias). Its furniture code is a verbatim copy of the original, so old renders stay identical.
"""

from __future__ import annotations

import random

import bpy

from lib import empty, material

def escritorio_noche(timeline: dict | None = None) -> dict:
    """Bedroom-office at 3 a.m.: the novato sits at his desk facing camera, the window (rain, city)
    behind him; the AI stands on the desk next to the laptop. Warm desk lamp vs cold screen and moonlight."""
    import props

    fps = (timeline or {}).get("fps", 30)
    total = (timeline or {}).get("total_frames", 900)
    props.galaxy_world(fps)
    root = empty("SET_escritorio_noche")
    K = props.kenney

    # Floor + rug.
    # The room is a diorama on a chunk of rock floating in the galaxy.
    props.floating_island(root, (0, 0.35, 0), 3.45, 1.9, 2.4, material("set_floor", "#1b1a20", 0.75))
    props.crystals(root, (0, 0.35, 0), 3.45, 1.9)
    props.planet_with_ring(root, (-24.0, 70.0, 20.0), 4.0)
    props.floating_rocks(root, 7, ((-6, 6), (2.6, 7), (-2.5, 4)), seed=8)
    props.floating_rocks(root, 4, ((-6.5, -3.9), (-1, 2), (-2, 3)), seed=9)
    props.floating_rocks(root, 4, ((3.9, 6.5), (-1, 2), (-2, 3)), seed=10)
    K("rugRectangle", (-1.4, 0.15, 0.002), 0, root, tint={"carpet": "#3b2f4a", "carpetDarker": "#2a2236"})

    # Back wall: wall | window | wall (Kenney modules, 1.95 m wide each), dark plaster tint.
    wall_y = 1.75
    wall_tint = {"_defaultMat": "#273047", "wood": "#3a2a20", "metalDark": "#1a1d24"}
    w = props.KENNEY_SCALE
    SILL = 0.766  # the window's sill (measured in Blender)
    # Window module in the middle; the rest of the walls are torn away like a room ripped out of a building:
    # crumbling brick edges and a few loose bricks drifting off into space.
    K("wallWindow", (-0.5 * w, wall_y, 0), 0, root, tint=wall_tint)
    wall_h = 1.29 * w  # Kenney wall module height
    plaster = material("set_wall_plaster", "#273047", 0.95)
    brick = material("set_wall_brick", "#8a5646", 0.9)
    back_y = wall_y + 0.04
    props.broken_wall(root, "wall_back_L", (-1.5 * w, back_y, 0), (1, 0, 0), w, wall_h,
                      lambda t: 0.7 + 0.3 * t + (0.12 if 0.3 < t < 0.45 else 0), plaster, brick, seed=2, floaters=2)
    props.broken_wall(root, "wall_back_R", (0.5 * w, back_y, 0), (1, 0, 0), w, wall_h,
                      lambda t: 1 - 0.85 * t ** 1.3 - (0.12 if 0.55 < t < 0.7 else 0), plaster, brick, seed=3, floaters=4)
    props.broken_wall(root, "wall_side_L", (-1.5 * w - 0.06, back_y, 0), (0, -1, 0), 2.6, wall_h,
                      lambda t: 0.72 * (1 - t) ** 0.8 + 0.06, plaster, brick, seed=4, floaters=3)
    # No glass in space: the window is an open frame onto the galaxy.
    for obj in bpy.data.objects:
        if obj.type == "MESH" and any(sl.material and sl.material.name.split(".")[0] == "glass" for sl in obj.material_slots):
            obj.hide_render = True

    # Outside: a drifting galaxy sky (the window is the show).
    rng = random.Random(3)

    # Desk, chair, laptop, lamp and clutter.
    desk_top = 0.384 * w
    K("desk", (0.715, 0.935, 0), 180, root, tint={"wood": "#3b2b24", "metal": "#2a2d33"})
    K("chairDesk", (0.01, 1.62, 0), 180, root, tint={"carpet": "#2e3440"})  # origin is a corner: centred under the lead
    lap = props.laptop((-0.32, 0.62, desk_top), 180, root)
    # When the AI walks to the laptop its close-up looks across the desk: the lamp moves out of that line.
    lamp_x = -0.98 if (timeline or {}).get("ai_visits_laptop") else -0.72
    # A desk lamp in the cast (rigs/thing.py form "lampara") IS the lamp: the prop goes (its light stays).
    from lib import character_meta

    lamp_in_cast = any((character_meta(c).get("object") or {}).get("form") == "lampara"
                       for c in (timeline or {}).get("characters", []) if not character_meta(c).get("offscreen"))
    if not lamp_in_cast:
        K("lampSquareTable", (lamp_x, 0.2 if lamp_x == -0.72 else 0.35, desk_top), 0, root, tint={"lamp": "#f2d6a8"})
    props.mug((0.02, 0.8, desk_top), root)
    # Copies of the AI (beat.ai_copies) need room: the speaker, plant, books and bin go.
    crowded = any((b.get("ai_copies") or 1) > 1 for b in (timeline or {}).get("beats", []))
    if not crowded:
        K("speakerSmall", (0.66, 0.9, desk_top), 200, root, scale=1.0)
        K("plantSmall1", (0.62, 0.33, desk_top), 0, root, scale=1.6)
    if not crowded:
        K("books", (0.18, 0.78, desk_top), 160, root, scale=1.4)  # the mini peeks out behind the mug instead
    K("cardboardBoxClosed", (1.0, 0.85, 0), 15, root)
    if not crowded:
        K("trashcan", (0.95, 0.2, 0), 0, root)

    # Bookcase + plant + posters + fairy lights on the back wall.
    K("bookcaseOpen", (1.35, wall_y - 0.5, 0), 0, root, tint={"wood": "#4a3326"})
    for i, z in enumerate((0.05, 0.47, 0.9, 1.32)):
        K("books", (1.42 + (i % 2) * 0.22, wall_y - 0.47, z), rng.uniform(-10, 10), root, scale=1.6)
    K("pottedPlant", (-1.75, 1.35, 0), 30, root)
    # The flatmate's corner: sofa on the rug, turned towards the desk, a couple of cushions.
    sofa_at, sofa_yaw = (-2.8, -0.157, 0), 25  # Kenney origin is a back corner; this centres it at (-2.1, 0.6), 3/4 to camera
    K("loungeSofa", sofa_at, sofa_yaw, root, tint={"carpet": "#5a4a6a", "carpetDarker": "#463a54", "wood": "#3b2b24"})
    props.poster("poster_a", (-1.55, wall_y - 0.03, 1.65), (0.5, 0.7), ["#1d2a44", "#ff8a3d", "#3d8bff", "#e8e2d4"], root)
    props.poster("poster_b", (-2.25, wall_y - 0.03, 1.5), (0.35, 0.45), ["#2b1d2f", "#ffd38a", "#7a3b2e"], root)
    props.fairy_lights((-1.05, wall_y - 0.06, 2.34), (1.05, wall_y - 0.06, 2.34), 0.26, 22, root)

    # Lights: warm lamp (key), cold laptop glow on the face, moonlight rim through the window.
    props.point_light("lamp_light", (-0.6, 0.32, desk_top + 0.48), "#ffb066", 70, 0.07)
    # Soft warm key from the lamp side, in front: lights faces (and the AI) for camera.
    props.area_light("lamp_key", (-1.3, -0.5, 1.7), (0.0, 0.85, 1.05), "#ffb47a", 85, 1.2)
    props.area_light("screen_light", (-0.32, 0.66, desk_top + 0.3), (-0.32, 1.12, desk_top + 0.62), "#9cc0ff", 2.5, 0.3, 0.18)
    props.area_light("moon_rim", (0.8, 3.6, 3.0), (-0.2, 1.0, 1.2), "#7fa2ff", 420, 1.5)
    # Cold rim behind the AI on the desk: separates the terracotta from the warm room.
    props.area_light("ai_rim", (0.9, 1.5, 1.5), (0.32, 0.62, 1.0), "#8fb4ff", 70, 0.6)
    props.area_light("room_fill", (1.6, -2.4, 1.8), (0, 0.8, 1.0), "#4a6aaa", 70, 3.0)
    props.point_light("fairy_glow", (0, wall_y - 0.45, 2.3), "#ffc46b", 25, 0.15)
    # Galaxy glow from the open side: a soft violet rim on everyone.
    props.area_light("galaxy_rim", (3.6, 2.4, 2.4), (-0.1, 0.9, 1.1), "#a77bff", 260, 2.5)
    props.area_light("galaxy_under", (0.0, -1.5, -2.5), (0.0, 0.4, -0.8), "#7d5cff", 35, 3.0)
    if timeline and any(b.get("away") for b in timeline["beats"]):
        # Where his voice comes from while he is out (beat.novato_away): off to camera left, past the sofa.
        timeline.setdefault("_gaze_points", {})["_door"] = (-3.2, -0.6, 1.5)

    return {
        "slots": {
            "left": (-0.32, 1.12, -0.06),
            "right": (0.32, 0.62, desk_top),
            "right_a": (0.2, 0.58, desk_top),
            "right_b": (0.62, 0.66, desk_top),
            # Right next to the laptop's keyboard: close enough for the stubby arms to type.
            "laptop": (0.0, 0.47, desk_top),
            "sofa": (-1.668, 0.736, 0.0),
            # In front of the laptop, between the novato and whatever is out there (the robot).
            "front": (0.02, 0.3, desk_top),  # beside the laptop, not behind it: the screen must not cross the shot  # on the seat, the end nearer the desk (measured in Blender)
        },
        "facing": {"left": 22, "right": -62, "right_a": -55, "right_b": -70, "laptop": -60, "sofa": 25, "front": -15},
        "ai_scale": 0.72,
        "seated": ["novato"],
        "laptop": lap,
        "phone_spot": (-0.6, 0.74, desk_top),
        # Copies of the AI (beat.ai_copies), in the order they appear: the first ones on the desk (two_shot sees
        # them), then the floor, the box, the bookcase and the window sill behind him (wide_room). Clear of
        # the lines of closeup_ai, closeup_novato and closeup_mini. They turn to face him (blender/copies.py):
        # none on the floor straight in front of him, or the camera only sees their backs.
        "copy_spots": [
            (0.64, 0.8, desk_top), (0.6, 0.33, desk_top), (0.95, -0.15, 0.0), (-0.42, -0.2, 0.0),
            (1.15, 1.1, 0.49), (1.6, 1.45, 1.657), (1.9, 1.45, 0.9), (1.35, 0.4, 0.0),
            (0.15, 1.8, SILL), (-0.95, 0.05, 0.0), (1.3, -0.45, 0.0),
        ],
        # Musical episodes (timeline score): the copies line up on the floor in front of the desk like a band,
        # low to high from left to right, facing the camera (the AI itself plays from the desk).
        # A V: the AI leads from the point, the copies step back to each side (a straight row of five doesn't
        # fit across a vertical frame).
        "band_spots": [(-0.01, 0.08, 0.0), (0.71, 0.08, 0.0), (-0.37, 0.36, 0.0), (1.07, 0.36, 0.0)],
        "band_lead": (0.35, -0.2, 0.0),
        "band_target": (0.35, -3.5, 0.4),
        "mini_spot": ((0.09, 0.87, desk_top), -25),  # peeking out behind the mug
        "desk_top": desk_top,
        "island_center": (0.0, 0.35, 0.0),
    }


def mundo(timeline: dict | None = None) -> dict:
    """The miniseries set: the room plus the world inside, joined by the portal (blender/mundo.py)."""
    import mundo as world_set

    return world_set.build(timeline or {})



SETS = {"escritorio_noche": escritorio_noche, "mundo": mundo}
