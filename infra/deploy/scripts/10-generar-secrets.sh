#!/usr/bin/env bash
# ------------------------------------------------------------
# Genera el archivo .env del despliegue con secretos aleatorios.
# Idempotente: si .env ya existe, NO lo sobrescribe.
# ------------------------------------------------------------
set -euo pipefail
ROOT="${1:-$HOME/caracterizacion}"
ENV_FILE="$ROOT/.env"
EXAMPLE="$ROOT/infra/deploy/.env.caracterizacion.example"

if [ -f "$ENV_FILE" ]; then
  echo "Ya existe $ENV_FILE — no se sobrescribe (conserva los passwords actuales)."
  exit 0
fi

[ -f "$EXAMPLE" ] || { echo "ERROR: no se encuentra la plantilla $EXAMPLE"; exit 1; }

SECRET_KEY="$(openssl rand -base64 50 | tr -d '\n')"
DB_PASSWORD="$(openssl rand -hex 24)"
REDIS_PASSWORD="$(openssl rand -hex 24)"
# Fernet key válida: 32 bytes en base64 url-safe (44 chars).
FIELD_KEY="$(openssl rand 32 | openssl base64 -A | tr '+/' '-_')"

cp "$EXAMPLE" "$ENV_FILE"
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASSWORD}|"                 "$ENV_FILE"
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|"                   "$ENV_FILE"
sed -i "s|^FIELD_ENCRYPTION_KEY=.*|FIELD_ENCRYPTION_KEY=${FIELD_KEY}|" "$ENV_FILE"
sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|"       "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Generado $ENV_FILE (permisos 600). Secretos aleatorios listos."
echo "Recuerda: este archivo NO se sube a git."
