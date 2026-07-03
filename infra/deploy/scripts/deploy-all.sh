#!/usr/bin/env bash
# ------------------------------------------------------------
# Orquestador del despliegue completo de caracterización.
# Ejecuta en orden: secrets -> build frontend -> stack -> datos -> verificación.
# ------------------------------------------------------------
set -euo pipefail
ROOT="${1:-$HOME/caracterizacion}"
SCRIPTS="$ROOT/infra/deploy/scripts"

echo "############################################################"
echo "# Despliegue SRNI Caracterización — $(date)"
echo "# Raíz: $ROOT"
echo "############################################################"

bash "$SCRIPTS/10-generar-secrets.sh" "$ROOT"
set -a; . "$ROOT/.env"; set +a          # exportar variables para compose
bash "$SCRIPTS/20-build-frontend.sh" "$ROOT"
bash "$SCRIPTS/30-desplegar.sh"     "$ROOT"
bash "$SCRIPTS/40-cargar-datos.sh"  "$ROOT"
bash "$SCRIPTS/50-verificar.sh"     "$ROOT"

echo ""
echo "############################################################"
echo "# Despliegue terminado."
echo "# Panel web (local al servidor):  http://localhost:8090/"
echo "# Acceso externo: requiere que la OTI abra el puerto 8090,"
echo "#   o usar túnel SSH:  ssh -L 8090:localhost:8090 admin_rni@30.0.1.109"
echo "############################################################"
