"""The course checker (.claude/skills/tarrito/comprobar.py): every lot uses a known check, and the lots of the
installer (1·1, 1·4, 1·5) and the stamps (curso/progreso.json, migrating the old .fabrica/sellos.json) behave."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(".claude") / "skills" / "tarrito" / "comprobar.py"
CHECKS = Path("curso") / "comprobaciones.json"


def _module():
    spec = importlib.util.spec_from_file_location("tarrito_comprobar", ROOT / SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _project(tmp_path: Path) -> Path:
    p = tmp_path / "fabrica"
    for rel in (SCRIPT, CHECKS):
        (p / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, p / rel)
    return p


def _run(p: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1", "FFPROBE_BIN": str(p / "no-ffprobe")}
    return subprocess.run([sys.executable, str(p / SCRIPT), *args], cwd=p, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=120)


def test_every_lot_uses_a_known_check():
    mod = _module()
    cfg = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))
    known = set(mod.TYPES) | {"pregunta", "lotes"}
    assert len(cfg["lotes"]) == 50
    for lot in cfg["lotes"]:
        assert mod.lot_id(lot["lote"]) == lot["lote"]
        assert {c["tipo"] for c in lot["comprobaciones"]} <= known, lot["lote"]


def test_installer_lots_and_stamps(tmp_path):
    p = _project(tmp_path)
    (p / ".fabrica").mkdir()
    (p / ".fabrica" / "sellos.json").write_text(
        json.dumps({"1·1": {"titulo": "Tu carpeta", "aprobado": "2026-05-01 18:30"}}), encoding="utf-8")

    r = _run(p, "1.5")
    assert r.returncode == 1 and "FALTA · 1·5" in r.stdout and "/humo" in r.stdout
    (p / "episodes" / "humo").mkdir(parents=True)
    (p / "episodes" / "humo" / "final.mp4").write_bytes(b"\0" * 1000)
    assert "casi vacío" in _run(p, "1·5").stdout
    (p / "episodes" / "humo" / "final.mp4").write_bytes(b"\0" * 300_000)
    r = _run(p, "1-5")
    assert r.returncode == 0 and "APROBADO · 1·5" in r.stdout

    r = _run(p, "1·4")  # not installed by /fabrica:instalar, no reels/ to run the doctor
    assert r.returncode == 1 and ".fabrica/plantilla.json" in r.stdout and "doctor" in r.stdout

    stamps = json.loads((p / "curso" / "progreso.json").read_text(encoding="utf-8"))["sellos"]
    assert set(stamps) == {"1·1", "1·5"} and stamps["1·1"].startswith("2026-05-01T18:30")
    assert "APROBADO 2026-05-01" in _run(p, "--estado").stdout


def test_cloud_folder_fails(tmp_path, monkeypatch):
    mod = _module()
    monkeypatch.setattr(mod, "ROOT", tmp_path / "Dropbox" / "fabrica")
    assert "Dropbox" in mod.c_carpeta({}, {})
    monkeypatch.setattr(mod, "ROOT", tmp_path / "fabrica")
    assert mod.c_carpeta({}, {}) is None or len(str(tmp_path)) > mod.MAX_PATH


def test_cloud_and_long_folder_examples_match_the_system(tmp_path, monkeypatch):
    mod = _module()
    monkeypatch.setattr(mod, "ROOT", tmp_path / "Dropbox" / "fabrica")
    monkeypatch.setattr(sys, "platform", "linux")
    msg = mod.c_carpeta({}, {})
    assert "~/fabrica" in msg and "C:" not in msg
    monkeypatch.setattr(sys, "platform", "darwin")
    assert "C:" not in mod.c_carpeta({}, {})
    monkeypatch.setattr(sys, "platform", "win32")
    assert "C:\\fabrica" in mod.c_carpeta({}, {}) and "~/fabrica" not in mod.c_carpeta({}, {})


def _character(p: Path, name: str, voice: bool = False) -> None:
    folder = p / "personajes" / name
    folder.mkdir(parents=True, exist_ok=True)
    data = {"id": name, "role": "cosa", "display_name": name.title()}
    if voice:
        data["voice"] = {"voice_id": "abc123"}
    (folder / "personaje.json").write_text(json.dumps(data), encoding="utf-8")
    (folder / "fotograma.png").write_bytes(b"\0" * 6000)
    (folder / "casting.md").write_text("# casting\n", encoding="utf-8")


def test_example_characters_do_not_stamp_4_4_and_4_5(tmp_path):
    p = _project(tmp_path)
    cfg = json.loads((p / CHECKS).read_text(encoding="utf-8"))
    assert {"lucio", "estudiante"} <= set(cfg["personajes_ejemplo"])
    for example in cfg["personajes_ejemplo"]:  # what the template ships, with voice and everything
        _character(p, example, voice=True)
    for lot in ("4·4", "4·5"):
        r = _run(p, lot)
        assert r.returncode == 1 and f"FALTA · {lot}" in r.stdout, r.stdout
    _character(p, "tarro", voice=True)  # the student's own
    for lot in ("4·4", "4·5"):
        r = _run(p, lot)
        assert r.returncode == 0 and f"APROBADO · {lot}" in r.stdout, r.stdout


def test_template_characters_are_all_listed_as_examples():
    cfg = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))
    shipped = {d.name for d in (ROOT / "personajes").iterdir() if d.is_dir()}
    assert shipped <= set(cfg["personajes_ejemplo"])


def test_reels_ejemplo_is_pre_approved():
    allow = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    assert "Bash(uv run reels ejemplo:*)" in allow


def test_answers_ignore_end_dots_but_keep_inner_ones():
    norm = _module().norm
    assert norm("No.") == norm("no") == "no"
    assert norm("La puntuación.") == "la puntuacion"
    assert norm("script.json.") == "script.json"
    assert norm("reels/x.mp4") == "reels/x.mp4"
    assert norm("Sí, ¡TÚ!") == "si tu"


def _answer(lot: str, text: str) -> bool:
    mod = _module()
    cfg = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))
    spec = next(x for x in cfg["lotes"] if x["lote"] == lot)["comprobaciones"][0]
    return mod.c_pregunta(spec, cfg, text) is None


@pytest.mark.parametrize("lot,text,ok", [
    ("9·2", "No.", True), ("9·2", "no, sigue cobrando", True), ("9·2", "No, no sé… no deja de cobrar", True),
    ("9·2", "No sé.", False), ("9·2", "no lo sé", False), ("9·2", "ni idea", False), ("9·2", "Sí, deja de cobrar", False),
    ("10·3", "Una.", True), ("10·3", "una vez", True), ("10·3", "Uno.", True), ("10·3", "1", True),
    ("10·3", "uno o dos", False), ("10·3", "más de uno", False), ("10·3", "2", False),
    ("11·4", "El fotograma cero.", True), ("11·4", "segundo cero", True), ("11·4", "fotograma 0", True),
    ("11·4", "la música", False),
])
def test_question_answers(lot, text, ok):
    assert _answer(lot, text) is ok


def test_9_4_needs_the_final_gate(tmp_path):
    p = _project(tmp_path)
    (p / "publicar" / "mi-reel").mkdir(parents=True)
    (p / "publicar" / "mi-reel" / "mi-reel.mp4").write_bytes(b"\0" * 400_000)
    (p / "publicar" / "mi-reel" / "mi-reel.txt").write_text("Texto. Envíaselo a quien…\n", encoding="utf-8")
    (p / "episodes" / "mi-reel").mkdir(parents=True)
    estado = p / "episodes" / "mi-reel" / "estado.md"
    estado.write_text("- [x] Puerta 4 · preview · aprobada 2026-10-20\n- [ ] Puerta 5 · final (OK a publicar)\n",
                      encoding="utf-8")
    r = _run(p, "9.4")
    assert r.returncode == 1 and "Puerta 5" in r.stdout
    estado.write_text("- [x] Puerta 5 · final · aprobada 2026-10-21 · apuesta 30 % / 2 %\n", encoding="utf-8")
    r = _run(p, "9.4")
    assert r.returncode == 0 and "APROBADO · 9·4" in r.stdout


def test_lot_titles_say_computadora():
    text = (ROOT / CHECKS).read_text(encoding="utf-8").lower()
    assert "ordenador" not in text
    cfg = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))
    titles = {x["lote"]: x["titulo"] for x in cfg["lotes"]}
    assert titles["9·2"] == "Alquilar una supercomputadora" and titles["10·1"] == "De tu computadora al teléfono"


def test_numeros_is_pre_approved():
    allow = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    assert "Bash(uv run python .claude/skills/numeros/numeros.py:*)" in allow
