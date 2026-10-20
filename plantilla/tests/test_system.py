"""Cross-platform glue (reels/system.py): every branch is tested by faking the OS, so this runs anywhere."""

import os
import subprocess
from pathlib import Path

import pytest

from reels import system
from reels.assets import ROOT


@pytest.mark.parametrize("platform,expected", [("darwin", "mac"), ("win32", "windows"), ("linux", "linux")])
def test_current_os(monkeypatch, platform, expected):
    monkeypatch.setattr(system.sys, "platform", platform)
    assert system.current_os() == expected


def test_exe_suffix_only_on_windows(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    assert system.exe("rhubarb") == "rhubarb.exe"
    assert system.exe("rhubarb.exe") == "rhubarb.exe"
    monkeypatch.setattr(system, "current_os", lambda: "mac")
    assert system.exe("rhubarb") == "rhubarb"


def test_devnull_is_the_os_one():
    assert system.DEVNULL == os.devnull


def test_project_path_is_relative_to_project_root_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert system.project_path("models/x.bin") == ROOT / "models" / "x.bin"
    assert system.project_path(tmp_path / "abs.bin") == tmp_path / "abs.bin"


def test_whisper_model_default_and_env(monkeypatch, tmp_path):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    assert system.whisper_model() == ROOT / "models" / "ggml-small.bin"
    monkeypatch.setenv("WHISPER_MODEL", "models/ggml-base.bin")
    assert system.whisper_model() == ROOT / "models" / "ggml-base.bin"
    monkeypatch.setenv("WHISPER_MODEL", str(tmp_path / "m.bin"))
    assert system.whisper_model() == tmp_path / "m.bin"


def test_paths_with_spaces_and_accents(tmp_path, monkeypatch):
    """Windows users called «María José»: a tool in such a folder is found and the path survives intact."""
    folder = tmp_path / "Users" / "María José" / "fábrica"
    folder.mkdir(parents=True)
    tool = folder / "blender"
    tool.write_text("", encoding="utf-8")
    monkeypatch.setenv("BLENDER_BIN", str(tool))
    assert system.find_blender() == str(tool)


def test_find_tool_env_var_wins_and_wrong_value_is_not_replaced(tmp_path, monkeypatch):
    fake = tmp_path / "ffmpeg"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("FFMPEG_BIN", str(fake))
    assert system.find_tool("ffmpeg", "FFMPEG_BIN") == str(fake)
    monkeypatch.setenv("FFMPEG_BIN", str(tmp_path / "nope"))
    assert system.find_tool("ffmpeg", "FFMPEG_BIN") is None
    monkeypatch.setenv("BLENDER_BIN", str(tmp_path / "nope"))
    assert system.find_blender() is None


def test_blender_candidates_per_os(monkeypatch, tmp_path):
    mac = system.blender_candidates("mac")
    assert Path("/Applications/Blender.app/Contents/MacOS/Blender") in mac

    pf = tmp_path / "Program Files"
    for v in ("4.5", "5.2"):
        exe = pf / "Blender Foundation" / f"Blender {v}" / "blender.exe"
        exe.parent.mkdir(parents=True)
        exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("ProgramFiles", str(pf))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "none"))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    win = system.blender_candidates("windows")
    assert [p.parent.name for p in win[:2]] == ["Blender 5.2", "Blender 4.5"]  # newest first

    monkeypatch.setattr(system.Path, "home", classmethod(lambda cls: tmp_path))
    opt = tmp_path / ".local" / "opt" / "blender-5.2.2-linux-x64"
    opt.mkdir(parents=True)
    (opt / "blender").write_text("", encoding="utf-8")
    linux = system.blender_candidates("linux")
    assert opt / "blender" in linux


def test_linux_tool_dirs_include_user_local_opt(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "linux")
    monkeypatch.setattr(system.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".local" / "bin").mkdir(parents=True)
    (tmp_path / ".local" / "opt" / "ffmpeg-9" / "bin").mkdir(parents=True)
    dirs = system.tool_dirs()
    assert tmp_path / ".local" / "bin" in dirs
    assert tmp_path / ".local" / "opt" / "ffmpeg-9" / "bin" in dirs


def test_setup_path_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "tool_dirs", lambda: [tmp_path])
    monkeypatch.setenv("PATH", "/usr/bin")
    system.setup_path()
    system.setup_path()
    assert os.environ["PATH"].split(os.pathsep).count(str(tmp_path)) == 1


def test_remotion_runs_node_directly_not_npx(tmp_path, monkeypatch):
    cli = tmp_path / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("", encoding="utf-8")
    monkeypatch.setattr(system, "find_tool", lambda names, env_var=None: "/x/node")
    assert system.remotion_cmd(tmp_path) == ["/x/node", str(cli)]


def test_remotion_without_node_modules_explains_npm_ci(tmp_path, monkeypatch):
    monkeypatch.setattr(system, "find_tool", lambda names, env_var=None: "/x/node")
    monkeypatch.setattr(system.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="npm ci"):
        system.remotion_cmd(tmp_path)


def test_remotion_falls_back_to_resolved_npx(tmp_path, monkeypatch):
    """On Windows `npx` is npx.cmd: only the full path from which() can be started without a shell."""
    monkeypatch.setattr(system, "find_tool", lambda names, env_var=None: None)
    monkeypatch.setattr(system.shutil, "which", lambda name: r"C:\Program Files\nodejs\npx.CMD")
    assert system.remotion_cmd(tmp_path)[0] == r"C:\Program Files\nodejs\npx.CMD"


@pytest.mark.parametrize("os_name,expected", [("mac", ["open"]), ("linux", ["xdg-open"])])
def test_open_path_uses_the_os_opener(monkeypatch, os_name, expected):
    calls = []
    monkeypatch.setattr(system, "current_os", lambda: os_name)
    monkeypatch.setattr(system.subprocess, "Popen", lambda cmd, **kw: calls.append(cmd))
    assert system.open_path("/tmp/vídeo final.mp4")
    assert calls == [[*expected, "/tmp/vídeo final.mp4"]]


def test_open_path_on_windows_uses_startfile(monkeypatch):
    opened = []
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(system.os, "startfile", lambda p: opened.append(p), raising=False)
    assert system.open_path(r"C:\fabrica\final.mp4")
    assert opened == [r"C:\fabrica\final.mp4"]


def test_open_path_never_raises(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "linux")

    def boom(*a, **k):
        raise FileNotFoundError("xdg-open")

    monkeypatch.setattr(system.subprocess, "Popen", boom)
    assert system.open_path("/x.mp4") is False


@pytest.mark.parametrize("text,expected", [
    ("ffmpeg version 9.0.2-static https://johnvansickle.com", (9, 0, 2)),
    ("ffmpeg version n7.1 Copyright (c) 2000-2024", (7, 1)),
    ("ffmpeg version 7.1-full_build-www.gyan.dev Copyright", (7, 1)),
    ("ffmpeg version 6.1.1-3ubuntu5 Copyright", (6, 1, 1)),
    ("ffmpeg version N-117000-gabc123 Copyright", None),  # git build: no number, irnorm decides
])
def test_ffmpeg_version_parsing(monkeypatch, text, expected):
    monkeypatch.setattr(system, "run_text", lambda cmd, timeout=60: text)
    assert system.ffmpeg_version("ffmpeg") == expected


def test_irnorm_detection(monkeypatch):
    monkeypatch.setattr(system, "run_text", lambda cmd, timeout=60: "Filter afir\n  irnorm <float> ...")
    assert system.ffmpeg_has_irnorm("ffmpeg")
    monkeypatch.setattr(system, "run_text", lambda cmd, timeout=60: "Filter afir\n  irgain <float> ...")
    assert not system.ffmpeg_has_irnorm("ffmpeg")


def test_run_text_decodes_utf8(tmp_path):
    import sys

    out = system.run_text([sys.executable, "-c", "import sys; sys.stdout.buffer.write('fábrica ✔'.encode('utf-8'))"])
    assert "fábrica ✔" in out


def test_keep_awake_is_best_effort(monkeypatch):
    monkeypatch.setattr(system.shutil, "which", lambda name: None)
    monkeypatch.setattr(system, "current_os", lambda: "linux")
    with system.keep_awake():
        pass


def test_real_ffmpeg_if_installed():
    """On a configured machine (and in CI after installing), the real ffmpeg must be >= 7 with irnorm."""
    path = system.find_tool("ffmpeg", "FFMPEG_BIN")
    if not path:
        pytest.skip("ffmpeg not installed here")
    assert system.ffmpeg_has_irnorm(path)
    v = system.ffmpeg_version(path)
    assert v is None or v >= system.FFMPEG_MIN


def test_real_rhubarb_supports_phonetic_recognizer_if_installed():
    """Spanish needs `-r phonetic` (the default recognizer, PocketSphinx, is English only): reels/lipsync.py uses it."""
    path = system.find_rhubarb()
    if not path:
        pytest.skip("rhubarb not installed here")
    help_text = subprocess.run([path, "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert "phonetic" in help_text.stdout + help_text.stderr


def test_tools_unpacked_from_release_zips_are_found(monkeypatch, tmp_path):
    """whisper-bin-x64.zip unpacks as Release/whisper-cli.exe: dropping the zip's folder into tools/ is enough."""
    monkeypatch.setattr(system, "TOOLS", tmp_path)
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(system.shutil, "which", lambda name: None)
    monkeypatch.delenv("WHISPER_BIN", raising=False)
    exe = tmp_path / "whisper" / "Release" / "whisper-cli.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    assert system.find_whisper() == str(exe)


def test_windows_tool_dirs_include_winget_links(monkeypatch, tmp_path):
    links = tmp_path / "Microsoft" / "WinGet" / "Links"
    links.mkdir(parents=True)
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert links in system.tool_dirs()


def test_every_render_keeps_the_computer_awake():
    """Each Blender render (full, preview, animatic, benchmark) and the cloud render run inside keep_awake."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent

    def inside_keep_awake(lines, i):
        return "keep_awake" in "\n".join(lines[max(0, i - 6):i + 1])

    build = (root / "reels" / "build.py").read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(build):
        if '"blender/render.py"' in line:
            assert inside_keep_awake(build, i), f"build.py:{i + 1} renders without keep_awake"
    smoke = (root / "reels" / "smoke.py").read_text(encoding="utf-8").splitlines()
    calls = [i for i, line in enumerate(smoke) if "= _render_frames(blend" in line]
    assert calls and all(inside_keep_awake(smoke, i) for i in calls)
    cli = (root / "reels" / "cli.py").read_text(encoding="utf-8")
    assert re.search(r"keep_awake\([^)]*\):\s*\n\s*console\.print\([^\n]*cloud_mod\.render", cli)
