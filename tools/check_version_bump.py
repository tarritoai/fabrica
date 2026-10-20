"""CI guard: if plugin/ changed against the base ref, plugin/.claude-plugin/plugin.json must carry a higher semantic
version. (Claude Code only ships a new copy of the plugin to students when that string changes.)

    python tools/check_version_bump.py origin/main
Exit 0 = fine, 1 = the version must be bumped. Changes in plantilla/ without a bump only warn: students receive the
template through the marketplace clone, but a bump is what announces the update.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

MANIFEST = "plugin/.claude-plugin/plugin.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def version(texto: str) -> tuple[int, int, int]:
    v = json.loads(texto)["version"]
    m = SEMVER.match(v)
    if not m:
        raise SystemExit(f"::error file={MANIFEST}::la versión «{v}» no es semántica (X.Y.Z)")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    actual = version(open(MANIFEST, encoding="utf-8").read())
    try:
        anterior_txt = git("show", f"{base}:{MANIFEST}")
    except subprocess.CalledProcessError:
        print(f"{base} no tiene {MANIFEST} todavía: nada que comparar ({'.'.join(map(str, actual))})")
        return 0
    anterior = version(anterior_txt)
    cambios = git("diff", "--name-only", f"{base}...HEAD").split()
    plugin = [c for c in cambios if c.startswith("plugin/")]
    plantilla = [c for c in cambios if c.startswith("plantilla/")]
    v = lambda t: ".".join(map(str, t))  # noqa: E731
    if plugin and actual <= anterior:
        print(f"::error file={MANIFEST}::plugin/ ha cambiado ({len(plugin)} archivos) pero la versión sigue en "
              f"{v(actual)} (en {base}: {v(anterior)}). Súbela; si no, los alumnos no reciben el cambio.")
        return 1
    if plantilla and actual <= anterior:
        print(f"::warning file={MANIFEST}::plantilla/ ha cambiado sin subir la versión del plugin ({v(actual)}).")
    print(f"versión {v(anterior)} → {v(actual)} · cambios en plugin/: {len(plugin)} · en plantilla/: {len(plantilla)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
