# ─── Arranca el backend Django escuchando en toda la red ────────────────────
#
# Uso:
#   .\arrancar-backend.ps1
#
# Qué hace:
#   1. Activa el venv del backend (srni-backend\.venv)
#   2. Aplica migraciones pendientes
#   3. Arranca runserver en 0.0.0.0:8001 (no solo localhost — el celular llega)
#
# Si es la primera vez en este equipo, también:
#   - Abre puerto 8001 en Windows Firewall (requiere admin)

$ErrorActionPreference = 'Stop'
$rootDir    = $PSScriptRoot
$backendDir = Join-Path $rootDir 'srni-backend'
$venvActivate = Join-Path $backendDir '.venv\Scripts\Activate.ps1'

# ── 1. Verificar venv ───────────────────────────────────────────────────────
if (-not (Test-Path $venvActivate)) {
    Write-Host "ERROR: no encuentro el venv en $venvActivate" -ForegroundColor Red
    Write-Host '  Crea el entorno con:' -ForegroundColor Yellow
    Write-Host "    cd $backendDir" -ForegroundColor Yellow
    Write-Host '    python -m venv .venv' -ForegroundColor Yellow
    Write-Host '    .\.venv\Scripts\Activate.ps1' -ForegroundColor Yellow
    Write-Host '    pip install -r requirements.txt' -ForegroundColor Yellow
    exit 1
}

# ── 2. Verificar regla de firewall ──────────────────────────────────────────
$reglaExiste = Get-NetFirewallRule -DisplayName 'Django SRNI 8001' -ErrorAction SilentlyContinue
if (-not $reglaExiste) {
    Write-Host '─── Abriendo puerto 8001 en Windows Firewall...' -ForegroundColor Cyan
    try {
        New-NetFirewallRule `
            -DisplayName 'Django SRNI 8001' `
            -Direction Inbound `
            -LocalPort 8001 `
            -Protocol TCP `
            -Action Allow `
            -ErrorAction Stop | Out-Null
        Write-Host '  Regla agregada.' -ForegroundColor Green
    } catch {
        Write-Host '  No se pudo agregar la regla (¿permisos de admin?). Continúo, pero el celular puede no conectar.' -ForegroundColor Yellow
    }
}

# ── 3. Activar venv y arrancar ──────────────────────────────────────────────
Set-Location $backendDir
. $venvActivate

Write-Host ''
Write-Host '─── Aplicando migraciones...' -ForegroundColor Cyan
python manage.py migrate

Write-Host ''
Write-Host '─── Arrancando Django en 0.0.0.0:8001 ...' -ForegroundColor Cyan

# Mostrar IPs por las que es accesible
$ips = Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object {
           $_.IPAddress -notlike '127.*' -and
           $_.IPAddress -notlike '169.254.*' -and
           $_.InterfaceAlias -notlike '*WSL*' -and
           ($_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*' -or $_.IPAddress -like '172.*')
       }

foreach ($ip in $ips) {
    Write-Host "  http://$($ip.IPAddress):8001  ($($ip.InterfaceAlias))" -ForegroundColor Green
}
Write-Host ''

python manage.py runserver 0.0.0.0:8001
