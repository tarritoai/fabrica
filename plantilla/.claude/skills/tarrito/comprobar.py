"""`/tarrito comprobar`: check the deliverable of each course lot (curso/comprobaciones.json) and stamp it APROBADO.

This is the ONLY checker of the course. Inside the project the student says `/tarrito comprobar [lote]`; before the
factory exists, `/fabrica:tarrito comprobar` (the plugin) checks the few pre-install lots itself, and as soon as the
project exists it just runs this script (with the project's Python) and relays its output and exit code.

Usage (from the project root):
    uv run python .claude/skills/tarrito/comprobar.py                 # every pending lot; stamps what passes
    uv run python .claude/skills/tarrito/comprobar.py 5.2             # just that lot (5·2, 5.2, 5-2 and 05-2 all work)
    uv run python .claude/skills/tarrito/comprobar.py 2.3 --respuesta "cinco"   # lots that are a question
    uv run python .claude/skills/tarrito/comprobar.py --estado        # the stamp card

Stamps live in curso/progreso.json (the only place). Older installs of the plugin stamped in .fabrica/sellos.json:
those stamps are read and copied over the first time. Standard library only (it must work before anything else is
installed); the lots that need the factory's own code (doctor, comando) run it with the project's .venv Python.
Exit code: 0 = passed (or the sweep ran), 1 = something is missing, 2 = unknown lot.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHECKS = ROOT / "curso" / "comprobaciones.json"
PROGRESS = ROOT / "curso" / "progreso.json"
LEGACY_STAMPS = ROOT / ".fabrica" / "sellos.json"  # where the plugin used to stamp (read and migrated)
CLOUDS = ("OneDrive", "iCloud", "Mobile Documents", "Dropbox", "Google Drive", "GoogleDrive", "Box Sync")
MAX_PATH = 120
PLACEHOLDER = re.compile(r"<[^<>\n`]{1,120}>")
COMMENT = re.compile(r"<!--.*?-->", re.S)
CODE = re.compile(r"`[^`\n]*`")


# --- helpers -------------------------------------------------------------------------------------------------------

def norm(text: str) -> str:
    """lowercase, no accents, no punctuation except inner dots and slashes: 'Sí, ¡TÚ!' -> 'si tu'."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    words = re.sub(r"[^a-z0-9/.]+", " ", text).split()
    return " ".join(w.strip(".") for w in words if w.strip("."))  # 'script.json.' -> 'script.json'


def lot_id(text: str) -> str:
    parts = [p.lstrip("0") or "0" for p in re.split(r"[·.\-,_ ]+", text.strip()) if p]
    return "·".join(parts)


def files(spec: dict, cfg: dict) -> list[Path]:
    globs = spec.get("rutas") or [spec["ruta"]]
    out: list[Path] = []
    for g in globs:
        out += sorted(p for p in ROOT.glob(g) if p.is_file())
    skip = list(spec.get("excluir", []))
    if spec.get("solo_tuyos"):
        skip += [f"*/{e}/*" for e in cfg.get("ejemplos", [])] + [f"*/{e}.*" for e in cfg.get("ejemplos", [])]
    if spec.get("sin_personajes_ejemplo"):
        skip += [f"personajes/{e}/*" for e in cfg.get("personajes_ejemplo", [])]
    rel = lambda p: p.relative_to(ROOT).as_posix()  # noqa: E731
    return [p for p in out if not any(fnmatch.fnmatch(rel(p), s) for s in skip)]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def section(text: str, heading: str | None) -> str:
    if not heading:
        return text
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().lower().startswith(heading.lower())), None)
    if start is None:
        return ""
    end = next((j for j in range(start + 1, len(lines))
                if lines[j].startswith("#") and len(lines[j]) - len(lines[j].lstrip("#")) <= level), len(lines))
    return "\n".join(lines[start + 1:end])


def dotted(data, path: str):
    for key in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def python() -> str:
    """The project's own Python (.venv, where reels and its dependencies live), else the one running this script."""
    for rel in ("Scripts/python.exe", "bin/python"):
        if (ROOT / ".venv" / rel).exists():
            return str(ROOT / ".venv" / rel)
    return sys.executable


def clean_env() -> dict[str, str]:
    """Environment for the factory's code: UTF-8 and no leftovers of whatever Python launched us (uv, the plugin)."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "UV_RUN_RECURSION_DEPTH", "CONDA_PREFIX")}
    return {**env, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run_reels(args: list[str], timeout: float) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run([python(), "-m", "reels.cli", *args], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, env=clean_env())
    except (OSError, subprocess.TimeoutExpired):
        return None


def env_value(var: str) -> str | None:
    """One variable of the project's .env (only tool paths are asked for; nothing is printed)."""
    if value := os.environ.get(var, "").strip():
        return value
    env = ROOT / ".env"
    if not env.exists():
        return None
    for ln in read(env).splitlines():
        if ln.strip().startswith(f"{var}="):
            return ln.split("=", 1)[1].strip().strip("'\"") or None
    return None


def ffprobe() -> str | None:
    """ffprobe as the factory finds it: FFPROBE_BIN in .env (relative to the project), the PATH, or tools/."""
    if value := env_value("FFPROBE_BIN"):
        p = Path(value) if Path(value).is_absolute() else ROOT / value
        if p.exists():
            return str(p)
    if found := shutil.which("ffprobe"):
        return found
    name = "ffprobe.exe" if sys.platform.startswith("win") else "ffprobe"
    hits = sorted((ROOT / "tools").glob(f"*/bin/{name}")) + sorted((ROOT / "tools").glob(f"*/{name}"))
    return str(hits[0]) if hits else None


def duration(video: Path) -> float | None:
    """Seconds of a video, or None if ffprobe is not there (then the length is not held against the student)."""
    exe = ffprobe()
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=60).stdout.strip()
        return float(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def md_table(text: str) -> tuple[list[str], list[list[str]]]:
    rows = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    cells = lambda ln: [c.strip() for c in ln.strip("|").split("|")]  # noqa: E731
    head = [norm(c) for c in cells(rows[0])]
    body = [cells(r) for r in rows[2:] if not set(r.replace("|", "").strip()) <= set("-: ")]
    return head, body


# --- check types (each returns None when it passes, or what is missing) ------------------------------------------

def c_archivo(s, cfg):
    found = files(s, cfg)
    big = [p for p in found if p.stat().st_size >= s.get("min_bytes", 1)]
    return None if big else s["falta"]


def c_video(s, cfg):
    found = files(s, cfg)
    if not found:
        return s["falta"]
    big = [p for p in found if p.stat().st_size >= s.get("min_bytes", 1)]
    if not big:
        return f"{found[-1].relative_to(ROOT).as_posix()} está casi vacío ({found[-1].stat().st_size // 1024} KB): el render se cortó. Repite /humo."
    if minimum := s.get("min_segundos"):
        secs = duration(big[-1])
        if secs is not None and secs < minimum:
            return f"{big[-1].relative_to(ROOT).as_posix()} dura {secs:.1f} s (mínimo {minimum} s): el render se cortó. Repite /humo."
    return None


def c_json(s, cfg):
    for p in files(s, cfg):
        try:
            data = json.loads(read(p))
        except ValueError:
            continue
        if all(str(dotted(data, k) or "").strip() for k in s.get("campos_no_vacios", [])):
            return None
    return s["falta"]


def c_jsonl(s, cfg):
    n = 0
    for p in files(s, cfg):
        for line in read(p).splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            where = s.get("donde", {})
            if any(str(row.get(k)) not in (v if isinstance(v, list) else [v]) for k, v in where.items()):
                continue
            if all(str(dotted(row, k) if dotted(row, k) is not None else "").strip() for k in s.get("campos_no_vacios", [])):
                n += 1
    return None if n >= s.get("min", 1) else s["falta"]


def c_sin_huecos(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    text = CODE.sub("", COMMENT.sub("", section(read(found[0]), s.get("seccion"))))
    holes = PLACEHOLDER.findall(text)
    return None if not holes and text.strip() else f"{s['falta']} (quedan {len(holes)} huecos, p. ej. {holes[0]})" if holes else s["falta"]


def c_items(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    text = COMMENT.sub("", section(read(found[0]), s.get("seccion")))
    items = [ln for ln in text.splitlines() if re.match(r"\s*([-*+]|\d+[.)])\s+\S", ln) and not PLACEHOLDER.fullmatch(
        re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", ln).strip())]
    return None if len(items) >= s["min"] else f"{s['falta']} (hay {len(items)} de {s['min']})"


def c_titulos(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    text = COMMENT.sub("", section(read(found[0]), s.get("seccion")))
    n = sum(1 for ln in text.splitlines() if ln.startswith(s["nivel"] + " "))
    return None if n >= s["min"] else f"{s['falta']} (hay {n} de {s['min']})"


def c_contiene(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    text = norm(read(found[0]))
    missing = [t for t in s["textos"] if not any(norm(alt) in text for alt in t.split("|"))]
    return None if not missing else f"{s['falta']} (falta: {', '.join(m.split('|')[0] for m in missing)})"


def c_no_contiene(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    text = norm(COMMENT.sub("", read(found[0])))
    return None if not any(norm(t) in text for t in s["textos"]) else s["falta"]


def c_regex(s, cfg):
    pat = re.compile(s["patron"], re.M)
    n = sum(len(pat.findall(COMMENT.sub("", read(p)))) for p in files(s, cfg))  # templates hide examples in comments
    return None if n >= s.get("min", 1) else s["falta"]


def c_tabla(s, cfg):
    found = files(s, cfg)
    if not found:
        return s.get("falta_archivo", s["falta"])
    head, body = md_table(read(found[0]))
    col = lambda name: next((i for i, h in enumerate(head) if norm(name) in h), None)  # noqa: E731
    missing = [c for c in s["columnas"] if col(c) is None]
    if missing:
        return f"La tabla de {found[0].relative_to(ROOT).as_posix()} necesita las columnas: {', '.join(s['columnas'])} (falta: {', '.join(missing)})"
    rows = [r for r in body if any(c.strip() for c in r)]
    if len(rows) < s.get("min_filas", 1):
        return f"{s['falta']} (hay {len(rows)} filas de {s['min_filas']})"
    ie, im = col(s["columna_estado"]), col(s["columna_motivo"])
    dead = [r for r in rows if ie < len(r) and norm(s["valor_muerta"]) in norm(r[ie])]
    if len(dead) < s.get("min_fraccion_muertas", 0) * len(rows):
        return f"El jurado mata al menos la mitad: hay {len(dead)} muertas de {len(rows)} ideas."
    nomotive = [r for r in dead if im >= len(r) or len(r[im].strip()) < 3]
    if nomotive:
        return f"Cada muerta lleva su motivo: hay {len(nomotive)} sin motivo (p. ej. «{nomotive[0][0]}»)."
    ij = col(s["columna_jurado"])
    if sum(1 for r in rows if ij < len(r) and r[ij].strip()) < len(rows):
        return "Falta la nota del jurado al lado de alguna idea (columna «jurado»)."
    return None


def c_pregunta(s, cfg, answer: str | None):
    if answer is None:
        return f"PREGUNTA: {s['pregunta']}"
    a = f" {norm(answer)} "
    return None if any(f" {norm(r)} " in a for r in s["respuestas"]) else s["falta"]


def c_sistema(s, cfg):
    machine = platform.machine().lower()
    if sys.platform == "darwin" and machine not in ("arm64", "aarch64"):
        return "Tu Mac tiene procesador Intel: la fábrica necesita un Mac con Apple Silicon (M1 o posterior). Mira «¿Sirve mi computadora?» en el Manual."
    if sys.platform.startswith("win") and machine not in ("amd64", "x86_64", "arm64"):
        return "Windows de 32 bits: la fábrica necesita Windows 10/11 de 64 bits."
    if not (sys.platform == "darwin" or sys.platform.startswith(("win", "linux"))):
        return f"Sistema no soportado ({sys.platform}): la fábrica funciona en macOS (Apple Silicon), Windows 10/11 y Linux."
    return None


def ejemplo_carpeta() -> str:
    """A short folder that exists as an example on THIS system (no C:\\ on Linux or Mac)."""
    return "C:\\fabrica" if sys.platform.startswith("win") else "~/fabrica"


def c_carpeta(s, cfg):
    path = str(ROOT)
    cloud = next((c for c in CLOUDS if c.lower() in path.lower()), None)
    # Windows: «Documentos» or «Escritorio» redirected to OneDrive may not say OneDrive in the path.
    od = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer") or os.environ.get("OneDriveCommercial")
    if not cloud and sys.platform.startswith("win") and od and path.lower().startswith(od.rstrip("\\/").lower()):
        cloud = "OneDrive"
    if cloud:
        return f"Tu fábrica está dentro de {cloud} ({path}): la sincronización rompe los renders. Muévela a una carpeta corta fuera de la nube (p. ej. {ejemplo_carpeta()})."
    if len(path) > MAX_PATH:
        return f"La ruta de tu fábrica es muy larga ({len(path)} caracteres): muévela a una carpeta corta (p. ej. {ejemplo_carpeta()})."
    return None


def c_sin_api_key(s, cfg):
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "Tienes la variable ANTHROPIC_API_KEY puesta: Claude Code cobra por API en vez de usar tu suscripción. Quítala (Manual, lote 1·3) y abre una terminal nueva."
    return None


def c_comando(s, cfg):
    p = run_reels(s["args"], s.get("timeout", 180))
    if p is None:
        return s["falta"]
    if p.returncode == 0:
        return None
    bad = [ln.strip() for ln in p.stdout.splitlines() if "✘" in ln][:3]
    return s["falta"] + (" Lo que falla: " + " · ".join(bad) if bad else "")


def c_doctor(s, cfg):
    """`reels doctor --skip-api --json`: passes when nothing is «falta»; otherwise names each missing piece."""
    p = run_reels(["doctor", "--skip-api", "--json"], s.get("timeout", 600))
    out = p.stdout if p else ""
    try:
        data = json.loads(out[out.index("{"):])
    except ValueError:
        return s["falta"] + " (el doctor no ha podido revisar la fábrica: faltan sus dependencias; repite /fabrica:instalar)"
    if data.get("ok"):
        return None
    bad = [f"{c.get('name')} ({c.get('detail')})" for c in data.get("checks", []) if c.get("status") == "falta"]
    return s["falta"] + (" Lo que falla: " + " · ".join(bad[:5]) if bad else "")


def c_lotes(s, cfg, stamps):
    missing = [lot for lot in s["lotes"] if lot not in stamps]
    return None if not missing else f"{s['falta']} (faltan: {', '.join(missing)})"


TYPES = {"archivo": c_archivo, "video": c_video, "doctor": c_doctor, "json": c_json, "jsonl": c_jsonl, "sin_huecos": c_sin_huecos, "items": c_items,
         "titulos": c_titulos, "contiene": c_contiene, "no_contiene": c_no_contiene, "regex": c_regex,
         "tabla": c_tabla, "sistema": c_sistema, "carpeta": c_carpeta, "sin_api_key": c_sin_api_key,
         "comando": c_comando}


# --- main ------------------------------------------------------------------------------------------------------------

def evaluate(lot: dict, cfg: dict, stamps: dict, answer: str | None) -> list[str]:
    problems = []
    for s in lot["comprobaciones"]:
        kind = s["tipo"]
        if kind == "pregunta":
            r = c_pregunta(s, cfg, answer)
        elif kind == "lotes":
            r = c_lotes(s, cfg, stamps)
        else:
            r = TYPES[kind](s, cfg)
        if r:
            problems.append(r)
    return problems


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _legacy_stamps() -> dict:
    """Stamps of the plugin's old checker: {"1·5": {"titulo": …, "aprobado": "2026-05-01 18:30"}} → ISO strings."""
    out = {}
    for lot, value in _load(LEGACY_STAMPS).items():
        when = value.get("aprobado", "") if isinstance(value, dict) else str(value)
        try:
            when = datetime.strptime(when, "%Y-%m-%d %H:%M").astimezone().isoformat(timespec="seconds")
        except ValueError:
            when = when or datetime.now().astimezone().isoformat(timespec="seconds")
        out[lot_id(lot)] = when
    return out


def load_stamps() -> dict:
    stamps = dict(_load(PROGRESS).get("sellos") or {})
    legacy = {k: v for k, v in _legacy_stamps().items() if k not in stamps}
    if legacy:  # migrate once: from now on curso/progreso.json has them all (the old file is left as it was)
        stamps.update(legacy)
        save_stamps(stamps)
    return stamps


def save_stamps(stamps: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    data = {**_load(PROGRESS), "sellos": stamps}
    PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def show(lot: dict, problems: list[str]) -> None:
    head = f"{lot['lote']} · {lot['titulo']}"
    if not problems:
        print(f"APROBADO · {head}\n  {lot['aprobado']}")
    elif problems[0].startswith("PREGUNTA: "):
        print(f"PREGUNTA · {head}\n  {problems[0][10:]}\n  (contesta con: --lote {lot['lote']} --respuesta \"…\")")
    else:
        print(f"FALTA · {head} · entregable: {lot['entregable']}")
        for p in problems:
            print(f"  - {p}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Comprueba el entregable de cada lote del curso.")
    ap.add_argument("lote", nargs="?", help="p. ej. 5·2, 5.2 o 5-2 (sin nada: todos los pendientes)")
    ap.add_argument("--lote", dest="lote_opt")
    ap.add_argument("--respuesta", help="para los lotes que son una pregunta")
    ap.add_argument("--estado", action="store_true", help="la tarjeta de sellos")
    a = ap.parse_args()

    cfg = json.loads(CHECKS.read_text(encoding="utf-8"))
    lots = cfg["lotes"]
    stamps = load_stamps()

    if a.estado:
        done = sum(1 for lot in lots if lot["lote"] in stamps)
        print(f"Sellos: {done} de {len(lots)}")
        for lot in lots:
            mark = "APROBADO " + stamps[lot["lote"]][:10] if lot["lote"] in stamps else "pendiente"
            print(f"  {lot['lote']:>5}  {mark:<20} {lot['titulo']}")
        return 0

    wanted = a.lote or a.lote_opt
    if wanted:
        lid = lot_id(wanted)
        lot = next((x for x in lots if x["lote"] == lid), None)
        if not lot:
            print(f"No conozco el lote «{wanted}». Los lotes van de 0·1 a {lots[-1]['lote']}.")
            return 2
        problems = evaluate(lot, cfg, stamps, a.respuesta)
        show(lot, problems)
        if not problems and lid not in stamps:
            stamps[lid] = datetime.now().astimezone().isoformat(timespec="seconds")
            save_stamps(stamps)
        return 0 if not problems else 1

    new, first_pending = [], None
    for lot in lots:
        if lot["lote"] in stamps:
            continue
        auto = all(s["tipo"] != "pregunta" for s in lot["comprobaciones"])
        problems = evaluate(lot, cfg, stamps, None) if auto else ["PREGUNTA: " + lot["comprobaciones"][0]["pregunta"]]
        if auto and not problems:
            stamps[lot["lote"]] = datetime.now().astimezone().isoformat(timespec="seconds")
            new.append(lot)
        elif first_pending is None:
            first_pending = (lot, problems)
    save_stamps(stamps)
    for lot in new:
        show(lot, [])
    if not new:
        print("Ningún sello nuevo esta vez.")
    if first_pending:
        print("\nSiguiente pendiente:")
        show(*first_pending)
    print(f"\nSellos: {len(stamps)} de {len(lots)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
