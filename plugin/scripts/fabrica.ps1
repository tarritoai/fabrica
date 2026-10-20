# Windows entry point of the factory installer (Mac and Linux: fabrica.sh).
# Run it as:  powershell -NoProfile -ExecutionPolicy Bypass -File fabrica.ps1 <step> [--proyecto DIR] ...
# (-ExecutionPolicy Bypass applies to this one run only: nothing changes on the system, no administrator.)
# Makes sure `uv` exists (official installer, into %USERPROFILE%\.local\bin) and runs fabrica.py with the Python 3.12
# that uv provides. This file is ASCII on purpose: Windows PowerShell 5.1 misreads accents in files without a BOM.
# No param() block on purpose: every argument (including --proyecto) reaches $args untouched.

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }

function Find-Uv {
    if ($env:FABRICA_UV -and (Test-Path -LiteralPath $env:FABRICA_UV)) { return $env:FABRICA_UV }
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @()
    if ($env:UV_INSTALL_DIR) { $candidates += (Join-Path $env:UV_INSTALL_DIR 'uv.exe') }
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE '.local\bin\uv.exe')
        $candidates += (Join-Path $env:USERPROFILE '.cargo\bin\uv.exe')
    }
    if ($env:LOCALAPPDATA) { $candidates += (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\uv.exe') }
    foreach ($c in $candidates) { if (Test-Path -LiteralPath $c) { return $c } }
    return $null
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host '-> Instalando uv (el ayudante que trae Python; sin permisos de administrador)...'
    try {
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex"
    } catch {
        Write-Host ('x No he podido instalar uv: ' + $_.Exception.Message + ' [codigo: uv-falta]')
        exit 1
    }
    $uv = Find-Uv
    if (-not $uv) { Write-Host 'x No he podido instalar uv. [codigo: uv-falta]'; exit 1 }
}

$env:FABRICA_UV = $uv
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:UV_SYSTEM_CERTS) { $env:UV_SYSTEM_CERTS = '1' }  # trust Windows certificates (antivirus that inspect HTTPS)

$script = Join-Path $PSScriptRoot 'fabrica.py'
& $uv run --no-project --python 3.12 $script @args
exit $LASTEXITCODE
