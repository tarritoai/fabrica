"""Build dist/fabrica-plugin.zip: the plugin folder WITH the template inside (fabrica/plantilla/), for the install
route that needs no git (an `archive` source; see .claude-plugin/marketplace-sin-git.json), with both templates
(fabrica/plantilla/ and fabrica/plantilla-2d/). The zip holds one top
folder, `fabrica/`, which Claude Code accepts as the plugin root ("at the top of the zip or one directory down").

    python tools/empaquetar.py            # → dist/fabrica-plugin.zip and its .sha256
"""

from __future__ import annotations

import hashlib
import os
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plugin" / "scripts"))

from fabrica_lib.plantilla import archivos  # noqa: E402  (same exclusions as an install: no .venv, node_modules...)

FECHA = (2026, 1, 1, 0, 0, 0)  # fixed timestamps: the same sources give the same zip


def _meter(zf: zipfile.ZipFile, origen: Path, destino: str) -> None:
    info = zipfile.ZipInfo(destino, FECHA)
    ejecutable = origen.suffix in (".sh",) or os.access(origen, os.X_OK) and origen.suffix not in (".py", ".json", ".md")
    info.external_attr = ((0o755 if ejecutable else 0o644) | 0o100000) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, origen.read_bytes())


def main() -> int:
    dist = RAIZ / "dist"
    dist.mkdir(exist_ok=True)
    salida = dist / "fabrica-plugin.zip"
    with zipfile.ZipFile(salida, "w") as zf:
        for rel, p in sorted(archivos(RAIZ / "plugin").items()):
            _meter(zf, p, f"fabrica/{rel}")
        for carpeta in ("plantilla", "plantilla-2d"):  # the 3D factory and the 2D one («la nave de enfrente»)
            for rel, p in sorted(archivos(RAIZ / carpeta).items()):
                _meter(zf, p, f"fabrica/{carpeta}/{rel}")
    sha = hashlib.sha256(salida.read_bytes()).hexdigest()
    (dist / "fabrica-plugin.zip.sha256").write_text(f"{sha}  fabrica-plugin.zip\n", encoding="utf-8")
    print(f"{salida} ({salida.stat().st_size / 1e6:.1f} MB) sha256 {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
