"""The course checker of the 2D factory (the same script as the 3D one): the module lots A·1–A·5, ids with a letter,
and checks that look into the other factory («nave»)."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(".claude") / "skills" / "tarrito" / "comprobar.py"
CHECKS = Path("curso") / "comprobaciones.json"


def _module():
    spec = importlib.util.spec_from_file_location("tarrito_comprobar_2d", ROOT / SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _project(base: Path, name: str, tipo: str) -> Path:
    p = base / name
    for rel in (SCRIPT, CHECKS):
        (p / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, p / rel)
    (p / ".fabrica").mkdir(parents=True, exist_ok=True)
    (p / ".fabrica" / "plantilla.json").write_text(json.dumps({"version": "0.2.0", "tipo": tipo}), encoding="utf-8")
    return p


def _run(p: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONUTF8": "1", "FFPROBE_BIN": str(p / "no-ffprobe")}
    return subprocess.run([sys.executable, str(p / SCRIPT), *args], cwd=p, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=120)


def test_module_lots_are_known_checks():
    mod = _module()
    cfg = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))
    assert [lot["lote"] for lot in cfg["lotes"]] == ["A·1", "A·2", "A·3", "A·4", "A·5"]
    for lot in cfg["lotes"]:
        assert mod.lot_id(lot["lote"]) == lot["lote"]
        assert {c["tipo"] for c in lot["comprobaciones"]} <= set(mod.TYPES)


def test_lot_ids_with_letters():
    mod = _module()
    assert mod.lot_id("a.1") == mod.lot_id("A1") == mod.lot_id("a-1") == mod.lot_id("lote A·1") == "A·1"
    assert mod.lot_id("05-2") == "5·2"


def test_module_lots_from_the_2d_factory(tmp_path):
    nave = _project(tmp_path, "nave-2d", "2d")
    r = _run(nave, "a.2")
    assert r.returncode == 1 and "FALTA · A·2" in r.stdout and "/humo" in r.stdout
    (nave / "episodes" / "humo").mkdir(parents=True)
    (nave / "episodes" / "humo" / "final.mp4").write_bytes(b"\0" * 200_000)
    assert _run(nave, "A·2").returncode == 0
    (nave / "personajes" / "narrador").mkdir(parents=True)
    (nave / "personajes" / "narrador" / "personaje.json").write_text(json.dumps({"voice": {"voice_id": "x1"}}), encoding="utf-8")
    assert "APROBADO · A·3" in _run(nave, "A·3").stdout


def test_a1_finds_the_brief_in_the_3d_factory(tmp_path):
    fabrica = _project(tmp_path, "fabrica", "3d")
    nave = _project(tmp_path, "nave-2d", "2d")
    assert _run(nave, "A·1").returncode == 1
    brief = fabrica / "curso" / "ejercicios" / "encargo.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# Encargo: cuentos\n## Lo que cambia\n- Motor: dibujo\n- Voz: un narrador\n## Puertas\n- guion\n## Gasto\n- poco\n",
                     encoding="utf-8")
    r = _run(nave, "A·1")
    assert r.returncode == 0 and "APROBADO · A·1" in r.stdout, r.stdout


def test_without_a_2d_factory_the_message_says_how(tmp_path):
    alone = _project(tmp_path, "solo", "3d")
    cfg = json.loads((alone / CHECKS).read_text(encoding="utf-8"))
    cfg["lotes"] = json.loads((ROOT / CHECKS).read_text(encoding="utf-8"))["lotes"]
    (alone / CHECKS).write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    r = _run(alone, "A·2")
    assert r.returncode == 1 and "/fabrica:nave" in r.stdout
