"""The cast alias layer (reparto.json), the script schema and the free lint keep working together."""

import json
from pathlib import Path

import pytest

from reels import cast
from reels.schema import Character, Episode

ROOT = Path(__file__).resolve().parent.parent
KNOWN = {"prota", "taza", "hugo", "chica", "mama"}


def test_default_cast_file_is_valid():
    aliases = cast.parse(json.loads((ROOT / "reparto.json").read_text(encoding="utf-8")), KNOWN)
    assert aliases["humano"] == "novato" and aliases["cosa"] == "claude"
    assert aliases["prota"] == "novato" and aliases["taza"] == "claude"
    assert cast.parse_project(json.loads((ROOT / "reparto.json").read_text(encoding="utf-8")), KNOWN).players == {
        "novato": "prota", "claude": "taza"}


def test_default_cast_without_file_is_the_neutral_pair():
    """No reparto.json: the template's neutral lead and its mug (never the brand's jar)."""
    assert cast.default_players(KNOWN) == {"novato": "prota", "claude": "taza"}
    # A brand pack that brings folders named like the slots keeps its own.
    assert cast.default_players(KNOWN | {"novato", "claude"}) == {"novato": "novato", "claude": "claude"}


def test_student_names(monkeypatch):
    aliases = cast.parse({"humano": {"nombre": "lucia"}, "cosa": {"nombre": "flexo"}, "otros": {"compi": "hugo"}}, KNOWN)
    assert aliases["lucia"] == "novato" and aliases["flexo"] == "claude" and aliases["compi"] == "hugo"


@pytest.mark.parametrize("data,msg", [
    ({"humano": {"nombre": "Lucía"}}, "minúsculas"),
    ({"humano": {"nombre": "hugo"}}, "ya es otro personaje"),
    ({"humano": {"nombre": "x"}, "cosa": {"nombre": "x"}}, "repetido"),
    ({"otros": {"compi": "nadie"}}, "no existe"),
    ({"humano": {"nombre": "lucia", "interno": "lucia"}}, "interno"),
])
def test_bad_cast_files_explain_themselves(data, msg):
    with pytest.raises(cast.CastError, match=msg):
        cast.parse(data, KNOWN)


def test_resolve_script_translates_names_cameras_and_fields(monkeypatch):
    monkeypatch.setattr(cast, "aliases", lambda: {"humano": "novato", "cosa": "claude", "lucia": "novato", "flexo": "claude"})
    raw = {"characters": ["lucia", "flexo"], "beats": [
        {"speaker": "flexo", "camera": "closeup_cosa", "cut_camera": "closeup_humano", "gaze": "lucia",
         "humano_fuera": True, "event": {"component": "PhoneCall", "props": {"owner": "lucia"}}},
        {"speaker": None, "reactor": "lucia", "camera": "two_shot"},
    ]}
    out = cast.resolve_script(raw)
    assert out["characters"] == ["novato", "claude"]
    b1, b2 = out["beats"]
    assert (b1["speaker"], b1["camera"], b1["cut_camera"], b1["gaze"]) == ("claude", "closeup_ai", "closeup_novato", "novato")
    assert b1["novato_away"] is True and "humano_fuera" not in b1
    assert b1["event"]["props"]["owner"] == "novato"
    assert b2["reactor"] == "novato"
    assert raw["characters"] == ["lucia", "flexo"]  # the input is not modified


def test_humo_script_validates_with_role_names(humo_script):
    ep = Episode.model_validate(humo_script)
    assert ep.characters == [Character.novato, Character.claude]
    assert ep.beats[0].speaker == Character.claude
    assert ep.beats[0].camera.value == "closeup_ai"


def test_old_internal_ids_still_validate(humo_script):
    humo_script["characters"] = ["novato", "claude"]
    for b in humo_script["beats"]:
        if b["speaker"]:
            b["speaker"] = "claude"
    assert Episode.model_validate_json(json.dumps(humo_script)).beats[1].speaker == Character.claude


def test_json_path_goes_through_the_alias_layer(humo_script):
    """`reels` loads scripts with model_validate_json: the before-validator must see the parsed dict there too."""
    ep = Episode.model_validate_json(json.dumps(humo_script, ensure_ascii=False))
    assert ep.beats[0].speaker == Character.claude


def test_schema_still_rejects_bad_scripts(humo_script):
    humo_script["beats"][0]["camera"] = "dron_volando"
    with pytest.raises(Exception, match="camera"):
        Episode.model_validate(humo_script)
    humo_script["beats"][0]["camera"] = "two_shot"
    humo_script["characters"] = ["cosa"]
    with pytest.raises(Exception, match="role humano"):
        Episode.model_validate(humo_script)


def test_lint_runs_on_the_smoke_episode(episode_in_tmp, humo_script):
    from reels.lint import lint

    episode_in_tmp("humo", humo_script, audio_from=ROOT / "assets" / "humo" / "audio")
    issues = lint("humo")
    assert not [i for i in issues if i.level == "ERROR"]
    assert any("tests" in i.msg for i in issues)  # warnings still reach the user


def test_lint_blocks_a_silent_opening(episode_in_tmp, humo_script):
    from reels.lint import lint

    humo_script["beats"] = humo_script["beats"][2:]  # starts with the mute beat
    episode_in_tmp("mudo", humo_script)
    assert any(i.level == "ERROR" for i in lint("mudo"))
