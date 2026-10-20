"""Claude Code user settings the installer offers to change (only with the student's OK):

- `autoUpdate` of our marketplace, so fixes reach the student without them knowing about /plugin. Documented:
  "autoUpdate on its extraKnownMarketplaces entry in a settings file" wins over the /plugin toggle
  (code.claude.com/docs/en/plugins/loading#which-marketplaces-and-plugins-auto-update).
- `language`: Claude answers in that language everywhere (code.claude.com/docs/en/settings).

The file is edited only if it is valid JSON; a copy is kept next to it first.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .comun import FabricaError, carpeta_claude, decir, leer_json
from .plantilla import MARKETPLACE, REPO


def ruta_settings() -> Path:
    return carpeta_claude() / "settings.json"


def _leer(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise FabricaError(f"no toco {path}: no es un JSON válido ({e})", "settings-invalido",
                           "ábrelo con /config o arréglalo a mano; y activa las actualizaciones desde /plugin → "
                           "Marketplaces → tarritoai → Enable auto-update") from e
    if not isinstance(data, dict):
        raise FabricaError(f"no toco {path}: no tiene el formato esperado", "settings-invalido")
    return data


def _guardar(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_name(f"settings.json.antes-de-fabrica-{time.strftime('%Y%m%d-%H%M%S')}"))
    tmp = path.with_name("settings.json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def fuente_marketplace() -> dict:
    """The source the student actually added our marketplace from (GitHub, a local folder, a URL...)."""
    conocidos = leer_json(carpeta_claude() / "plugins" / "known_marketplaces.json", {}) or {}
    datos = conocidos.get(MARKETPLACE) if isinstance(conocidos, dict) else None
    if isinstance(datos, dict) and isinstance(datos.get("source"), dict):
        return datos["source"]
    return {"source": "github", "repo": REPO}


def activar_auto_update() -> bool:
    """True if something changed."""
    path = ruta_settings()
    data = _leer(path)
    mercados = data.setdefault("extraKnownMarketplaces", {})
    if not isinstance(mercados, dict):
        raise FabricaError("extraKnownMarketplaces de settings.json tiene un formato raro: no lo toco", "settings-invalido")
    entrada = mercados.setdefault(MARKETPLACE, {})
    if not isinstance(entrada, dict):
        raise FabricaError("la entrada tarritoai de settings.json tiene un formato raro: no la toco", "settings-invalido")
    if entrada.get("autoUpdate") is True and "source" in entrada:
        decir("actualizaciones automáticas de la fábrica: ya estaban activadas", "✔")
        return False
    entrada.setdefault("source", fuente_marketplace())
    entrada["autoUpdate"] = True
    _guardar(path, data)
    decir("actualizaciones automáticas de la fábrica: activadas (se aplican al abrir Claude Code)", "✔")
    return True


def poner_idioma(idioma: str = "spanish") -> bool:
    path = ruta_settings()
    data = _leer(path)
    if data.get("language") == idioma:
        decir(f"idioma de Claude: ya era «{idioma}»", "✔")
        return False
    data["language"] = idioma
    _guardar(path, data)
    decir(f"idioma de Claude: «{idioma}» (desde la próxima vez que abras Claude Code)", "✔")
    return True


def estado() -> dict:
    data = {}
    try:
        data = _leer(ruta_settings())
    except FabricaError:
        pass
    entrada = (data.get("extraKnownMarketplaces") or {}).get(MARKETPLACE) or {}
    conocidos = leer_json(carpeta_claude() / "plugins" / "known_marketplaces.json", {}) or {}
    km = conocidos.get(MARKETPLACE) if isinstance(conocidos, dict) else None
    auto = entrada.get("autoUpdate")
    if auto is None and isinstance(km, dict):
        auto = km.get("autoUpdate")
    return {"settings": str(ruta_settings()), "idioma": data.get("language"), "auto_update": bool(auto),
            "marketplace_añadido": isinstance(km, dict)}
