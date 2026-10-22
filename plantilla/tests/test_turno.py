"""The night shift (.claude/skills/turno-de-noche/turno.py): with `--cloud` the final clean-up of rented machines
always runs, also when a step fails, and the morning report says what it found."""

import argparse
import importlib.util
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _module():
    spec = importlib.util.spec_from_file_location("turno", ROOT / ".claude" / "skills" / "turno-de-noche" / "turno.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cloud_shift_cleans_up_even_when_the_render_fails(tmp_path, monkeypatch):
    mod = _module()
    monkeypatch.setattr(mod, "ROOT", tmp_path)  # it prints paths relative to the project
    monkeypatch.setattr(mod, "PUBLISH", tmp_path / "publicar")
    monkeypatch.setattr(mod, "EPISODES", tmp_path / "episodes")
    (tmp_path / "episodes" / "mi-reel" / "audio").mkdir(parents=True)
    (tmp_path / "episodes" / "mi-reel" / "script.json").write_text("{}", encoding="utf-8")
    (tmp_path / "episodes" / "mi-reel" / "audio" / "beat_01.wav").write_bytes(b"")
    (tmp_path / "episodes" / "mi-reel" / "scene.blend").write_bytes(b"")
    calls = []

    def fake_run(self, variant, name, args):
        calls.append(args[0])
        ok = args[0] not in ("render",)  # the cloud render dies (e.g. no internet)
        with self.log.open("a", encoding="utf-8") as f:
            f.write("✔ 1 máquina(s) destruida(s): ya no cobran\n" if args[0] == "cloud-cleanup" else "")
        self.steps.append({"variant": variant, "name": name, "ok": ok, "seconds": 1.0, "tail": [] if ok else ["x"]})
        return ok

    monkeypatch.setattr(mod.Shift, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["turno.py", "mi-reel", "--cloud"])
    assert mod.main() == 1
    assert calls[-1] == "cloud-cleanup" and "render" in calls
    parte = (tmp_path / "publicar" / "mi-reel" / "PARTE.md").read_text(encoding="utf-8")
    assert "## La nube" in parte and "1 máquina(s) destruida(s)" in parte and ".." not in parte


def test_local_shift_has_no_cloud_section(tmp_path, monkeypatch):
    mod = _module()
    monkeypatch.setattr(mod, "PUBLISH", tmp_path)
    shift = mod.Shift("x", tmp_path / "turno.log")
    a = argparse.Namespace(slug="x", cloud=False, calidad="final")
    parte = mod.report(shift, a, datetime.now(), True, ["A"]).read_text(encoding="utf-8")
    assert "La nube" not in parte
