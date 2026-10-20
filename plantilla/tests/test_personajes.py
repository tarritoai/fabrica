"""Characters as data (personajes/<id>/personaje.json), the cast by role and the object-with-a-face builder."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from reels import cast, schema
from reels.assets import character, character_file, known_characters
from reels.schema import Action, Character, Emotion, Episode, Set

ROOT = Path(__file__).resolve().parent.parent
PERSONAJES = sorted(p.parent.name for p in (ROOT / "personajes").glob("*/personaje.json"))
FORMS = re.findall(r'^    "(\w+)": form_\w+', (ROOT / "blender/rigs/thing.py").read_text(encoding="utf-8"), re.M) + \
    re.findall(r', "(\w+)": form_\w+', (ROOT / "blender/rigs/thing.py").read_text(encoding="utf-8"))
SHAPES = re.findall(r'"(\w+)": \w+[,}]', re.search(r"BUILDERS = \{(.*?)\}", (ROOT / "blender/rigs/placeholders.py")
                                                    .read_text(encoding="utf-8")).group(1) + "}")


@pytest.fixture(autouse=True)
def _no_active_cast():
    cast.activate({})
    yield
    cast.activate({})


def script(**kw) -> dict:
    """A minimal valid script, with `characters` and beats overridable."""
    data = json.loads((ROOT / "assets/humo/script.json").read_text(encoding="utf-8"))
    data.update(kw)
    return data


# --- personaje.json files -------------------------------------------------------------------------------------

def test_the_shipped_characters_are_there():
    assert {"lucio", "estudiante", "moka", "barista"} <= set(PERSONAJES)
    assert {"lucio", "estudiante", "moka", "barista"} <= known_characters()


@pytest.mark.parametrize("cid", PERSONAJES)
def test_personaje_files_are_complete(cid):
    meta = character_file(cid)
    assert meta["id"] == cid and meta["display_name"]
    assert meta["role"] in ("humano", "cosa")
    assert set(meta["emotions"]) <= {e.value for e in Emotion}
    assert set(meta["actions"]) <= {a.value for a in Action} and "idle" in meta["actions"]
    assert meta["placeholder"]["shape"] in SHAPES
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", meta["subtitle_color"])
    assert "voice_id" in meta["voice"]
    if meta["placeholder"]["shape"] == "object":
        assert meta["object"]["form"] in FORMS
        for color in (meta["object"].get("colors") or {}).values():
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", color)


def test_every_form_is_registered():
    assert set(FORMS) == {"lampara", "cafetera", "taza", "olla", "cajita", "zapatilla", "bloque", "cilindro", "bola", "cono"}


def test_new_characters_join_the_character_enum():
    for cid in PERSONAJES:
        assert Character(cid).value == cid


# --- cast by role -----------------------------------------------------------------------------------------------

def test_listing_characters_fills_the_roles():
    ep = Episode.model_validate(script(characters=["estudiante", "lucio"]))
    assert ep.reparto == {"humano": "estudiante", "cosa": "lucio"}
    assert [c.value for c in ep.characters] == ["novato", "claude"]
    assert ep.players() == {"novato": "estudiante", "claude": "lucio"}


def test_role_names_reach_the_players():
    ep = Episode.model_validate(script(characters=["barista", "moka"]))
    assert ep.beats[0].speaker == Character.claude  # the humo script speaks as "cosa"
    assert character("claude")["display_name"] == "Moka"  # active cast: the slot's file is the player's
    assert character("novato")["display_name"] == "Barista"


def test_names_of_the_players_work_in_beats():
    data = script(characters=["estudiante", "lucio"])
    for b in data["beats"]:
        if b["speaker"]:
            b["speaker"] = "lucio"
    data["beats"][-1]["reactor"] = "estudiante"
    ep = Episode.model_validate(data)
    assert {b.speaker for b in ep.beats if b.speaker} == {Character.claude}
    assert ep.beats[-1].reactor == Character.novato


def test_script_reparto_wins():
    ep = Episode.model_validate(script(characters=["humano", "cosa"], reparto={"humano": "estudiante", "cosa": "lucio"}))
    assert ep.players() == {"novato": "estudiante", "claude": "lucio"}


def test_default_cast_still_plays_the_template_characters():
    ep = Episode.model_validate(script())
    assert ep.reparto == {"humano": "prota", "cosa": "taza"}
    assert character("claude")["display_name"] == "Taza"
    assert character("novato")["display_name"] == "Prota"


def test_a_listed_slot_keeps_extras_as_themselves():
    """With the lead already cast, another human is an extra (the sofa), not a replacement."""
    ep = Episode.model_validate(script(characters=["novato", "claude", "estudiante"]))
    assert [c.value for c in ep.characters] == ["novato", "claude", "estudiante"]
    assert ep.reparto == {"humano": "prota", "cosa": "taza"}


def test_a_thing_alone_in_a_generic_set():
    data = script(characters=["moka"], set="mostrador", set_options={"variant": "obrador"})
    ep = Episode.model_validate(data)
    assert ep.reparto == {"cosa": "moka"} and ep.set == Set.mostrador
    assert ep.set_options == {"variant": "obrador"}


def test_desk_set_still_needs_a_human():
    with pytest.raises(Exception, match="built around"):
        Episode.model_validate(script(characters=["moka"]))


@pytest.mark.parametrize("reparto,msg", [
    ({"humano": "lucio"}, "cannot play|no puede hacer"),
    ({"cosa": "nadie"}, "no es ningún personaje"),
    ({"villano": "lucio"}, "no existe"),
])
def test_bad_script_reparto_explains_itself(reparto, msg):
    with pytest.raises(Exception, match=msg):
        Episode.model_validate(script(characters=["humano", "cosa"], reparto=reparto))


def test_project_file_can_pick_players():
    known = {"novato", "claude", "lucio", "estudiante", "hugo"}
    proj = cast.parse_project({"humano": {"personaje": "estudiante", "nombre": "ana"}, "cosa": "lucio"}, known)
    assert proj.players == {"novato": "estudiante", "claude": "lucio"}
    assert proj.aliases["ana"] == "novato" and proj.aliases["estudiante"] == "novato" and proj.aliases["lucio"] == "claude"
    with pytest.raises(cast.CastError, match="no existe"):
        cast.parse_project({"cosa": {"personaje": "flexo"}}, known)


def test_saved_scripts_reload_the_same_way():
    ep = Episode.model_validate(script(characters=["estudiante", "lucio"]))
    again = Episode.model_validate(json.loads(ep.model_dump_json()))
    assert again.players() == ep.players() and again.characters == ep.characters


def test_kinds():
    assert cast.kind_of("estudiante") == "humano" and cast.kind_of("novato") == "humano"
    assert cast.kind_of("lucio") == "cosa" and cast.kind_of("claude") == "cosa"
    assert cast.kind_of("mama") is None and cast.kind_of("nadie") is None


# --- examples ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("slug", ["lampara-de-las-tres", "cafeteria-moka"])
def test_examples_validate_and_lint_clean(slug, tmp_path, monkeypatch):
    import reels.assets as assets
    from reels import ejemplos
    from reels.lint import lint

    monkeypatch.setattr(assets, "EPISODES", tmp_path)
    out = ejemplos.prepare(slug)
    assert (out / "audio" / "beat_01.mp3").exists() and (out / "audio" / "beat_01.json").exists()
    ep = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    assert set(ep.reparto) == {"humano", "cosa"}
    assert ep.beats[-1].speaker is None
    assert not [i for i in lint(slug) if i.level == "ERROR"]


def test_writer_knows_any_thing_can_take_closeup_ai():
    from reels.writer import _extra_checks

    ep = Episode.model_validate(script(characters=["barista", "moka"], set="mostrador"))
    assert not [e for e in _extra_checks(ep) if "closeup_ai" in e]


# --- the builder, in Blender (skipped where Blender is not installed) -------------------------------------------

def _blender() -> str | None:
    from reels import system

    try:
        return system.blender()
    except Exception:  # noqa: BLE001
        return shutil.which("blender")


@pytest.fixture(scope="module")
def rig_report(tmp_path_factory):
    blender = _blender()
    if not blender or not Path(blender).exists() and not shutil.which(blender):
        pytest.skip("Blender not installed here")
    out = tmp_path_factory.mktemp("rig") / "rig.json"
    ids = [*PERSONAJES, *(f"@{f}" for f in FORMS)]
    subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(ROOT / "blender/check_rig.py"), "--",
                    str(out), *ids], check=True, capture_output=True, timeout=900)
    return json.loads(out.read_text(encoding="utf-8"))


FACE = ["ctrl_body", "ctrl_head", "eye_L", "eye_R", "brow_L", "brow_R", "mouth_rest", "mouth_M", "mouth_E", "mouth_A", "mouth_O"]


@pytest.mark.parametrize("form", FORMS)
def test_every_form_builds_the_whole_face(rig_report, form):
    r = rig_report[f"@{form}"]
    missing = [p for p in [*FACE, "eyelid_L", "eyelid_R", "mouth_smile", "ctrl_arm_L", "ctrl_arm_R"] if not r["parts"][p]]
    if form in ("lampara", "zapatilla"):  # no stubby arms: the lamp's own arm acts, the shoe has laces
        missing = [p for p in missing if not p.startswith("ctrl_arm")]
    assert not missing
    assert r["min_z"] > -0.01  # stands on the floor, nothing below it
    if form != "lampara":  # no steam out of a lamp
        assert "steam" in r["acting"]


def test_acting_parts_and_light(rig_report):
    assert {"arm_lower", "arm_upper", "arm_comp", "shade_tilt"} <= set(rig_report["lucio"]["acting"])
    lamp = rig_report["lucio"]["parts"]
    assert all(lamp[p] for p in ("rod_lower_L", "rod_upper_R", "spring_lower", "spring_upper", "knob_elbow"))
    assert rig_report["lucio"]["parts"]["lamp_bulb"] and {"lamp_spot", "lamp_fill"} <= set(rig_report["lucio"]["emissive_lights"])
    assert "lid_pivot" in rig_report["moka"]["acting"]
    for form in ("olla", "cajita", "cafetera"):
        assert "lid_pivot" in rig_report[f"@{form}"]["acting"]
    assert "laces_bow" in rig_report["@zapatilla"]["acting"]


def test_humans_from_data_keep_the_human_rig(rig_report):
    for cid in ("estudiante", "barista"):
        parts = rig_report[cid]["parts"]
        assert all(parts[p] for p in FACE) and not parts["eyelid_L"]


def test_schema_lists_the_generic_sets():
    assert {"estudio", "mostrador", "exterior"} <= {s.value for s in Set}
    assert not schema.SET_CAST["mostrador"].requires
