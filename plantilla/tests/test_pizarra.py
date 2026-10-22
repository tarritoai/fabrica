"""The chalkboard of the `mostrador` set says what the script asks (set_options "pizarra"), in chalk letters that
are plain meshes (the cloud machine has no font files), as big as fits the board; without it, the usual menu lines.
Builds the set in Blender when it is installed (blender/check_set.py)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BOARD_W = 1.3


def _blender() -> str | None:
    from reels import system

    try:
        return system.blender()
    except Exception:  # noqa: BLE001
        return shutil.which("blender")


def _build(tmp_path: Path, options: dict) -> dict:
    blender = _blender()
    if not blender:
        pytest.skip("Blender not installed here")
    out = tmp_path / "set.json"
    subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(ROOT / "blender/check_set.py"),
                    "--", str(out), "mostrador", json.dumps(options, ensure_ascii=False)], check=True,
                   capture_output=True, timeout=600)
    return json.loads(out.read_text(encoding="utf-8"))


def test_board_without_text_keeps_its_menu_lines(tmp_path):
    r = _build(tmp_path, {"variant": "cafeteria"})
    assert {f"chalk_line_{i}" for i in range(4)} <= set(r["chalk"])
    assert not any(n.startswith("chalk_text") for n in r["chalk"])
    assert len([n for n in r["chalk"] if n.startswith("pendant_bulb")]) == 3


def test_board_says_the_scripts_words(tmp_path):
    r = _build(tmp_path, {"variant": "cafeteria", "pizarra": "¡Hoy!|lo de siempre|café · 1,50 €"})
    texts = {n: v for n, v in r["chalk"].items() if n.startswith("chalk_text")}
    assert sorted(texts) == ["chalk_text_0", "chalk_text_1", "chalk_text_2"]
    assert all(v["type"] == "MESH" and v["verts"] > 50 for v in texts.values())  # real letters, not empty
    assert r["font_curves"] == 0  # converted to meshes: nothing depends on a font file
    assert not any(n.startswith("chalk_line") for n in r["chalk"])
    assert all(v["width"] <= BOARD_W - 0.1 for v in texts.values())
    zs = [texts[f"chalk_text_{i}"]["loc"][2] for i in range(3)]
    assert zs[0] > zs[1] > zs[2]  # first line on top
    board = r["chalk"]["chalkboard"]["loc"]
    assert all(abs(v["loc"][0] - board[0]) < 0.05 and v["loc"][1] < board[1] for v in texts.values())  # centred, in front


def test_long_lines_shrink_to_fit_and_only_four_lines(tmp_path):
    r = _build(tmp_path, {"variant": "cafeteria", "pizarra": "una frase larguísima que no cabe en la pizarra\n2\n3\n4\n5"})
    texts = {n: v for n, v in r["chalk"].items() if n.startswith("chalk_text")}
    assert len(texts) == 4
    assert max(v["width"] for v in texts.values()) <= BOARD_W - 0.1


def test_the_bakery_gets_a_board_only_when_the_script_writes_on_it(tmp_path):
    assert "chalkboard" not in _build(tmp_path, {"variant": "obrador"})["chalk"]
    r = _build(tmp_path, {"variant": "obrador", "pizarra": "Pan del día"})
    assert "chalkboard" in r["chalk"] and "chalk_text_0" in r["chalk"]
