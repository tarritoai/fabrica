"""Regenerate plugin/skills/tarrito/errores-conocidos.md from plugin/scripts/fabrica_lib/errores.json.

    python tools/gen_errores.py          # write the file
    python tools/gen_errores.py --check  # CI: fail if the file is out of date
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plugin" / "scripts"))

from fabrica_lib import diagnostico  # noqa: E402

DESTINO = RAIZ / "plugin" / "skills" / "tarrito" / "errores-conocidos.md"


def main() -> int:
    nuevo = diagnostico.markdown()
    if "--check" in sys.argv:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != nuevo:
            print(f"{DESTINO} no está al día: ejecuta python tools/gen_errores.py")
            return 1
        print("errores-conocidos.md al día")
        return 0
    DESTINO.write_text(nuevo, encoding="utf-8")
    print(f"escrito {DESTINO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
