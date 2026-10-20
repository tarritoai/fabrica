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

# A new terminal must find `uv` too (the student will type `uv run ...` later): make sure its folder is in the PATH
# of the shell's startup file, once. Writes nothing if the folder is already there. Never fails the installation.
asegurar_uv_en_path() {
  uvdir="$(dirname "$1")"
  case ":${ORIGINAL_PATH}:" in *":${uvdir}:"*) return 0 ;; esac
  case "$uvdir" in "$HOME"/*) linea="export PATH=\"\$HOME/${uvdir#"$HOME"/}:\$PATH\"  # La Fabrica: uv"; clave="${uvdir#"$HOME"/}" ;;
                   *) linea="export PATH=\"$uvdir:\$PATH\"  # La Fabrica: uv"; clave="$uvdir" ;; esac
  tocados=""; fallos=""
  apuntar_en() {  # one startup file: add the line unless it is already there (paths with spaces are fine)
    if [ -f "$1" ] && grep -qF -- "$clave" "$1" 2>/dev/null; then return 0; fi
    if { if [ -f "$1" ] && [ -n "$(tail -c1 "$1" 2>/dev/null)" ]; then printf '\n' >>"$1"; fi; printf '%s\n' "$linea" >>"$1"; } 2>/dev/null; then
      tocados="$tocados ${1}"
    else
      fallos="$fallos ${1}"
    fi
  }
  hecho=0
  for f in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$f" ]; then apuntar_en "$f"; hecho=1; fi
  done
  if [ "$hecho" = 0 ]; then  # no startup file yet: create the one of the shell this person uses
    case "${SHELL:-}" in
      *zsh) apuntar_en "$HOME/.zshrc" ;;
      *) if [ "$(uname -s)" = "Darwin" ]; then apuntar_en "$HOME/.zshrc"; else apuntar_en "$HOME/.bashrc"; fi ;;
    esac
  fi
  if [ -n "$tocados" ]; then
    echo "✔ He dejado uv accesible para tus terminales nuevas (apuntado en$tocados). Cierra esta terminal y abre otra para que lo use." >&2
  fi
  if [ -n "$fallos" ]; then
    echo "! No he podido escribir en$fallos. Para que una terminal nueva encuentre uv, añade esta línea a ese archivo:" >&2
    echo "    $linea" >&2
    echo "  (o cierra sesión y vuelve a entrar). Mientras, la fábrica funciona: yo sé dónde está uv." >&2
  fi
  return 0
}

ORIGINAL_PATH="$PATH"
UV="$(find_uv || true)"
if [ -z "$UV" ]; then
  echo "→ Instalando uv (el ayudante que trae Python; sin contraseña, en tu carpeta personal)…"
  UVLOG="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/uv-instalacion.log")"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >"$UVLOG" 2>&1 || true
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh >"$UVLOG" 2>&1 || true
  else
    echo "✘ No hay curl ni wget para descargar uv. Instala uno de los dos (o uv desde https://docs.astral.sh/uv/) y repite. [código: uv-falta]"; exit 1
  fi
  UV="$(find_uv || true)"
  if [ -z "$UV" ]; then
    echo "✘ No he podido instalar uv. Esto es lo que dijo el instalador (en inglés):"; tail -n 8 "$UVLOG" | sed 's/^/    /'
    echo "  Revisa tu conexión a internet y repite el paso. [código: uv-falta]"; exit 1
  fi
  echo "✔ uv instalado ($UV)"
fi
# Also when uv already existed but only in a folder that is not in the PATH (e.g. ~/.local/bin in a bare shell).
if ! command -v uv >/dev/null 2>&1 || [ "$(command -v uv)" != "$UV" ]; then asegurar_uv_en_path "$UV"; fi

export FABRICA_UV="$UV" PYTHONUTF8=1 PYTHONIOENCODING=utf-8
export UV_SYSTEM_CERTS="${UV_SYSTEM_CERTS:-1}"  # trust the system's certificates (antivirus that inspect HTTPS)
exec "$UV" run --no-project --python 3.12 "$DIR/fabrica.py" "$@"
