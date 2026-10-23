"""`/fabrica:tarrito comprobar [lote]`: the plugin's door to the course checks.

There is ONE checker and ONE list of deliverables, both in the student's project:
`.claude/skills/tarrito/comprobar.py` + `curso/comprobaciones.json` (inside the project the student says
`/tarrito comprobar [lote]`). So:
- when the folder already holds a factory, this module only runs that script, with the project's Python (.venv, or the
  plugin's own Python 3.12 if the dependencies are not installed yet: the script is standard library only), and
  passes its output and exit code through;
- before the factory exists (lessons 0·2, 1·1 and 1·3 come before /fabrica:instalar) it checks those few lots itself,
  with the same rules, and does NOT stamp: there is nowhere to stamp yet, and a file in the folder would make
  «preparar» think it is taken. The first `/tarrito comprobar` inside the factory stamps them in one go.

Stamps live only in the project's curso/progreso.json. The old .fabrica/sellos.json of earlier plugin versions is read
(and copied into progreso.json) by the project's script; `sellos()` below reads both for `fabrica estado`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from .comun import FabricaError, Log, decir, entorno_limpio, leer_json

SCRIPT = Path(".claude") / "skills" / "tarrito" / "comprobar.py"
PROGRESO = Path("curso") / "progreso.json"
SELLOS_ANTIGUOS = Path(".fabrica") / "sellos.json"
ANTES_DE_INSTALAR = {"0·2": "Antes de entrar", "1·1": "Tu carpeta y la terminal", "1·3": "Claude Pro y Claude Code"}
RUTA_MAXIMA = 120  # same limit as the project's «carpeta» check


def normalizar(lote: str) -> str:
    """'1.5', '1-5', '1,5', '01-5', 'lote 1·5' → '1·5'; 'a.1', 'A1', 'lote a-1' → 'A·1' (module lots)."""
    m = re.search(r"(\d+)\s*[·.\-,:_ ]\s*(\d+)", lote)
    if m:
        return f"{int(m.group(1))}·{int(m.group(2))}"
    m = re.search(r"\b([A-Za-z])\s*[·.\-,:_ ]?\s*(\d+)\b", re.sub(r"^\s*lote\s+", "", lote.strip(), flags=re.I))
    return f"{m.group(1).upper()}·{int(m.group(2))}" if m else lote.strip()


def hay_proyecto(proyecto: Path) -> bool:
    return (proyecto / SCRIPT).is_file() and (proyecto / "curso" / "comprobaciones.json").is_file()


def python_del_proyecto(proyecto: Path) -> str:
    for rel in ("Scripts/python.exe", "bin/python"):
        if (proyecto / ".venv" / rel).exists():
            return str(proyecto / ".venv" / rel)
    return sys.executable


def delegar(proyecto: Path, lote: str | None, respuesta: str | None = None) -> int:
    """Run the project's checker; its output goes straight to the screen. Returns its exit code."""
    cmd = [python_del_proyecto(proyecto), str(proyecto / SCRIPT)]
    if lote:
        cmd.append(normalizar(lote))
    if respuesta:
        cmd += ["--respuesta", respuesta]
    Log.escribir(f"$ {' '.join(cmd)}   (en {proyecto})")
    try:
        r = subprocess.run(cmd, cwd=proyecto, env=entorno_limpio(), timeout=1800)
    except subprocess.TimeoutExpired as e:
        raise FabricaError("la comprobación tardó demasiado y la he parado", "tiempo-agotado") from e
    Log.escribir(f"(código de salida {r.returncode})")
    return r.returncode


def antes_de_instalar(proyecto: Path, lote: str, revisar_carpeta, info_sistema) -> bool:
    """The pre-install lots, checked by the plugin itself (no stamp). `revisar_carpeta` / `info_sistema` come from
    fabrica.py (the same rules as /fabrica:instalar)."""
    decir(f"Lote {lote} · {ANTES_DE_INSTALAR[lote]}  (tu fábrica aún no está instalada)")
    problemas: list[str] = []
    if lote == "1·1":
        errores, avisos, _ = revisar_carpeta(proyecto)
        problemas = [e for e in errores if "carpeta-no-vacia" not in e]
        if len(str(proyecto)) > RUTA_MAXIMA:
            problemas.append(f"la ruta es muy larga ({len(str(proyecto))} letras): usa una carpeta corta")
        for av in avisos:
            decir(av, "!")
        ok_texto = f"{proyecto}: fuera de la nube y con una ruta corta"
    elif lote == "0·2":
        datos = info_sistema()
        problemas = list(datos["bloqueos"])
        for av in datos["avisos"]:
            decir(av, "!")
        ok_texto = f"{datos.get('version', '')} sirve para la fábrica"
    else:  # 1·3
        if os.environ.get("ANTHROPIC_API_KEY"):
            problemas = [("tienes la variable ANTHROPIC_API_KEY puesta: Claude Code cobra por API en vez de usar tu "
                          "suscripción. Quítala (Manual, lote 1·3) y abre una terminal nueva")]
        ok_texto = "Claude Code usa tu suscripción (no hay ANTHROPIC_API_KEY)"
    for p in problemas:
        decir(p, "✘")
    if problemas:
        decir("Todavía no · arregla lo de arriba y vuelve a comprobar", "✘")
        return False
    decir(ok_texto, "✔")
    decir(f"PASA · {lote}. El sello se pone solo la primera vez que hagas /tarrito comprobar dentro de tu fábrica.", "✔")
    return True


def comprobar(proyecto: Path, lote: str | None, respuesta: str | None = None, revisar_carpeta=None,
              info_sistema=None) -> int:
    """Exit code: 0 passed, 1 missing, 2 unknown lot (same as the project's script)."""
    if hay_proyecto(proyecto):
        return delegar(proyecto, lote, respuesta)
    lote = normalizar(lote or "")
    if lote in ANTES_DE_INSTALAR and revisar_carpeta and info_sistema:
        return 0 if antes_de_instalar(proyecto, lote, revisar_carpeta, info_sistema) else 1
    antes = ", ".join(ANTES_DE_INSTALAR)
    raise FabricaError(
        f"en {proyecto} todavía no hay una fábrica (¿estás en la carpeta de tu fábrica?)", "no-es-proyecto",
        f"si ya la instalaste, abre Claude Code en su carpeta y usa /tarrito comprobar {lote}; si no, antes de "
        f"instalar solo se comprueban los lotes {antes} (el resto, dentro de la fábrica: primero /fabrica:instalar)")


def sellos(proyecto: Path) -> dict:
    """Stamps of a project: curso/progreso.json, plus any left only in the old .fabrica/sellos.json."""
    out = dict((leer_json(proyecto / PROGRESO, {}) or {}).get("sellos") or {})
    for lote, valor in (leer_json(proyecto / SELLOS_ANTIGUOS, {}) or {}).items():
        out.setdefault(normalizar(lote), valor.get("aprobado", "") if isinstance(valor, dict) else valor)
    return out

