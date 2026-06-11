# ─── Arranca la app móvil Expo con la IP correcta detectada automáticamente ──
#
# Uso:
#   .\arrancar-mobile.ps1
#
# Qué hace:
#   1. Detecta la IP Wi-Fi (o Ethernet) activa de la máquina
#   2. Actualiza srni-mobile\.env.local con esa IP apuntando al puerto 8001
#   3. Verifica que el backend responde (opcional — no aborta si falla)
#   4. Arranca Expo en el puerto 8082 con caché limpio
#
# Cuando hayas cambiado de red Wi-Fi, ejecuta este script. El celular volverá
# a conectar sin tocar nada manualmente.

$ErrorActionPreference = 'Stop'
$rootDir   = $PSScriptRoot
$mobileDir = Join-Path $rootDir 'srni-mobile'
$envFile   = Join-Path $mobileDir '.env.local'

# ── 1. Detectar IP local válida ─────────────────────────────────────────────
Write-Host '─── Detectando IP de red...' -ForegroundColor Cyan

$ip = Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object {
          $_.IPAddress -notlike '127.*' -and
          $_.IPAddress -notlike '169.254.*' -and
          $_.InterfaceAlias -notlike '*WSL*' -and
          $_.InterfaceAlias -notlike '*Loopback*' -and
          ($_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*' -or $_.IPAddress -like '172.*')
      } |
      Sort-Object { if ($_.InterfaceAlias -like '*Wi-Fi*') { 0 } elseif ($_.InterfaceAlias -like '*Ethernet*') { 1 } else { 2 } } |
      Select-Object -First 1

if (-not $ip) {
    Write-Host 'ERROR: no se detectó IP local. ¿Estás conectado a la red?' -ForegroundColor Red
    exit 1
}

Write-Host "  IP detectada: $($ip.IPAddress) ($($ip.InterfaceAlias))" -ForegroundColor Green

# ── 2. Actualizar .env.local ────────────────────────────────────────────────
$nuevoContenido = "EXPO_PUBLIC_API_URL=http://$($ip.IPAddress):8001`n"
Set-Content -Path $envFile -Value $nuevoContenido -Encoding utf8 -NoNewline
Write-Host "  .env.local actualizado → http://$($ip.IPAddress):8001" -ForegroundColor Green

# ── 3. Verificar backend (no bloquea si falla) ──────────────────────────────
Write-Host ''
Write-Host '─── Verificando backend...' -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://$($ip.IPAddress):8001/health/" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  Backend responde: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host '  Backend NO responde en esa IP.' -ForegroundColor Yellow
    Write-Host '  Asegúrate de que el backend esté corriendo con:' -ForegroundColor Yellow
    Write-Host '    .\arrancar-backend.ps1' -ForegroundColor Yellow
    Write-Host ''
}

# ── 4. Arrancar Expo ────────────────────────────────────────────────────────
Write-Host ''
Write-Host '─── Arrancando Expo en puerto 8082 (con caché limpio)...' -ForegroundColor Cyan
Write-Host ''

Set-Location $mobileDir
& npx expo start --port 8082 --clear
