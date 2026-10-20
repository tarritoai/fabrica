#!/usr/bin/env bash
# Mac and Linux entry point of the factory installer (Windows: fabrica.ps1).
# Makes sure `uv` exists (official installer, into ~/.local/bin, no administrator) and runs fabrica.py with the
# Python 3.12 that uv provides. All arguments are passed through: fabrica.sh <step> [--proyecto DIR] ...
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)  # Git Bash on Windows: the PowerShell entry point knows Windows better
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$DIR/fabrica.ps1")" "$@" ;;
esac

find_uv() {
  if [ -n "${FABRICA_UV:-}" ] && [ -x "${FABRICA_UV}" ]; then echo "$FABRICA_UV"; return 0; fi
  if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
  for c in "${UV_INSTALL_DIR:-}/uv" "${XDG_BIN_HOME:-}/uv" "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" \
           /opt/homebrew/bin/uv /usr/local/bin/uv; do
    if [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

UV="$(find_uv || true)"
if [ -z "$UV" ]; then
  echo "→ Instalando uv (el ayudante que trae Python; sin contraseña, en tu carpeta personal)…"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "✘ No hay curl ni wget para descargar uv. [código: uv-falta]"; exit 1
  fi
  UV="$(find_uv || true)"
  if [ -z "$UV" ]; then echo "✘ No he podido instalar uv. [código: uv-falta]"; exit 1; fi
fi

export FABRICA_UV="$UV" PYTHONUTF8=1 PYTHONIOENCODING=utf-8
export UV_SYSTEM_CERTS="${UV_SYSTEM_CERTS:-1}"  # trust the system's certificates (antivirus that inspect HTTPS)
exec "$UV" run --no-project --python 3.12 "$DIR/fabrica.py" "$@"
