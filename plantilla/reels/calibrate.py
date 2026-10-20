"""How well does each critic predict what really happened? (/calibrar reads this.)

Two sources of predictions:
- metrics/predicciones.jsonl: written by /episodio before publishing (prospective, the honest one).
- metrics/calibracion.jsonl: blind re-rankings of already published ideas (retrospective; marked if contaminated).
Each critic's ranking is compared with the real ranking of mature reels (>=48 h) by Spearman correlation.
"""

from __future__ import annotations

import json

from reels.assets import ROOT
from reels.review import SETTLED_H, latest_snapshots, predictions

BLIND = ROOT / "metrics/calibracion.jsonl"
TARGETS = {"compartidos": lambda m: m["shares"] / m["reach"], "alcance": lambda m: m["reach"],
           "no_salta": lambda m: -m["reels_skip_rate"]}


def real() -> dict[str, dict]:
    """Mature reels (>=48 h) with every target metric."""
    out = {}
    for slug, s in latest_snapshots().items():
        m = s["metrics"]
        if slug.startswith("?") or s["age_h"] < SETTLED_H or not m.get("reach"):
            continue
        out[slug] = {k: f(m) for k, f in TARGETS.items() if m.get("reels_skip_rate") is not None or k != "no_salta"}
    return out


def spearman(predicted: list[str], actual: dict[str, float]) -> tuple[float | None, int]:
    """Rank correlation between a predicted order (best first) and real values, on the reels both have."""
    common = [s for s in predicted if s in actual]
    n = len(common)
    if n < 4:
        return None, n
    pr = {s: i for i, s in enumerate(common)}
    ar = {s: i for i, s in enumerate(sorted(common, key=lambda s: -actual[s]))}
    d2 = sum((pr[s] - ar[s]) ** 2 for s in common)
    return round(1 - 6 * d2 / (n * (n * n - 1)), 2), n


def critic_orders() -> dict[str, dict]:
    """{critic: {"orden": [...], "fuente": ..., "contaminado": bool}} merged from both sources.

    Prospective predictions become an order by score (nota for viewers, puntos for the jury)."""
    out: dict[str, dict] = {}
    scores: dict[str, dict[str, float]] = {}
    for slug, p in predictions().items():
        for name, v in (p.get("espectadores") or {}).items():
            if isinstance(v, dict) and v.get("nota") is not None:
                scores.setdefault(name, {})[slug] = v["nota"]
        if isinstance(p.get("jurado"), (int, float)):
            scores.setdefault("jurado", {})[slug] = p["jurado"]
    for name, sc in scores.items():
        out[f"{name} (antes de publicar)"] = {"orden": sorted(sc, key=lambda s: -sc[s]), "contaminado": False}
    if BLIND.exists():
        for line in BLIND.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            out[f"{row['critico']} (a ciegas {row['fecha']})"] = {"orden": row["orden"],
                                                                    "contaminado": row.get("contaminado", False)}
    return out


def table() -> list[str]:
    actual = real()
    cols = list(TARGETS)
    lines = [f"Reels maduros: {len(actual)}. Spearman: +1 ordena igual que la realidad, 0 = azar, −1 al revés; "
             "con n < 10, |ρ| < 0,6 no se distingue del azar.", "",
             "| crítico | n | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for name, c in sorted(critic_orders().items()):
        vals = []
        n = 0
        for col in cols:
            rho, n = spearman(c["orden"], {s: v[col] for s, v in actual.items() if col in v})
            vals.append("-" if rho is None else f"{rho:+.2f}")
        if n >= 4:
            lines.append(f"| {name}{' ⚠ contaminado' if c['contaminado'] else ''} | {n} | " + " | ".join(vals) + " |")
    return lines


def bias() -> list[str]:
    """Prospective numeric bets (salta_3s, compart_pct) against reality: always optimistic or pessimistic?"""
    snaps = latest_snapshots()
    lines = ["| reel | salta <3 s previsto → real | compartidos % previsto → real |", "|---|---|---|"]
    for slug, p in predictions().items():
        s = snaps.get(slug)
        if not s or s["age_h"] < SETTLED_H:
            continue
        m = s["metrics"]
        real_share = 100 * m["shares"] / m["reach"] if m.get("reach") else None
        lines.append(f"| {slug} | {p.get('salta_3s', '-')} → {m.get('reels_skip_rate', 0):.0f} | "
                     f"{p.get('compart_pct', '-')} → {real_share:.2f} |" if real_share is not None else f"| {slug} | - | - |")
    return lines
