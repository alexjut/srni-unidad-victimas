#!/usr/bin/env bash
# ------------------------------------------------------------
# Arranca ngrok contra el puerto 8090 usando un dominio reservado.
# Requiere haber configurado antes el authtoken:
#   ~/bin/ngrok config add-authtoken <TOKEN>
# Uso: 61-start-ngrok.sh <dominio.ngrok.app>
# ------------------------------------------------------------
set -euo pipefail
DOMAIN="${1:?Uso: 61-start-ngrok.sh <dominio.ngrok.app>}"
NGROK="$HOME/bin/ngrok"

# Matar instancia previa si existe
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

echo "Arrancando ngrok -> https://$DOMAIN  (puerto local 8090)"
nohup "$NGROK" http 8090 --url="https://$DOMAIN" > /tmp/ngrok.log 2>&1 &
sleep 5

echo "=== Túnel activo ==="
curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*"' | head -2
echo ""
echo "=== Prueba pública (vía ngrok) ==="
curl -s -o /dev/null -w "https://$DOMAIN/      -> HTTP %{http_code}\n" "https://$DOMAIN/" || true
curl -s -o /dev/null -w "https://$DOMAIN/api/  -> HTTP %{http_code}\n" "https://$DOMAIN/api/" || true
echo "Log: /tmp/ngrok.log"
