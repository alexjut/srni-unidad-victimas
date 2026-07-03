#!/usr/bin/env bash
# ------------------------------------------------------------
# Sube el código del HEAD actual (git archive) al servidor y ejecuta
# el despliegue completo. Pensado para correrse desde la máquina de
# desarrollo con la VPN conectada.
#
#   bash infra/deploy/scripts/subir-y-desplegar.sh
#
# Variables opcionales:
#   SSH_KEY      (default ~/.ssh/id_srni_servidor)
#   DEPLOY_HOST  (default admin_rni@30.0.1.109)
#   DEPLOY_DIR   (default ~/caracterizacion en el servidor)
# ------------------------------------------------------------
set -euo pipefail
KEY="${SSH_KEY:-$HOME/.ssh/id_srni_servidor}"
HOST="${DEPLOY_HOST:-admin_rni@30.0.1.109}"
DEST="${DEPLOY_DIR:-\$HOME/caracterizacion}"

echo ">> Verificando conexión SSH a $HOST (¿VPN conectada?) ..."
if ! ssh -i "$KEY" -o ConnectTimeout=12 -o BatchMode=yes "$HOST" 'echo ok' >/dev/null 2>&1; then
  echo "ERROR: no hay conexión SSH. Conecta la VPN e inténtalo de nuevo." >&2
  exit 1
fi

echo ">> Subiendo código (git archive HEAD) → $DEST ..."
git archive --format=tar HEAD | ssh -i "$KEY" "$HOST" "mkdir -p $DEST && tar -x -C $DEST"

echo ">> Ejecutando deploy-all.sh en el servidor ..."
ssh -i "$KEY" "$HOST" "cd $DEST && bash infra/deploy/scripts/deploy-all.sh"

echo ">> Reiniciando cz_nginx (re-resuelve IP del backend tras rebuild) ..."
ssh -i "$KEY" "$HOST" "cd $DEST && docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml restart cz_nginx"

echo ""
echo ">> Despliegue terminado."
echo ">> Probar por túnel:  ssh -i $KEY -L 8090:localhost:8090 $HOST  → http://localhost:8090/"
