"""The 2D contract: the shipped scripts validate and lint clean; lint catches what would only show after paying."""

import copy
import json

import pytest

from conftest import EXAMPLE, HUMO, fake_voice
from reels.lint import known_pieces, lint
from reels.schema import Episode


@pytest.mark.parametrize("folder", [EXAMPLE, HUMO], ids=["quijote-gafas", "humo"])
def test_shipped_scripts_validate(folder):
    Episode.model_validate_json((folder / "script.json").read_text(encoding="utf-8"))


def test_example_lints_clean(episodes_tmp, example_script):
    episodes_tmp("quijote-gafas", example_script)
    errors = [i for i in lint("quijote-gafas") if i.level == "ERROR"]
    assert errors == []


def test_generic_and_episode_pieces_are_known():
    names = known_pieces("quijote-gafas")
    assert {"Persona", "Cosa", "Objeto", "Campo", "Interior", "Ciudad", "Mar", "Trama", "Papel", "Noche"} <= names
    assert {"Quijote", "Molino", "LaMancha"} <= names
    assert "Quijote" in known_pieces("quijote-gafas-b")  # the B hook uses the A's pieces
    assert "Quijote" not in known_pieces("otro")


def test_lint_catches_anchor_actor_and_piece(episodes_tmp, example_script):
    bad = copy.deepcopy(example_script)
    bad["beats"][1]["events"][0]["at"] = "dragón"
    bad["beats"][1]["events"][1]["actor"] = "nadie"
    bad["beats"][2]["shot"]["actors"][0]["piece"] = "Dragon"
    episodes_tmp("quijote-gafas", bad)
    msgs = " | ".join(i.msg for i in lint("quijote-gafas") if i.level == "ERROR")
    assert "dragón" in msgs and "nadie" in msgs and "Dragon" in msgs


def test_slug_must_match_folder(episodes_tmp, example_script):
    episodes_tmp("otra-cosa", example_script)
    assert any("slug" in i.msg for i in lint("otra-cosa") if i.level == "ERROR")


def test_unknown_event_type_and_missing_fields_are_schema_errors(example_script):
    bad = copy.deepcopy(example_script)
    bad["beats"][1]["events"].append({"type": "explota", "at": "molino"})
    with pytest.raises(ValueError):
        Episode.model_validate(bad)
    bad = copy.deepcopy(example_script)
    bad["beats"][1]["events"].append({"type": "stamp", "at": "molino"})
    with pytest.raises(ValueError, match="text"):
        Episode.model_validate(bad)


def test_first_beat_opens_a_shot(example_script):
    bad = copy.deepcopy(example_script)
    bad["beats"][0]["shot"] = None
    with pytest.raises(ValueError, match="plano"):
        Episode.model_validate(bad)


def test_lint_reads_the_voice(episodes_tmp, example_script):
    voice = fake_voice(example_script)
    voice["takes"][0]["words"] = [w for w in voice["takes"][0]["words"] if w["beat"] != 3]
    episodes_tmp("quijote-gafas", example_script, voice)
    assert any("no tienen voz" in i.msg for i in lint("quijote-gafas"))


def test_every_piece_documented():
    """Each generic piece and background has a row in docs/piezas.md (what the script writer reads)."""
    from conftest import ROOT

    doc = (ROOT / "docs" / "piezas.md").read_text(encoding="utf-8")
    for name in ("Campo", "Interior", "Ciudad", "Mar", "Noche", "Trama", "Papel", "Persona", "Cosa", "Objeto"):
        assert f"`{name}`" in doc
    from reels.schema import EVENT_TYPES

    for t in EVENT_TYPES:
        assert f"`{t}`" in doc, t
    assert json.loads((ROOT / "assets" / "music" / "music.json").read_text(encoding="utf-8"))
