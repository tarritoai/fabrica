"""The template is brand-neutral: neutral default cast and room, no clay jar and no floating island inside it,
and the lamp's arm reads as an articulated metal arm."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from reels import cast
from reels.schema import Episode, Set

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _no_active_cast():
    cast.activate({})
    yield
    cast.activate({})


def test_default_set_is_the_neutral_room():
    assert Episode.model_fields["set"].default == Set.habitacion
    assert "mundo" not in {s.value for s in Set}  # the original series' world lives in the brand pack


def test_brand_pieces_are_not_in_the_template():
    assert not (ROOT / "blender/rigs/ceramic.py").exists()
    assert not (ROOT / "blender/mundo.py").exists() and not (ROOT / "blender/world_proto.py").exists()
    for brand in ("claude", "novato", "chatgpt"):
        assert not (ROOT / "assets/characters" / brand).exists()
    assert '"ceramic"' not in (ROOT / "blender/rigs/placeholders.py").read_text(encoding="utf-8").split("BUILDERS = {")[1].split("}")[0]


def test_default_cast_is_a_person_and_a_mug():
    data = json.loads((ROOT / "reparto.json").read_text(encoding="utf-8"))
    assert data["humano"]["personaje"] == "prota" and data["cosa"]["personaje"] == "taza"
    taza = json.loads((ROOT / "assets/characters/taza/character.json").read_text(encoding="utf-8"))
    assert taza["placeholder"]["shape"] == "object" and taza["object"]["form"] == "taza"


def test_humo_is_neutral(humo_script):
    ep = Episode.model_validate(humo_script)
    assert ep.set == Set.habitacion
    assert ep.reparto == {"humano": "prota", "cosa": "taza"}
    text = json.dumps(humo_script, ensure_ascii=False).lower()
    assert "tarrito" not in text and "tarro" not in text


def test_older_scripts_with_the_old_room_still_validate(humo_script):
    humo_script["set"] = "escritorio_noche"
    assert Episode.model_validate(humo_script).set.value == "escritorio_noche"


def test_lamp_arm_is_metal_with_springs():
    src = (ROOT / "blender/rigs/thing.py").read_text(encoding="utf-8")
    assert '"rod": "metal"' in src and '"spring": "metal"' in src and "arm_comp" in src


def _blender() -> str | None:
    from reels import system

    try:
        return system.blender()
    except Exception:  # noqa: BLE001
        return shutil.which("blender")


@pytest.mark.parametrize("options", [{}, {"window": "dia", "wall": "#9bb59a", "sofa": True}])
def test_room_builds_without_brand_dressing(tmp_path, options):
    blender = _blender()
    if not blender or not Path(blender).exists() and not shutil.which(blender):
        pytest.skip("Blender not installed here")
    out = tmp_path / "set.json"
    subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(ROOT / "blender/check_set.py"), "--",
                    str(out), "habitacion", json.dumps(options)], check=True, capture_output=True, timeout=600)
    r = json.loads(out.read_text(encoding="utf-8"))
    names = " ".join(r["objects"]).lower()
    for brand in ("galaxy", "island", "fairy", "planet", "crystal", "brick", "rock"):
        assert brand not in names, brand
    assert {"left", "right", "laptop", "front", "sofa"} <= set(r["slots"])
    assert {"laptop", "phone_spot", "copy_spots", "cameras"} <= set(r["anchors"])
    assert {"lamp_key", "lamp_light", "room_fill", "moon_rim", "screen_light"} <= set(r["lights"])
    assert any(n.startswith("city_block") for n in r["objects"])
    if options.get("window") == "dia":
        assert r["world_color"][2] > 0.3  # a blue day sky, not the night
