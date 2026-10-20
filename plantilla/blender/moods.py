"""Room light moods per beat (`beat.light`, `beat.light_snap`): the light follows the emotion.

Each mood multiplies the energy the set builder gave every named light; the fairy-light bulbs'
emission follows too. Changes fade slowly, or snap in two frames (the twist).
"""

from __future__ import annotations

import bpy

from lib import bake, smoothstep

FADE = 3.0  # s
SNAP = 2  # frames

# light name -> energy multiplier; "_fairy" = bulb emission multiplier; "_wb" = white-balance temperature
# multiplier on 6500 K (above 1 grades the whole picture warmer: the change has to read on a phone); "_think" = the AIs'
# lid-slit glow (in the dark it is the only light left, so it has to be seen where it comes from).
MOODS = {
    "noche": {},
    # 3 a.m.: the room sinks into shadow; the low lamp, the screen and the AI's own glow carry the faces.
    "madrugada": {"wall_wash": 0.2, "lamp_key": 0.22, "lamp_light": 0.5, "fairy_glow": 0.25, "_fairy": 0.35, "moon_rim": 0.45, "room_fill": 0.12,
                  "galaxy_rim": 0.3, "ai_rim": 0.5, "galaxy_under": 0.25, "screen_light": 3.0, "_wb": 0.88},
    "tibio": {"wall_wash": 0.8, "lamp_key": 1.4, "lamp_light": 1.6, "fairy_glow": 3.0, "_fairy": 1.5, "moon_rim": 0.7, "room_fill": 0.75,
              "galaxy_rim": 0.7, "ai_rim": 0.75, "galaxy_under": 0.8, "_wb": 1.08},
    "calido": {"wall_wash": 1.4, "lamp_key": 2.6, "lamp_light": 3.0, "fairy_glow": 8.0, "_fairy": 2.4, "moon_rim": 0.2, "room_fill": 0.3,
               "galaxy_rim": 0.25, "ai_rim": 0.3, "galaxy_under": 0.4, "screen_light": 3.0, "_wb": 1.3},
    # Dawn after the threat: warm and wide; the fairy lights flicker back (a dawn light comes from blender/future.py).
    "amanecer": {"wall_wash": 1.2, "lamp_key": 2.0, "lamp_light": 0.0, "fairy_glow": 3.0, "_fairy": 1.4, "moon_rim": 0.3, "room_fill": 0.6,
                 "galaxy_rim": 0.5, "ai_rim": 0.6, "galaxy_under": 0.5, "screen_light": 0.6, "_wb": 1.35},
    # Power cut: lamp and fairy lights dead; the laptop on battery lights the faces.
    "apagon": {"wall_wash": 0.05, "lamp_key": 0.05, "lamp_light": 0.0, "fairy_glow": 0.0, "_fairy": 0.0, "moon_rim": 0.6, "room_fill": 0.25,
               "galaxy_rim": 0.6, "ai_rim": 0.5, "galaxy_under": 0.5, "screen_light": 2.2, "_wb": 0.85},
    # The laptop dies too: only the cold light from space.
    "oscuro": {"wall_wash": 0.0, "lamp_key": 0.0, "lamp_light": 0.0, "fairy_glow": 0.0, "_fairy": 0.0, "moon_rim": 0.5, "room_fill": 0.12,
               "galaxy_rim": 0.5, "ai_rim": 0.3, "galaxy_under": 0.4, "screen_light": 0.0, "_wb": 0.8, "_think": 2.5},
    # The future: lamp and fairy lights dead; the red siren and the robot's spotlight do the rest (blender/future.py).
    "ruinas": {"wall_wash": 0.1, "lamp_key": 0.12, "lamp_light": 0.0, "fairy_glow": 0.0, "_fairy": 0.0, "moon_rim": 0.5, "room_fill": 0.35,
               "galaxy_rim": 0.6, "ai_rim": 0.5, "galaxy_under": 0.6, "screen_light": 0.6, "_wb": 0.9},
}


def apply(timeline: dict) -> None:
    beats = timeline["beats"]
    if not any(b.get("light") or b.get("away") for b in beats):
        return
    fps, total = timeline["fps"], timeline["total_frames"]
    # (frame, mood, snap) changes, starting from night.
    changes = [(0, "noche", True)] + [(b["start_frame"] + round((b.get("light_at") or 0.0) * fps), b["light"], bool(b.get("light_snap")))
                                      for b in beats if b.get("light")]
    names = {n for m in MOODS.values() for n in m}

    def mult(mood: str, name: str) -> float:
        return MOODS[mood].get(name, 1.0)

    frames = list(range(total))
    curves = {n: [] for n in names}
    prev, cur, t0, length = "noche", "noche", 0, 1
    ci = 0
    for f in frames:
        while ci + 1 < len(changes) and changes[ci + 1][0] <= f:
            ci += 1
            # The new fade starts from wherever the previous one had got to.
            prev = {n: curves[n][-1] if curves[n] else 1.0 for n in names}
            cur, t0 = changes[ci][1], changes[ci][0]
            length = SNAP if changes[ci][2] else int(FADE * fps)
        k = smoothstep((f - t0) / max(1, length))
        for n in names:
            a = prev[n] if isinstance(prev, dict) else mult(prev, n)
            curves[n].append(a + (mult(cur, n) - a) * k)

    # The laptop left the room with him (beat.novato_away): its glow on the desk goes with it.
    away = [0.0] * total
    for b in beats:
        if b.get("away"):
            for f in range(b["start_frame"], min(b["end_frame"], total)):
                away[f] = 1.0
    if any(away) and "screen_light" in curves:
        curves["screen_light"] = [v * (1.0 - a) for v, a in zip(curves["screen_light"], away)]

    for n, values in curves.items():
        if n == "_wb":
            scene = bpy.context.scene
            scene.view_settings.use_white_balance = True
            bake(scene, "view_settings.white_balance_temperature", -1, frames, [6500.0 * v for v in values])
            continue
        if n == "_think":
            for mat in {s.material for o in bpy.data.objects if o.name.startswith("think_light") for s in o.material_slots if s.material}:
                mul = next((nd for nd in mat.node_tree.nodes if nd.type == "MATH" and nd.operation == "MULTIPLY"), None)
                if mul is None:
                    continue
                base = mul.inputs[1].default_value
                bake(mat.node_tree, f'nodes["{mul.name}"].inputs[1].default_value', -1, frames, [base * v for v in values])
            continue
        if n == "_fairy":
            mat = bpy.data.materials.get("fairy_bulb")
            if mat:
                sock = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
                idx = list(mat.node_tree.nodes["Principled BSDF"].inputs).index(sock)
                base = sock.default_value
                bake(mat.node_tree, f'nodes["Principled BSDF"].inputs[{idx}].default_value', -1, frames, [base * v for v in values])
            continue
        obj = bpy.data.objects.get(n)
        if obj is None or obj.type != "LIGHT":
            continue
        base = obj.data.energy
        bake(obj.data, "energy", -1, frames, [base * v for v in values])
