"""The project template (plantilla/): where to find it, copying it into the student's folder, and updating a
student's copy WITHOUT touching their memory (docs, ideas, episodes, their characters...).

Where the template is found, in order:
1. <plugin>/plantilla        (a plugin zip that bundles it, see .github/workflows/ci.yml "paquete")
2. <plugin>/../plantilla     (the plugin loaded in place from a local marketplace or a clone of the repo)
3. the marketplace clone Claude Code keeps (plugins/known_marketplaces.json → installLocation/plantilla)
4. a download of the repo from GitHub at the tag of this plugin version (fabrica--v<version>), else main.
The newest version among the ones found wins.

Update rule (3-way, per file), using .fabrica/plantilla.json = the hash of every template file as last installed:
- student memory (MEMORIA below: docs of what works, hypotheses, decisions, ideas, episodes, style, brand, cast):
  never overwritten; missing files are added only if they never existed;
- untouched by the student (hash == installed hash) → replaced by the new version (old one backed up);
- changed by the student → kept; the new version is left in .fabrica/actualizacion-<version>/ for Claude to merge;
- removed from the template and untouched → moved to the backup; changed → kept.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path, PurePosixPath

from . import descargas
from .comun import (FabricaError, borrar, carpeta_claude, decir, escribir_json, leer_json, mover, raiz_plugin,
                    version_plugin, version_tupla)

REPO = "tarritoai/fabrica"
MARKETPLACE = "tarritoai"

# Never copied from the template, never touched in the student's project.
IGNORAR = {".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".git", ".fabrica", "tools",
           "models", "publicar", "grabaciones", "logs", ".cache", ".env", ".DS_Store", "Thumbs.db", "out", ".remotion"}
# The student's memory: what the factory learned about THEIR account, their episodes, their brand and cast.
# Never overwritten, even if they never edited it. (Their own characters, ideas and episodes are not in the template
# at all, so they are never touched either.) Everything else follows the 3-way rule: what the student changed is kept.
MEMORIA = ("docs/hipotesis.md", "docs/decisiones.md", "docs/lo-que-funciona.md", "docs/criticos.md",
           "docs/backlog-visual.md", "ideas/", "episodes/", "metrics/", "reviews/", "references/", "style/",
           "assets/brand/", "assets/music/", "reparto.json", "biblia.md")


def _ignorado(rel: PurePosixPath) -> bool:
    return any(parte in IGNORAR for parte in rel.parts) or rel.name.endswith((".pyc", ".part"))


def es_memoria(rel: str) -> bool:
    return any(rel == m or rel.startswith(m) for m in MEMORIA)


def hash_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def archivos(raiz: Path) -> dict[str, Path]:
    """Every file of a template (or project) that the template manages: relative POSIX path → absolute path."""
    out: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR]
        for f in filenames:
            p = Path(dirpath) / f
            rel = PurePosixPath(p.relative_to(raiz).as_posix())
            if not _ignorado(rel):
                out[str(rel)] = p
    return out


# --- finding the template ------------------------------------------------------------------------------------------


def _es_plantilla(p: Path) -> bool:
    return (p / "reels" / "cli.py").is_file() and (p / "pyproject.toml").is_file()


def _candidatos() -> list[tuple[str, Path, str]]:
    """(where, path, plugin version) of every template copy on this computer."""
    raiz = raiz_plugin()
    out = []
    for donde, p in (("plugin", raiz / "plantilla"), ("repositorio", raiz.parent / "plantilla")):
        if _es_plantilla(p):
            out.append((donde, p, version_plugin(raiz)))
    conocidos = leer_json(carpeta_claude() / "plugins" / "known_marketplaces.json", {}) or {}
    datos = conocidos.get(MARKETPLACE) if isinstance(conocidos, dict) else None
    ubicaciones = []
    if isinstance(datos, dict) and datos.get("installLocation"):
        ubicaciones.append(Path(datos["installLocation"]))
    ubicaciones.append(carpeta_claude() / "plugins" / "marketplaces" / MARKETPLACE)
    for loc in ubicaciones:
        if _es_plantilla(loc / "plantilla"):
            out.append(("marketplace", loc / "plantilla", version_plugin(loc / "plugin")))
    if env := os.environ.get("FABRICA_PLANTILLA", "").strip():  # tests and CI
        p = Path(env)
        if _es_plantilla(p):
            out.insert(0, ("FABRICA_PLANTILLA", p, version_plugin(p.parent / "plugin")))
    return out


def localizar(descargar_si_falta: bool = True) -> tuple[Path, str]:
    """The newest template copy available: (path, version)."""
    cands = _candidatos()
    if cands:
        donde, path, version = max(cands, key=lambda c: version_tupla(c[2]))
        decir(f"plantilla {version} ({donde}: {path})", "·")
        return path, version
    if not descargar_si_falta:
        raise FabricaError("no encuentro la plantilla de la fábrica", "plantilla-no-encontrada")
    return _descargar_plantilla()


def _descargar_plantilla() -> tuple[Path, str]:
    version = version_plugin()
    destino = Path(tempfile.gettempdir()) / f"fabrica-plantilla-{version}"
    if _es_plantilla(destino / "plantilla"):
        return destino / "plantilla", version
    for ref in (f"refs/tags/fabrica--v{version}", "refs/heads/main"):
        url = f"https://codeload.github.com/{REPO}/zip/{ref}"
        archivo = Path(tempfile.gettempdir()) / f"fabrica-{version}-{ref.rsplit('/', 1)[-1]}.zip"
        try:
            descargas.descargar(url, archivo, nombre="plantilla de la fábrica")
        except FabricaError:
            continue
        descargas.extraer(archivo, destino.with_name(destino.name + ".zip"))
        interior = descargas.una_sola_carpeta(destino.with_name(destino.name + ".zip"))
        if destino.exists():
            borrar(destino)
        mover(interior, destino)
        if _es_plantilla(destino / "plantilla"):
            return destino / "plantilla", version_plugin(destino / "plugin")
    raise FabricaError("no encuentro la plantilla de la fábrica ni puedo descargarla", "plantilla-no-encontrada")


# --- install (copy) ------------------------------------------------------------------------------------------------


def manifiesto(proyecto: Path) -> dict:
    return leer_json(proyecto / ".fabrica" / "plantilla.json", {}) or {}


def copiar(plantilla: Path, version: str, proyecto: Path) -> int:
    """Copy the template into a NEW (or empty-ish) project folder. Never overwrites an existing file. Returns the
    number of files copied and writes .fabrica/plantilla.json."""
    proyecto.mkdir(parents=True, exist_ok=True)
    origen = archivos(plantilla)
    hashes: dict[str, str] = {}
    copiados = 0
    for rel, src in sorted(origen.items()):
        dst = proyecto / rel
        hashes[rel] = hash_archivo(src)
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copiados += 1
    escribir_json(proyecto / ".fabrica" / "plantilla.json",
                  {"version": version, "instalada": time.strftime("%Y-%m-%d %H:%M"), "archivos": hashes})
    _ignorar_fabrica(proyecto)
    return copiados


def _ignorar_fabrica(proyecto: Path) -> None:
    gi = proyecto / ".gitignore"
    lineas = [".fabrica/copias/", ".fabrica/actualizacion-*/"]
    texto = gi.read_text(encoding="utf-8") if gi.exists() else ""
    faltan = [ln for ln in lineas if ln not in texto]
    if faltan:
        gi.write_text(texto.rstrip("\n") + "\n\n# Copias de seguridad de /fabrica:actualizar\n" + "\n".join(faltan) + "\n",
                      encoding="utf-8")


# --- update --------------------------------------------------------------------------------------------------------


def planificar(plantilla: Path, proyecto: Path) -> dict[str, list[str]]:
    """What an update would do, without touching anything."""
    base = manifiesto(proyecto).get("archivos", {})
    nueva = archivos(plantilla)
    plan: dict[str, list[str]] = {"nuevos": [], "actualizar": [], "conflictos": [], "memoria": [], "retirar": [],
                                  "iguales": []}
    for rel, src in sorted(nueva.items()):
        dst = proyecto / rel
        h_nuevo = hash_archivo(src)
        if not dst.exists():
            if es_memoria(rel) and rel in base:
                plan["memoria"].append(rel)  # the student deleted it on purpose
            else:
                plan["nuevos"].append(rel)
            continue
        h_alumno = hash_archivo(dst)
        if h_alumno == h_nuevo:
            plan["iguales"].append(rel)
        elif es_memoria(rel):
            plan["memoria"].append(rel)
        elif base.get(rel) == h_alumno:
            plan["actualizar"].append(rel)
        else:
            plan["conflictos"].append(rel)
    for rel, h_base in sorted(base.items()):
        if rel not in nueva and (proyecto / rel).exists() and not es_memoria(rel):
            if hash_archivo(proyecto / rel) == h_base:
                plan["retirar"].append(rel)
    return plan


def aplicar(plantilla: Path, version: str, proyecto: Path, plan: dict[str, list[str]]) -> Path:
    """Apply a plan from `planificar`. Everything replaced or retired is copied first to .fabrica/copias/<date>/."""
    marca = time.strftime("%Y%m%d-%H%M%S")
    copias = proyecto / ".fabrica" / "copias" / marca
    for rel in plan["actualizar"] + plan["retirar"]:
        (copias / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proyecto / rel, copias / rel)
    for rel in plan["nuevos"] + plan["actualizar"]:
        (proyecto / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plantilla / rel, proyecto / rel)
    for rel in plan["retirar"]:
        (proyecto / rel).unlink()
    propuestas = proyecto / ".fabrica" / f"actualizacion-{version}"
    for rel in plan["conflictos"] + plan["memoria"]:
        if (plantilla / rel).exists():
            (propuestas / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(plantilla / rel, propuestas / rel)
    hashes = {rel: hash_archivo(p) for rel, p in archivos(plantilla).items()}
    escribir_json(proyecto / ".fabrica" / "plantilla.json",
                  {"version": version, "instalada": manifiesto(proyecto).get("instalada"),
                   "actualizada": time.strftime("%Y-%m-%d %H:%M"), "archivos": hashes})
    _ignorar_fabrica(proyecto)
    return propuestas
