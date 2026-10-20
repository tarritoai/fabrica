"""The known-errors table (errores.json): match a pasted error, look up an installer error code, and render the
table as Markdown for the tutor skill and the course Manual."""

from __future__ import annotations

import json
import re
from pathlib import Path

ARCHIVO = Path(__file__).with_name("errores.json")
SO_NOMBRE = {"todos": "Todos", "windows": "Windows", "mac": "Mac", "linux": "Linux"}


def tabla() -> list[dict]:
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))["errores"]


def por_codigo(codigo: str) -> dict | None:
    return next((e for e in tabla() if e["id"] == codigo), None)


def diagnosticar(texto: str, so: str | None = None, maximo: int = 3) -> list[dict]:
    """Rows whose patterns appear in `texto`, best first (more patterns matched, then this OS before others)."""
    bajo = texto.lower()
    puntuados = []
    for e in tabla():
        hits = sum(1 for p in e["patrones"] if re.search(p, bajo))
        if hits:
            propio = 1 if so and (so in e["so"] or "todos" in e["so"]) else 0
            puntuados.append((hits, propio, e))
    puntuados.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [e for _, _, e in puntuados[:maximo]]


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def _codigo(texto: str) -> str:
    """Inline code that survives backticks inside the text (GLIBC messages use them)."""
    t = _celda(texto)
    return f"`` {t} ``" if "`" in t else f"`{t}`"


def markdown() -> str:
    """The table for humans (plugin/skills/tarrito/errores-conocidos.md and the Manual)."""
    filas = ["# Errores conocidos de la fábrica",
             "",
             "Generado desde `plugin/scripts/fabrica_lib/errores.json` con `python tools/gen_errores.py` (no lo edites a "
             "mano). Busca un trozo del texto en inglés que ves en pantalla. *Origen*: **probado** = lo hemos visto en "
             "una prueba real; **documentado** = lo dice la documentación oficial; **esperado** = mensaje típico, aún "
             "no visto en nuestras pruebas.",
             "",
             "| Sistema | Cuándo | Texto del error (exacto) | Qué significa | Qué hacer | Origen | id |",
             "|---|---|---|---|---|---|---|"]
    orden = {"todos": 0, "windows": 1, "mac": 2, "linux": 3}
    for e in sorted(tabla(), key=lambda e: orden.get(e["so"][0], 9)):
        so = ", ".join(SO_NOMBRE.get(s, s) for s in e["so"])
        filas.append(f"| {so} | {_celda(e['cuando'])} | {_codigo(e['texto'])} | {_celda(e['significa'])} | "
                     f"{_celda(e['arreglo'])} | {e['origen']} | `{e['id']}` |")
    return "\n".join(filas) + "\n"
