"""`reels doctor` gives OS-specific fixes, never requires Homebrew outside a Mac nor an Anthropic key."""

import json

import pytest
from typer.testing import CliRunner

from reels import doctor, system
from reels.cli import app


@pytest.mark.parametrize("os_name", ["windows", "linux"])
def test_no_homebrew_outside_mac(monkeypatch, os_name):
    monkeypatch.setattr(system, "current_os", lambda: os_name)
    assert doctor.check_brew() is None
    fixes = " ".join([doctor.ffmpeg_fix(), doctor.check_rubberband().fix, doctor.check_node().fix])
    assert "brew" not in fixes


def test_linux_fixes_need_no_sudo_for_required_tools(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "linux")
    assert "sudo" not in doctor.ffmpeg_fix()
    monkeypatch.setattr(system, "find_blender", lambda: None)
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    assert "sudo" not in doctor.check_blender().fix


def test_windows_fixes_use_winget(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    assert "winget install Gyan.FFmpeg" in doctor.ffmpeg_fix()
    monkeypatch.setattr(system, "find_blender", lambda: None)
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    assert "winget install BlenderFoundation.Blender" in doctor.check_blender().fix


def test_mac_without_brew_says_install_brew_first(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "mac")
    monkeypatch.setattr(system, "find_tool", lambda names, env_var=None: None)
    assert doctor.check_brew().status == doctor.WARN
    assert "Homebrew" in doctor.ffmpeg_fix()


def test_anthropic_key_absent_is_fine():
    assert doctor.check_anthropic({}, {}).status == doctor.OK


def test_anthropic_key_in_shell_warns_about_api_billing():
    c = doctor.check_anthropic({"ANTHROPIC_API_KEY": "sk-ant-xxx"}, {})
    assert c.status == doctor.WARN and "cobrar" in c.detail


def test_anthropic_key_in_env_file_is_only_a_warning():
    c = doctor.check_anthropic({}, {"ANTHROPIC_API_KEY": "sk-ant-xxx"})
    assert c.status == doctor.WARN


@pytest.mark.parametrize("path,status", [
    (r"C:\Users\María José\OneDrive\fabrica", doctor.WARN),
    (r"C:\Users\María José\fabrica", doctor.WARN),
    (r"C:\fabrica", doctor.OK),
])
def test_windows_project_path(monkeypatch, path, status):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(doctor, "ROOT", path)
    assert doctor.check_project_path().status == status


def test_doctor_json_runs_offline():
    result = CliRunner().invoke(app, ["doctor", "--skip-api", "--json"])
    data = json.loads(result.stdout)
    assert data["os"] in {"mac", "windows", "linux"}
    names = {c["name"] for c in data["checks"]}
    assert {"Python", "ffmpeg", "Blender", "Rhubarb (labios)", "modelo de whisper", "ANTHROPIC_API_KEY"} <= names
    assert result.exit_code == (0 if data["ok"] else 1)


def test_cli_commands():
    out = CliRunner().invoke(app, ["--help"]).stdout
    for cmd in ("doctor", "humo", "descargar-modelo", "lint", "build", "render", "compose", "check"):
        assert cmd in out
    for gone in ("icloud", "semanal", "voices-ab", "ref-fetch", "ref-grid"):
        assert gone not in out


@pytest.mark.parametrize("os_name,needle", [("windows", "winget install --id Git.Git -e --scope user"),
                                            ("mac", "xcode-select --install"),
                                            ("linux", "sudo apt install openssh-client")])
def test_ssh_is_checked_for_the_cloud(monkeypatch, os_name, needle):
    """ssh and ssh-keygen (render --cloud): a warning without a Vast key, missing (falta) with one."""
    monkeypatch.setattr(system, "current_os", lambda: os_name)
    monkeypatch.setattr(system, "find_ssh_tool", lambda name: None)
    monkeypatch.delenv("VAST_API_KEY", raising=False)
    checks = doctor.check_ssh()
    assert [c.name.split()[0] for c in checks] == ["ssh", "ssh-keygen"]
    assert all(c.status == doctor.WARN and needle in c.fix for c in checks)
    monkeypatch.setenv("VAST_API_KEY", "x")
    assert all(c.status == doctor.FAIL for c in doctor.check_ssh())


def test_ssh_found_is_ok():
    if not system.find_ssh_tool("ssh"):
        pytest.skip("no ssh on this machine")
    assert doctor.check_ssh()[0].status == doctor.OK


def test_orphan_machines_are_a_failure_with_the_fix(monkeypatch):
    from reels import cloud

    monkeypatch.setenv("VAST_API_KEY", "x")
    monkeypatch.setattr(cloud, "orphans", lambda c: ([{"id": 1, "dph_total": 0.3}], []))
    check = doctor.check_vast_machines()
    assert check.status == doctor.FAIL and "cloud-cleanup" in check.fix and "0.30" in check.detail
    monkeypatch.setattr(cloud, "orphans", lambda c: ([], [{"id": 2}]))
    assert doctor.check_vast_machines().status == doctor.OK
    monkeypatch.delenv("VAST_API_KEY")
    assert doctor.check_vast_machines() is None


def test_doctor_speaks_neutral_spanish():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for rel in ("reels/cli.py", "reels/doctor.py", "reels/smoke.py", "reels/cloud.py", "curso/comprobaciones.json"):
        assert "ordenador" not in (root / rel).read_text(encoding="utf-8").lower(), rel
