"""The night shift: render + compose + check an episode (and its B hook) unattended, then write the morning report.

Usage (from the project root):
    uv run python .claude/skills/turno-de-noche/turno.py <slug> [--cloud] [--calidad final] [--portada N]
                                                         [--sin-b] [--segundo-plano]

--segundo-plano: start itself detached and return at once (closing Claude Code or the terminal does not stop it).
Everything runs inside reels.system.keep_awake (the computer must not fall asleep). It never publishes anything.
Output: publicar/<slug>/PARTE.md (always, also when a step fails) and publicar/<slug>/turno.log.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reels.system import exit_cleanly_on_terminate, keep_awake  # noqa: E402

EPISODES = ROOT / "episodes"
PUBLISH = ROOT / "publicar"
CRITICAL = {"guion", "voces", "revisión del guion", "escena", "render", "montaje", "vídeo final"}  # these stop the shift


class Shift:
    def __init__(self, slug: str, log: Path) -> None:
        self.slug = slug
        self.log = log
        self.steps: list[dict] = []  # {"variant", "name", "ok", "seconds", "tail"}
        self.checks: dict[str, tuple[int, int, list[str]]] = {}  # variant -> (ok lines, bad lines, bad texts)
        self.cloud_note = ""  # what the final clean-up of the cloud said

    def run(self, variant: str, name: str, args: list[str]) -> bool:
        cmd = [sys.executable, "-m", "reels.cli", *args]
        t0 = time.time()
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        with self.log.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%H:%M:%S} · {variant} · {name}: reels {' '.join(args)}\n")
            f.flush()
            p = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace")
            f.write(p.stdout)
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        ok = p.returncode == 0
        self.steps.append({"variant": variant, "name": name, "ok": ok, "seconds": time.time() - t0,
                           "tail": lines[-8:] if not ok else []})
        if name == "comprobación":
            good = [ln for ln in lines if "✔ beat" in ln]
            bad = [ln.strip() for ln in lines if "✘ beat" in ln]
            self.checks[variant] = (len(good), len(bad), bad)
        return ok

    def fail(self, variant: str, name: str, why: str) -> None:
        self.steps.append({"variant": variant, "name": name, "ok": False, "seconds": 0.0, "tail": [why]})


def has_voices(slug: str) -> bool:
    audio = EPISODES / slug / "audio"
    return audio.is_dir() and any(audio.glob("beat_*.wav"))


def duration(slug: str) -> float | None:
    tl = EPISODES / slug / "timeline.json"
    try:
        return float(json.loads(tl.read_text(encoding="utf-8"))["duration"])
    except (OSError, ValueError, KeyError):
        return None


def do_variant(shift: Shift, slug: str, variant: str, a: argparse.Namespace, dest: Path) -> bool:
    if not (EPISODES / slug / "script.json").exists():
        shift.fail(variant, "guion", f"no existe episodes/{slug}/script.json")
        return False
    if not has_voices(slug):
        shift.fail(variant, "voces", "no hay voces: primero la capa 2 de /episodio (Puerta 2)")
        return False
    if not shift.run(variant, "revisión del guion", ["lint", slug]):
        return False
    if not (EPISODES / slug / "scene.blend").exists() and not shift.run(variant, "escena", ["build", slug]):
        return False
    render = ["render", slug, "--quality", a.calidad] + (["--cloud"] if a.cloud else [])
    if not shift.run(variant, "render", render):
        return False
    if not shift.run(variant, "montaje", ["compose", slug]):
        return False
    shift.run(variant, "comprobación", ["check", slug])  # a failed line is reported, the video is still delivered
    shift.run(variant, "hoja del arranque", ["sheet", slug, "--start", "0", "--end", "3", "--fps", "8"])
    dur = duration(slug)
    if dur and dur > 5:
        shift.run(variant, "hoja del final", ["sheet", slug, "--start", f"{dur - 5:.1f}", "--end", f"{dur:.1f}",
                                              "--fps", "4"])
    final = EPISODES / slug / "final.mp4"
    if not final.exists():
        shift.fail(variant, "vídeo final", f"no se generó episodes/{slug}/final.mp4")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(final, dest)
    return True


def size(p: Path) -> str:
    return f"{p.stat().st_size / 1e6:.1f} MB" if p.exists() else ""


def report(shift: Shift, a: argparse.Namespace, started: datetime, done_ok: bool, variants: list[str]) -> Path:
    slug = a.slug
    out = PUBLISH / slug
    out.mkdir(parents=True, exist_ok=True)
    ended = datetime.now()
    mins = int((ended - started).total_seconds() // 60)
    lines = [f"# Parte de la mañana · {slug}", "",
             f"Turno: {started:%d/%m %H:%M} → {ended:%H:%M} ({mins // 60} h {mins % 60} min) · render "
             f"{'en la nube' if a.cloud else 'en tu computadora'} · calidad {a.calidad}", ""]
    if done_ok:
        lines.append("**Resultado: ✔ todo hecho.** El vídeo está en esta carpeta. No se ha publicado nada.")
    else:
        failed = next((s for s in reversed(shift.steps) if not s["ok"] and s["name"] in CRITICAL),
                      {"name": "?", "variant": "?"})
        lines.append(f"**Resultado: ✘ se paró en «{failed['name']}» ({failed['variant']}).** No se ha publicado nada.")
    lines += ["", "## Qué hizo la fábrica", "| versión | paso | resultado | tiempo |", "|---|---|---|---|"]
    for s in shift.steps:
        lines.append(f"| {s['variant']} | {s['name']} | {'✔' if s['ok'] else '✘'} | {s['seconds'] / 60:.1f} min |")
    errors = [s for s in shift.steps if not s["ok"]]
    if errors:
        lines += ["", "## Lo que falló (últimas líneas)"]
        for s in errors:
            lines.append(f"- **{s['variant']} · {s['name']}**:")
            lines += [f"  `{t.strip()[:160]}`" for t in s["tail"]]
        lines.append("- El registro completo está en `turno.log`. Pídele a Claude: «lee el parte del turno de noche».")
    if shift.checks:
        lines += ["", "## Comprobación frase a frase (¿cada frase suena en su plano?)"]
        for v, (good, bad, texts) in shift.checks.items():
            lines.append(f"- {v}: {good} de {good + bad} frases bien" + (":" if bad else "."))
            lines += [f"  - {t}" for t in texts]
    if a.cloud:
        lines += ["", "## La nube",
                  f"- Limpieza final: {shift.cloud_note.rstrip('.') or 'no se pudo comprobar'}.",
                  "- Para quedarte tranquilo: console.vast.ai → Instances tiene que estar vacía "
                  "(o `uv run reels cloud-cleanup`)."]
    lines += ["", f"## En `publicar/{slug}/`"]
    expected = [(f"{slug}.mp4", "el vídeo A")]
    if "B" in variants:
        expected.append((f"{slug}-b.mp4", "el vídeo B (gancho B)"))
    expected += [(f"{slug}.txt", "el texto del post A"), (f"{slug}_portada.png", "la portada")]
    if "B" in variants:
        expected.insert(3, (f"{slug}-b.txt", "el texto del post B (tiene que empezar con otra frase)"))
    for name, what in expected:
        p = out / name
        lines.append(f"- {'✔' if p.exists() else '✘ falta'} `{name}` · {what} {size(p) if name.endswith('.mp4') else ''}".rstrip())
    lines += ["", "## Antes de publicar (lo haces tú)",
              "- [ ] Ver el vídeo entero, con sonido y en el teléfono.",
              f"- [ ] Mirar las hojas `episodes/{slug}/sheet_0-3.png` (arranque) o pedirle al ojo que las revise.",
              f"- [ ] Aprobar la Puerta 5 con `/episodio {slug}` (texto, portada, predicción).",
              "- [ ] Subir A y B como reels de prueba; a las ~24 h, publicar para todos el que menos gente pierda en 3 s.",
              "", "_La fábrica nunca publica: lo subes tú._"]
    parte = out / "PARTE.md"
    parte.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return parte


def detach(argv: list[str], log: Path) -> int:
    args = [a for a in argv if a != "--segundo-plano"]
    log.parent.mkdir(parents=True, exist_ok=True)
    out = log.open("a", encoding="utf-8")
    kw: dict = {"cwd": ROOT, "stdout": out, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *args], **kw)
    (log.parent / "turno.pid").write_text(str(p.pid), encoding="utf-8")
    print(f"Turno de noche en marcha (proceso {p.pid}). Registro: {log.relative_to(ROOT)}")
    print("Puedes cerrar Claude Code. Deja la computadora enchufada y sin apagar; por la mañana, PARTE.md.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Turno de noche: render + montaje + comprobación + parte de la mañana.")
    ap.add_argument("slug")
    ap.add_argument("--cloud", action="store_true", help="render en una GPU alquilada (cuesta: pide OK antes)")
    ap.add_argument("--calidad", default="final", help="final (por defecto) | preview | draft")
    ap.add_argument("--portada", type=int, default=0, help="beat del que sale la portada (0 = sin portada)")
    ap.add_argument("--sin-b", action="store_true", help="no hacer el gancho B aunque exista episodes/<slug>-b/")
    ap.add_argument("--segundo-plano", action="store_true", help="lanzarse aparte y volver enseguida")
    a = ap.parse_args()

    out = PUBLISH / a.slug
    log = out / "turno.log"
    if a.segundo_plano:
        return detach(sys.argv[1:], log)

    out.mkdir(parents=True, exist_ok=True)
    if (out / "PARTE.md").exists():  # a report from an older shift must not pass for tonight's
        (out / "PARTE.md").replace(out / "PARTE-anterior.md")
    started = datetime.now()
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n##### Turno de noche · {a.slug} · {started:%Y-%m-%d %H:%M}\n")
    shift = Shift(a.slug, log)
    variants = ["A"]
    b_slug = f"{a.slug}-b"
    if not a.sin_b and (EPISODES / b_slug / "script.json").exists():
        variants.append("B")
    ok = True
    # exit_cleanly_on_terminate: if the shift is told to stop (SIGTERM, a closed console on Windows), the `finally`
    # below still destroys any rented machine. If the computer loses power, the machine's own guard does it.
    with keep_awake("turno de noche"), exit_cleanly_on_terminate():
        try:
            ok = do_variant(shift, a.slug, "A", a, out / f"{a.slug}.mp4")
            if ok and a.portada:
                shift.run("A", "portada", ["cover", a.slug, "--beat", str(a.portada)])
            if ok and "B" in variants:
                ok = do_variant(shift, b_slug, "B", a, out / f"{b_slug}.mp4")
        finally:
            if a.cloud:  # a rented machine left running keeps charging: always clean up (only machines nobody uses)
                shift.run("-", "apagar máquinas de la nube", ["cloud-cleanup"])
                shift.cloud_note = next((ln.strip() for ln in reversed(log.read_text(encoding="utf-8").splitlines())
                                         if "✔" in ln or "✘" in ln), "")
    parte = report(shift, a, started, ok, variants)
    (out / "turno.pid").unlink(missing_ok=True)
    print(f"{'✔' if ok else '✘'} Parte de la mañana: {parte.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
