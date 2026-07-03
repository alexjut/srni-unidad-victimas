#!/usr/bin/env bash
# ------------------------------------------------------------
# Instala ngrok (si falta) y prepara Django para aceptar dominios ngrok.
# NO arranca ngrok ni maneja el authtoken (eso se hace aparte, por seguridad).
# ------------------------------------------------------------
set -euo pipefail
ROOT="${1:-$HOME/caracterizacion}"
cd "$ROOT"
COMPOSE="docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml"

# 1) Instalar ngrok en ~/bin si no está
mkdir -p "$HOME/bin"
if ! command -v ngrok >/dev/null 2>&1 && [ ! -x "$HOME/bin/ngrok" ]; then
  echo "Instalando ngrok..."
  curl -sSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -o /tmp/ngrok.tgz
  tar -xzf /tmp/ngrok.tgz -C "$HOME/bin"
  chmod +x "$HOME/bin/ngrok"
fi
"$HOME/bin/ngrok" version || { echo "ERROR: ngrok no quedó instalado"; exit 1; }

# 2) Asegurar dominios ngrok en ALLOWED_HOSTS del .env (idempotente)
if ! grep -q 'ngrok' .env; then
  sed -i 's|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=30.0.1.109,localhost,127.0.0.1,.ngrok-free.app,.ngrok.app,.ngrok.io|' .env
  echo "ALLOWED_HOSTS actualizado con dominios ngrok."
else
  echo "ALLOWED_HOSTS ya incluye ngrok."
fi

# 3) Recrear backend para tomar el nuevo ALLOWED_HOSTS + reiniciar nginx
echo "Recreando backend/celery con el nuevo entorno..."
$COMPOSE up -d cz_backend cz_celery
sleep 6
$COMPOSE restart cz_nginx
echo "Listo. ngrok instalado y Django acepta dominios ngrok."
echo "Siguiente: agregar authtoken y arrancar ngrok (scripts aparte)."
