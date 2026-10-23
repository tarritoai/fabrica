"""Metrics typed by hand (what you see in the Instagram / TikTok / YouTube app), saved with the same schema that
`reels stats` writes, so `reels review`, `reels calibrate`, /revision and the analista read them unchanged.

Usage (from the project root):
    uv run python .claude/skills/numeros/numeros.py guardar --plataforma instagram --slug <slug> \
        --publicado "2026-11-02 21:30" --visitas 12345 --alcance 9876 --compartidos 120 \
        [--likes N] [--comentarios N] [--guardados N] [--visto-medio 14.2] [--salta 33] [--seguidores 950] [--enlace URL]
    uv run python .claude/skills/numeros/numeros.py tabla --plataforma tiktok
    uv run python .claude/skills/numeros/numeros.py pendientes

Files: metrics/<plataforma>.jsonl (one snapshot per line) and the follower count in metrics/account.jsonl
(Instagram, the file `reels stats` uses) or metrics/account-<plataforma>.jsonl.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

METRICS = ROOT / "metrics"
PUBLISH = ROOT / "publicar"
EPISODES = ROOT / "episodes"
PLATFORMS = ("instagram", "tiktok", "youtube")
SETTLED_H = 48


def now() -> datetime:
    return datetime.now().astimezone()


def parse_when(text: str) -> datetime:
    """'2026-11-02 21:30' (local time of this computer) or a full ISO date with offset."""
    text = text.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).astimezone()
        except ValueError:
            pass
    return datetime.fromisoformat(text).astimezone()


def video_of(slug: str) -> Path | None:
    found = sorted(PUBLISH.glob(f"*/{slug}.mp4"))
    return found[0] if found else None


def duration(slug: str) -> float | None:
    video = video_of(slug)
    if not video:
        return None
    try:
        from reels import system

        out = subprocess.run([system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return round(float(out.stdout.strip()), 2) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:  # noqa: BLE001  ffprobe missing: the duration is optional
        return None


def known_slugs() -> set[str]:
    slugs = {p.stem for p in PUBLISH.glob("*/*.mp4")}
    slugs |= {p.parent.name for p in EPISODES.glob("*/script.json")}
    return slugs


def guardar(a: argparse.Namespace) -> int:
    warnings = []
    if a.slug not in known_slugs():
        warnings.append(f"no encuentro «{a.slug}» en publicar/ ni en episodes/: ¿está bien escrito? (se guarda igual)")
    posted = parse_when(a.publicado)
    t = now()
    age_h = round((t - posted).total_seconds() / 3600, 1)
    if age_h < 0:
        print("✘ La fecha de publicación es del futuro: revísala.")
        return 1
    metrics = {
        "views": a.visitas, "reach": a.alcance, "likes": a.likes, "comments": a.comentarios, "shares": a.compartidos,
        "saved": a.guardados,
        "ig_reels_avg_watch_time": round(a.visto_medio * 1000) if a.visto_medio is not None else None,
        "reels_skip_rate": a.salta,
    }
    metrics = {k: v for k, v in metrics.items() if v is not None}
    if a.alcance > a.visitas:
        warnings.append("el alcance (cuentas) suele ser menor que las visitas: ¿están al revés?")
    if a.salta is not None and not 0 <= a.salta <= 100:
        print("✘ El % que se va antes de 3 s tiene que estar entre 0 y 100.")
        return 1
    dur = a.duracion or duration(a.slug)
    if a.visto_medio and dur and a.visto_medio > dur * 1.05:
        warnings.append(f"el tiempo medio visto ({a.visto_medio} s) es mayor que lo que dura el vídeo ({dur} s)")
    row = {
        "fetched_at": t.isoformat(timespec="seconds"),
        "media_id": f"manual-{a.plataforma}-{a.slug}",
        "slug": a.slug,
        "posted_at": posted.isoformat(timespec="minutes"),
        "age_h": age_h,
        "permalink": a.enlace,
        "duration_s": dur,
        "metrics": metrics,
        "platform": a.plataforma,
        "source": "manual",
    }
    METRICS.mkdir(exist_ok=True)
    with (METRICS / f"{a.plataforma}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if a.seguidores is not None:
        acc = METRICS / ("account.jsonl" if a.plataforma == "instagram" else f"account-{a.plataforma}.jsonl")
        with acc.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"fetched_at": row["fetched_at"], "followers": a.seguidores, "source": "manual"}) + "\n")

    def pct(n: int | None) -> str:
        return f"{100 * n / a.alcance:.2f} %" if n is not None and a.alcance else "-"

    print(f"✔ Guardado en metrics/{a.plataforma}.jsonl · {a.slug} · {age_h:.0f} h desde que se publicó"
          + ("" if age_h >= SETTLED_H else " (menos de 48 h: datos provisionales)"))
    print(f"  compartidos/alcance {pct(a.compartidos)} · guardados/alcance {pct(a.guardados)} · "
          f"se va antes de 3 s {f'{a.salta:g} %' if a.salta is not None else '-'} · "
          f"% visto {f'{100 * a.visto_medio / dur:.0f} %' if a.visto_medio and dur else '-'}")
    if a.seguidores is not None:
        print(f"  seguidores: {a.seguidores}")
    for w in warnings:
        print(f"  ⚠ {w}")
    return 0


def latest(platform: str) -> dict[str, dict]:
    path = METRICS / f"{platform}.jsonl"
    rows: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = r.get("slug") or f"?{r.get('media_id')}"
            if key not in rows or r["fetched_at"] > rows[key]["fetched_at"]:
                rows[key] = r
    return rows


def tabla(a: argparse.Namespace) -> int:
    rows = latest(a.plataforma)
    if not rows:
        print(f"Aún no hay números de {a.plataforma} (metrics/{a.plataforma}.jsonl). Usa /numeros para meterlos.")
        return 0

    def pct(n, d) -> str:
        return f"{100 * n / d:.1f}" if n is not None and d else "-"

    head = ["episodio", "publicado", "edad", "dur s", "visitas", "alcance", "salta <3s %", "visto s", "% visto",
            "compart. %", "guard. %", "coment. %", "likes %"]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for slug, r in sorted(rows.items(), key=lambda kv: kv[1]["posted_at"]):
        m = r["metrics"]
        reach = m.get("reach")
        watch = (m.get("ig_reels_avg_watch_time") or 0) / 1000
        dur = r.get("duration_s")
        age = (now() - datetime.fromisoformat(r["posted_at"])).total_seconds() / 3600
        print("| " + " | ".join([
            slug, datetime.fromisoformat(r["posted_at"]).strftime("%d/%m %H:%M"),
            f"{age:.0f} h" + ("" if age >= SETTLED_H else " *"), f"{dur:.0f}" if dur else "-",
            str(m.get("views", "-")), str(reach or "-"),
            f"{m['reels_skip_rate']:g}" if m.get("reels_skip_rate") is not None else "-",
            f"{watch:.1f}" if watch else "-", f"{100 * watch / dur:.0f}" if watch and dur else "-",
            pct(m.get("shares"), reach), pct(m.get("saved"), reach), pct(m.get("comments"), reach),
            pct(m.get("likes"), reach),
        ]) + " |")
    print("\n`*` = menos de 48 h: provisional. Porcentajes sobre alcance (cuentas), no sobre visitas. "
          "La edad es la de hoy; los números, los de la última vez que los metiste.")
    return 0


def pendientes(_: argparse.Namespace) -> int:
    videos = sorted({p.stem for p in PUBLISH.glob("*/*.mp4")})
    if not videos:
        print("No hay vídeos en publicar/ todavía.")
        return 0
    data = {pl: latest(pl) for pl in PLATFORMS}
    print("| reel | " + " | ".join(PLATFORMS) + " |")
    print("|---|" + "---|" * len(PLATFORMS))
    for slug in videos:
        cells = []
        for pl in PLATFORMS:
            r = data[pl].get(slug)
            if not r:
                cells.append("sin datos")
                continue
            days = (now() - datetime.fromisoformat(r["fetched_at"])).days
            cells.append(f"hace {days} d" + (" ⚠ viejo" if days > 7 else ""))
        print(f"| {slug} | " + " | ".join(cells) + " |")
    print("\nSolo hace falta la plataforma donde publicas. Mete los números a las 48 h y otra vez a los 7 días.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Métricas a mano: guardar, ver la tabla o ver qué falta.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("guardar")
    g.add_argument("--plataforma", choices=PLATFORMS, required=True)
    g.add_argument("--slug", required=True)
    g.add_argument("--publicado", required=True, help='fecha y hora de publicación, "AAAA-MM-DD HH:MM" (hora local)')
    g.add_argument("--visitas", type=int, required=True)
    g.add_argument("--alcance", type=int, required=True, help="cuentas alcanzadas (o espectadores únicos)")
    g.add_argument("--compartidos", type=int, required=True)
    g.add_argument("--likes", type=int)
    g.add_argument("--comentarios", type=int)
    g.add_argument("--guardados", type=int)
    g.add_argument("--visto-medio", type=float, help="tiempo medio de reproducción, en segundos")
    g.add_argument("--salta", type=float, help="% de gente que se va antes de 3 s")
    g.add_argument("--seguidores", type=int, help="seguidores totales de la cuenta ahora mismo")
    g.add_argument("--enlace")
    g.add_argument("--duracion", type=float, help="duración del vídeo en s (si no, se mide del vídeo de publicar/)")
    t = sub.add_parser("tabla")
    t.add_argument("--plataforma", choices=PLATFORMS, default="instagram")
    sub.add_parser("pendientes")
    a = ap.parse_args()
    return {"guardar": guardar, "tabla": tabla, "pendientes": pendientes}[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
