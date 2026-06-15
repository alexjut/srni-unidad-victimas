#!/usr/bin/env bash
# ============================================================
# Build + despliegue de la APK (Opción A — desarrollo continuo)
# ------------------------------------------------------------
# Corre en la MÁQUINA DEL DESARROLLADOR (Git Bash / WSL / Linux).
# 1) Compila la APK en EAS (nube de Expo)  2) descarga el .apk
# 3) lo sube al servidor en /movil/app.apk (con respaldo de la anterior)
#
# Requisitos (una sola vez):
#   - Token de Expo en  ~/.eas-token   (o variable EXPO_TOKEN)
#   - Llave SSH del servidor en  ~/.ssh/id_srni_servidor  (o variable SSH_KEY)
#   - VPN de la entidad activa · node/npx · curl · ssh/scp
#
# Uso:
#   bash infra/deploy/scripts/deploy-apk.sh            # perfil preview (APK)
#   bash infra/deploy/scripts/deploy-apk.sh preview
# ============================================================
set -euo pipefail

PROFILE="${1:-preview}"
SERVER="admin_rni@30.0.1.109"
DEST="/home/admin_rni/caracterizacion/infra/deploy/movil/app.apk"
KEY="${SSH_KEY:-$HOME/.ssh/id_srni_servidor}"

# Raíz del repo (este script está en infra/deploy/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# --- Token de Expo (sin exponerlo: archivo o variable de entorno) ---
if [ -z "${EXPO_TOKEN:-}" ] && [ -f "$HOME/.eas-token" ]; then
  EXPO_TOKEN="$(tr -d '\r\n' < "$HOME/.eas-token")"
fi
[ -z "${EXPO_TOKEN:-}" ] && { echo "ERROR: falta EXPO_TOKEN (~/.eas-token o variable de entorno)"; exit 1; }
export EXPO_TOKEN
[ -f "$KEY" ] || { echo "ERROR: no se encuentra la llave SSH: $KEY"; exit 1; }

cd "$REPO_ROOT/srni-mobile"

echo "============================================================"
echo "  Build EAS — perfil '$PROFILE'  (tarda ~10-15 min)"
echo "============================================================"
npx eas-cli build --platform android --profile "$PROFILE" --non-interactive --wait --json > /tmp/eas-build.json

# URL del artefacto (.apk). Soporta varias claves según versión de EAS.
APK_URL="$(grep -o '"applicationArchiveUrl":"[^"]*"' /tmp/eas-build.json | head -1 | sed 's/.*:"//;s/"$//')"
[ -z "$APK_URL" ] && APK_URL="$(grep -o '"buildUrl":"[^"]*"' /tmp/eas-build.json | head -1 | sed 's/.*:"//;s/"$//')"
[ -z "$APK_URL" ] && { echo "ERROR: no se encontró la URL del .apk en la respuesta de EAS"; exit 1; }
echo "Artefacto: $APK_URL"

echo "Descargando .apk..."
curl -L "$APK_URL" -o /tmp/app.apk
SIZE="$(du -h /tmp/app.apk | cut -f1)"
echo "Descargado ($SIZE)."

echo "Respaldando versión anterior y subiendo la nueva..."
ssh -i "$KEY" "$SERVER" "f=$DEST; [ -f \$f ] && cp \$f \$f.bak 2>/dev/null || true"
scp -i "$KEY" /tmp/app.apk "$SERVER:$DEST"

echo "============================================================"
echo "  APK desplegada ✅"
echo "  Descarga pública: https://prod-caracterizacion.ngrok.app/movil/app.apk"
echo "  Página + QR:      https://prod-caracterizacion.ngrok.app/descargar/"
echo "============================================================"
