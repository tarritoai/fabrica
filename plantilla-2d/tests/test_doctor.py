"""The 2D doctor: no Blender, no Rhubarb, no graphics card; plain fixes for each OS; JSON for the installer."""

import json

import pytest
from typer.testing import CliRunner

from reels import doctor, system
from reels.cli import app


def test_no_3d_tools_are_checked(monkeypatch):
    names = [c.name for _, cs in doctor.collect(skip_api=True) for c in cs]
    assert not [n for n in names if any(k in n.lower() for k in ("blender", "rhubarb", "vast", "ssh", "muebles"))]
    assert any(n.startswith("ffmpeg") for n in names) and any("Remotion" in n for n in names)


@pytest.mark.parametrize("os_name", ["windows", "linux"])
def test_no_homebrew_outside_mac(monkeypatch, os_name):
    monkeypatch.setattr(system, "current_os", lambda: os_name)
    assert doctor.check_brew() is None
    assert "brew" not in doctor.ffmpeg_fix()


def test_doctor_json_shape():
    r = CliRunner().invoke(app, ["doctor", "--skip-api", "--json"])
    data = json.loads(r.stdout[r.stdout.index("{"):])
    assert set(data) == {"os", "ok", "checks"} and data["checks"]
    assert r.exit_code == (0 if data["ok"] else 1)


def test_check_reads_whisper_word_times(monkeypatch, tmp_path):
    from reels import check

    assert check.missing_words("Ve un gigante… y es un molino.", "ve un gig ante y es un") == ["molino"]
    line = "[00:00:02.040 --> 00:00:02.200]  Ve"
    assert check._LINE.match(line).group(7) == "Ve"
