#!/usr/bin/env bash
# ------------------------------------------------------------
# Construye las imágenes, levanta el stack y aplica migraciones.
# ------------------------------------------------------------
set -euo pipefail
ROOT="${1:-$HOME/caracterizacion}"
cd "$ROOT"
COMPOSE="docker compose --env-file $ROOT/.env -f infra/deploy/docker-compose.caracterizacion.yml"

echo "=== Construyendo imágenes ==="
$COMPOSE build

echo "=== Levantando el stack ==="
$COMPOSE up -d

echo "=== Esperando a que PostgreSQL esté sano ==="
for i in $(seq 1 30); do
  if $COMPOSE exec -T cz_postgres pg_isready -U "${DB_USER:-srni_app}" >/dev/null 2>&1; then
    echo "  PostgreSQL listo."; break
  fi
  sleep 2
done

echo "=== Migraciones ==="
$COMPOSE exec -T cz_backend python manage.py migrate --noinput

echo "=== collectstatic ==="
$COMPOSE exec -T cz_backend python manage.py collectstatic --noinput

echo "=== Estado del stack ==="
$COMPOSE ps
