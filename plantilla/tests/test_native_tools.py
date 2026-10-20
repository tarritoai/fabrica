"""Native tools on Windows with a project in a folder with accents («C:\\Users\\María José\\mi fábrica»).

Seen in CI on windows-latest: Rhubarb 1.14 with -q writes nothing to stdout (exit code 0, so the old code failed
with «Expecting value»); its .exe cannot find res/ from a folder with accents; whisper.cpp crashes on an absolute
path with accents. The OS is faked, and the tools are small Python scripts, so this runs anywhere."""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from reels import lipsync, system

posix_only = pytest.mark.skipif(os.name == "nt", reason="the fake tools are #! scripts")


def _script(path: Path, body: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\nimport json, os, shutil, sys\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


# --- native_path --------------------------------------------------------------------------------------------------


def test_native_path_untouched_outside_windows(monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "linux")
    assert system.native_path("/home/María José/a.wav", "/home/María José") == "/home/María José/a.wav"


def test_native_path_on_windows_is_relative_when_it_has_accents(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    project = tmp_path / "María José" / "mi fábrica"
    assert system.native_path(tmp_path / "fabrica" / "a.wav", project) == str(tmp_path / "fabrica" / "a.wav")
    wav = project / "episodes" / "humo" / "audio" / "beat_01.wav"
    assert system.native_path(wav, project) == os.path.join("episodes", "humo", "audio", "beat_01.wav")
    assert system.native_path(wav, wav.parent) == "beat_01.wav"


def test_native_path_explains_a_file_it_cannot_name(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    with pytest.raises(RuntimeError, match="tildes o eñes"):
        system.native_path(tmp_path / "Música" / "canción.wav", tmp_path / "fabrica")


# --- ascii_tool (Rhubarb's copy) ------------------------------------------------------------------------------------


def _rhubarb_folder(root: Path) -> Path:
    folder = root / "María José" / "mi fábrica" / "tools" / "rhubarb-1.14.0"
    (folder / "res" / "sphinx").mkdir(parents=True)
    (folder / "res" / "sphinx" / "mdef").write_text("model", encoding="utf-8")
    (folder / "tests").mkdir()
    (folder / "tests" / "big.wav").write_text("not needed", encoding="utf-8")
    (folder / "rhubarb.exe").write_text("exe", encoding="utf-8")
    (folder / "helper.dll").write_text("dll", encoding="utf-8")
    return folder


def test_ascii_tool_untouched_when_path_is_ascii_or_not_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    assert system.ascii_tool(r"C:\fabrica\tools\rhubarb-1.14.0\rhubarb.exe") == r"C:\fabrica\tools\rhubarb-1.14.0\rhubarb.exe"
    monkeypatch.setattr(system, "current_os", lambda: "mac")
    assert system.ascii_tool("/Users/María/fábrica/rhubarb") == "/Users/María/fábrica/rhubarb"


def test_ascii_tool_copies_exe_dlls_and_res_once(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    safe = tmp_path / "Public" / "fabrica-tools"
    monkeypatch.setattr(system, "ascii_base_candidates", lambda: [tmp_path / "Pública" / "fabrica-tools", safe])
    folder = _rhubarb_folder(tmp_path)

    copy = Path(system.ascii_tool(str(folder / "rhubarb.exe"), extras=("res",)))
    assert copy.parent.parent == safe and str(copy).isascii()
    assert copy.read_text(encoding="utf-8") == "exe"
    assert (copy.parent / "helper.dll").exists()
    assert (copy.parent / "res" / "sphinx" / "mdef").read_text(encoding="utf-8") == "model"
    assert not (copy.parent / "tests").exists()  # 160 MB of Rhubarb's own tests stay behind

    (copy.parent / "res" / "sphinx" / "mdef").write_text("touched", encoding="utf-8")
    assert system.ascii_tool(str(folder / "rhubarb.exe"), extras=("res",)) == str(copy)
    assert (copy.parent / "res" / "sphinx" / "mdef").read_text(encoding="utf-8") == "touched"  # not copied again

    (folder / "rhubarb.exe").write_text("new version", encoding="utf-8")
    assert system.ascii_tool(str(folder / "rhubarb.exe"), extras=("res",)) == str(copy)
    assert copy.read_text(encoding="utf-8") == "new version"
    assert (copy.parent / "res" / "sphinx" / "mdef").read_text(encoding="utf-8") == "model"
    assert not list(safe.glob("*.part-*"))


def test_ascii_base_skips_folders_with_accents(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "ascii_base_candidates", lambda: [tmp_path / "Pública", tmp_path / "ok"])
    assert system.ascii_base() == tmp_path / "ok"
    monkeypatch.setattr(system, "ascii_base_candidates", lambda: [tmp_path / "Pública"])
    with pytest.raises(RuntimeError, match="C:\\\\fabrica"):
        system.ascii_base()


def test_ascii_base_candidates_are_writable_without_admin(monkeypatch):
    monkeypatch.setenv("PUBLIC", r"C:\Users\Public")
    monkeypatch.setenv("ProgramData", r"C:\ProgramData")
    names = [str(p) for p in system.ascii_base_candidates()]
    assert names[0].startswith(r"C:\Users\Public") and names[1].startswith(r"C:\ProgramData")


# --- run_tool: plain Spanish errors ----------------------------------------------------------------------------------


def test_run_tool_names_the_tool_and_the_reason():
    code = "import sys; sys.stderr.write('Progress\\nError: cannot open file\\n'); sys.exit(3)"
    with pytest.raises(RuntimeError) as e:
        system.run_tool([sys.executable, "-c", code], "Rhubarb (los labios)")
    assert "Rhubarb (los labios) ha fallado (código 3)" in str(e.value)
    assert "cannot open file" in str(e.value)


def test_run_tool_shows_windows_crash_codes_in_hex(monkeypatch):
    class Done:
        returncode, stdout, stderr = 3221226505, "", ""

    monkeypatch.setattr(system.subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(RuntimeError, match="0xC0000409"):
        system.run_tool(["whisper-cli"], "whisper")


def test_run_tool_missing_program():
    with pytest.raises(RuntimeError, match="reels doctor"):
        system.run_tool(["/no/such/tool-xyz"], "Rhubarb")


# --- Rhubarb end to end (fake rhubarb and ffmpeg) -------------------------------------------------------------------

FAKE_FFMPEG = "shutil.copy(sys.argv[sys.argv.index('-i') + 1], sys.argv[-1])"
# Like Rhubarb 1.14 on Windows: with -q, nothing on stdout; the result only goes to the -o file.
FAKE_RHUBARB = """
args = sys.argv[1:]
open(os.path.join(os.environ['FAKE_LOG']), 'w').write(json.dumps({'cwd': os.getcwd(), 'args': args}))
assert os.path.exists(args[-1]), 'no wav'
assert open(args[args.index('--dialogFile') + 1], encoding='utf-8').read() == 'Hola. Soy Tarrito.'
cues = {'mouthCues': [{'start': 0.0, 'end': 0.2, 'value': 'X'}, {'start': 0.2, 'end': 0.5, 'value': 'D'}]}
open(args[args.index('-o') + 1], 'w').write(json.dumps(cues))
"""


@pytest.fixture
def clip(tmp_path, monkeypatch):
    audio = tmp_path / "María José" / "mi fábrica" / "episodes" / "humo" / "audio"
    audio.mkdir(parents=True)
    wav = audio / "beat_01.wav"
    wav.write_bytes(b"RIFF")
    monkeypatch.setattr(system, "ffmpeg", lambda: _script(tmp_path / "bin" / "ffmpeg", FAKE_FFMPEG))
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "rhubarb.log"))
    return wav


@posix_only
def test_cues_read_from_the_output_file_not_stdout(clip, tmp_path, monkeypatch):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(lipsync, "rhubarb_bin", lambda: _script(tmp_path / "bin" / "rhubarb", FAKE_RHUBARB))
    cues = lipsync.cues_for(clip, "Hola. Soy Tarrito.")
    assert cues == [{"start": 0.0, "end": 0.2, "viseme": "mouth_rest"}, {"start": 0.2, "end": 0.5, "viseme": "mouth_A"}]
    seen = json.loads((tmp_path / "rhubarb.log").read_text())
    assert Path(seen["cwd"]) == clip.parent
    assert all(a.isascii() for a in seen["args"]), seen["args"]  # never the project's path
    assert sorted(p.name for p in clip.parent.iterdir()) == ["beat_01.txt", "beat_01.visemes.json", "beat_01.wav"]


@posix_only
def test_rhubarb_that_says_nothing_gets_a_clear_error(clip, tmp_path, monkeypatch):
    monkeypatch.setattr(lipsync, "rhubarb_bin", lambda: _script(tmp_path / "bin" / "rhubarb", "pass"))
    with pytest.raises(RuntimeError, match="Rhubarb \\(los labios\\) no ha devuelto nada para beat_01.wav") as e:
        lipsync.cues_for(clip, "Hola. Soy Tarrito.")
    assert "Expecting value" not in str(e.value)


@posix_only
def test_rhubarb_failure_says_why(clip, tmp_path, monkeypatch):
    body = "sys.stderr.write('[Fatal] Could not determine path of bin directory.\\n'); sys.exit(1)"
    monkeypatch.setattr(lipsync, "rhubarb_bin", lambda: _script(tmp_path / "bin" / "rhubarb", body))
    with pytest.raises(RuntimeError, match="Rhubarb \\(los labios\\) con beat_01.wav ha fallado .*bin directory"):
        lipsync.cues_for(clip, "Hola. Soy Tarrito.")
    assert not clip.with_suffix(".lift.wav").exists()


# --- whisper -------------------------------------------------------------------------------------------------------


@posix_only
def test_whisper_runs_from_the_project_with_relative_paths(monkeypatch, tmp_path):
    project = tmp_path / "María José" / "mi fábrica"
    (project / "models").mkdir(parents=True)
    (project / "models" / "ggml-small.bin").write_bytes(b"m")
    wav = project / "episodes" / "humo" / "renders" / "_check.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"RIFF")
    body = "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:]}))"
    monkeypatch.setattr(system, "ROOT", project)
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(system, "whisper", lambda: _script(tmp_path / "bin" / "whisper-cli", body))
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    seen = json.loads(system.run_whisper(["-l", "es", "-nt", "-np"], wav).stdout)
    assert Path(seen["cwd"]) == project
    assert seen["args"] == ["-m", os.path.join("models", "ggml-small.bin"), "-l", "es", "-nt", "-np",
                            os.path.join("episodes", "humo", "renders", "_check.wav")]


def test_whisper_without_model_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "whisper", lambda: "whisper-cli")
    monkeypatch.setenv("WHISPER_MODEL", str(tmp_path / "none.bin"))
    with pytest.raises(RuntimeError, match="falta el modelo de whisper"):
        system.run_whisper([], tmp_path / "a.wav")
