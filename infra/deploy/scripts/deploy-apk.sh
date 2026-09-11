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
#
#   # Subir una APK ya compilada, SIN volver a construir:
#   APK_LOCAL=/tmp/app-125.apk bash infra/deploy/scripts/deploy-apk.sh
#
# ─── Por qué existe APK_LOCAL ───────────────────────────────────────────
# El build corre en la nube y NO necesita VPN; el `scp` final sí. Cuando la
# VPN se cae a mitad —y se cae— sin esta variable habria que repetir los
# 10-15 minutos de compilacion para subir un artefacto que ya existe, y
# ademas quedaria con otro versionCode: `autoIncrement` sube en cada build,
# asi que la APK que alguien ya instalo y la que se publica dejarian de ser
# la misma. Con APK_LOCAL se sube exactamente la que se probo.
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

if [ -n "${APK_LOCAL:-}" ]; then
  [ -f "$APK_LOCAL" ] || { echo "ERROR: no existe $APK_LOCAL" >&2; exit 1; }
  # Un .apk es un zip: si el archivo quedó a medias —descarga cortada, que con la
  # VPN de la entidad pasa— la firma no está y el teléfono rechaza la instalación
  # sin decir por qué. Cuesta nada comprobarlo acá y evita un misterio en campo.
  if [ "$(head -c 2 "$APK_LOCAL")" != "PK" ]; then
    echo "ERROR: $APK_LOCAL no parece un .apk (no empieza por 'PK')." >&2
    exit 1
  fi
  cp "$APK_LOCAL" /tmp/app.apk
  echo "============================================================"
  echo "  Usando la APK ya compilada: $APK_LOCAL  ($(du -h /tmp/app.apk | cut -f1))"
  echo "  Sin build: se sube exactamente el artefacto que se probó."
  echo "============================================================"
else
  echo "============================================================"
  echo "  Build EAS — perfil '$PROFILE'  (tarda ~10-15 min)"
  echo "============================================================"
  npx eas-cli build --platform android --profile "$PROFILE" --non-interactive --wait --json > /tmp/eas-build.json

  # URL del artefacto (.apk). El JSON de EAS viene formateado (con espacios), así que
  # extraemos directamente la primera URL https://...apk (robusto ante el formato).
  APK_URL="$(grep -oE 'https://[^"]*\.apk' /tmp/eas-build.json | head -1)"
  [ -z "$APK_URL" ] && { echo "ERROR: no se encontró la URL del .apk en la respuesta de EAS"; cat /tmp/eas-build.json; exit 1; }
  echo "Artefacto: $APK_URL"

  echo "Descargando .apk..."
  curl -L "$APK_URL" -o /tmp/app.apk
  SIZE="$(du -h /tmp/app.apk | cut -f1)"
  echo "Descargado ($SIZE)."
fi

echo "Respaldando versión anterior y subiendo la nueva..."
ssh -i "$KEY" "$SERVER" "f=$DEST; [ -f \$f ] && cp \$f \$f.bak 2>/dev/null || true"
scp -i "$KEY" /tmp/app.apk "$SERVER:$DEST"

echo "============================================================"
echo "  APK desplegada ✅"
echo "  Descarga pública: https://prod-caracterizacion.ngrok.app/movil/app.apk"
echo "  Página + QR:      https://prod-caracterizacion.ngrok.app/descargar/"
echo "============================================================"
