#!/usr/bin/env bash
# ============================================================
# Despliegue del CÓDIGO del backend a producción (30.0.1.109)
# ------------------------------------------------------------
# Para cambios de Python, que van HORNEADOS en la imagen. NO recarga
# instrumentos, NO reconstruye el frontend, NO toca la base de datos más
# allá de aplicar migraciones.
#
#   bash infra/deploy/scripts/desplegar-backend-codigo.sh
#
# ─── Por qué existe, teniendo deploy-all.sh al lado ────────────────────
# `deploy-all.sh` ejecuta `40-cargar-datos.sh`, que recarga los 8
# instrumentos con `cargar_perfil --reemplazar`. Eso purga capítulos en
# cascada y **rompe la sincronía con la APK**, que trae los mismos
# instrumentos con identificadores fijos. Y reconstruye el frontend, que
# no es de este equipo. Para un cambio de Python nada de eso hace falta,
# y el disco del servidor está al límite (compartido con otros cuatro
# despliegues).
#
# Y `30-desplegar.sh` hace `compose build` sin servicio: construye todo.
#
# ─── Las tres trampas que este script evita, todas medidas ────────────
# 1. `--env-file .env` es obligatorio. Compose v2 busca el `.env` en la
#    carpeta del archivo de compose (infra/deploy/), que NO lo tiene: el
#    real vive en ~/caracterizacion/.env. Sin la bandera, SECRET_KEY
#    queda vacío, gunicorn entra en ciclo de reinicio y prod responde 502.
# 2. Hay CUATRO contenedores con la misma imagen — cz_backend, cz_celery,
#    cz_celery_padron y cz_beat—. Recrear solo el primero deja a los
#    trabajadores corriendo el código viejo, y eso es peor que no
#    desplegar: el sistema queda en dos versiones a la vez.
# 3. Al recrear cz_backend cambia su dirección en la red de Docker, y
#    cz_nginx la resuelve UNA vez al arrancar. Sin reiniciarlo, todo
#    /api/ responde 502 aunque gunicorn esté sano. Ojo: `/` sigue dando
#    200 porque lo sirve nginx, así que la verificación va contra /api/.
#
# Variables opcionales:
#   SSH_KEY      (default ~/.ssh/id_srni_servidor)
#   DEPLOY_HOST  (default admin_rni@30.0.1.109)
# ============================================================
set -euo pipefail

KEY="${SSH_KEY:-$HOME/.ssh/id_srni_servidor}"
HOST="${DEPLOY_HOST:-admin_rni@30.0.1.109}"
RAIZ='$HOME/caracterizacion'
COMPOSE="docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml"
#: Los cuatro que comparten la imagen. Ver trampa 2.
SERVICIOS='cz_backend cz_celery cz_celery_padron cz_beat'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

[ -f "$KEY" ] || { echo "ERROR: no se encuentra la llave SSH: $KEY" >&2; exit 1; }

echo ">> Verificando conexión SSH a $HOST (¿VPN conectada?) ..."
if ! ssh -i "$KEY" -o ConnectTimeout=12 -o BatchMode=yes "$HOST" 'echo ok' >/dev/null 2>&1; then
  echo "ERROR: no hay conexión SSH. Conecta la VPN e inténtalo de nuevo." >&2
  exit 1
fi

# El disco es el cuello: 61 GB compartidos con otros cuatro despliegues, y si
# Postgres se queda sin espacio se detiene PARA TODOS. Un `build` necesita
# margen para la capa nueva; abortar acá es mucho más barato que a mitad.
echo ">> Espacio libre antes de construir:"
ssh -i "$KEY" "$HOST" 'df -h / /datos | tail -n +1'
LIBRE_GB="$(ssh -i "$KEY" "$HOST" "df --output=avail -BG / | tail -1 | tr -dc '0-9'")"
if [ "${LIBRE_GB:-0}" -lt 5 ]; then
  echo "ERROR: quedan ${LIBRE_GB} GB en la raíz. Libera antes de construir:" >&2
  echo "       ssh -i $KEY $HOST 'docker builder prune -f'   # recupera ~2 GB, sin riesgo" >&2
  exit 1
fi

echo ">> Subiendo el backend del HEAD actual ..."
# `git archive` exporta exactamente lo versionado: sin __pycache__, sin media/,
# sin .env. Copiar la carpeta entera se llevaría el entorno virtual y la caché.
git archive --format=tar.gz -o /tmp/srni-backend-deploy.tar.gz HEAD srni-backend
scp -i "$KEY" /tmp/srni-backend-deploy.tar.gz "$HOST:~/srni-backend-deploy.tar.gz"
ssh -i "$KEY" "$HOST" "cd $RAIZ && tar xzf ~/srni-backend-deploy.tar.gz"

echo ">> Construyendo la imagen del backend ..."
ssh -i "$KEY" "$HOST" "cd $RAIZ && $COMPOSE build cz_backend"

echo ">> Recreando los cuatro contenedores que usan esa imagen ..."
ssh -i "$KEY" "$HOST" "cd $RAIZ && $COMPOSE up -d --force-recreate $SERVICIOS"

echo ">> Aplicando migraciones ..."
ssh -i "$KEY" "$HOST" "cd $RAIZ && $COMPOSE exec -T cz_backend python manage.py migrate --noinput"

echo ">> Reiniciando cz_nginx (ver trampa 3) ..."
ssh -i "$KEY" "$HOST" 'docker restart cz_nginx'

echo ">> Verificando ..."
# Contra /api/, no contra la raíz: nginx sirve `/` por su cuenta y daría 200
# aunque el backend estuviera caído.
sleep 5
CODIGO="$(ssh -i "$KEY" "$HOST" 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/')"
ssh -i "$KEY" "$HOST" 'docker ps --format "{{.Names}}\t{{.Status}}" | grep "^cz_"'

echo ""
if [ "$CODIGO" = "200" ]; then
  echo ">> Despliegue terminado. /api/ responde $CODIGO ✅"
else
  echo ">> ⚠️  /api/ responde $CODIGO (se esperaba 200)." >&2
  echo "   Revisar:  ssh -i $KEY $HOST 'docker logs --tail 50 cz_backend'" >&2
  echo "   Si es 502: confirmar que el .env está presente y que cz_nginx reinició." >&2
  exit 1
fi
