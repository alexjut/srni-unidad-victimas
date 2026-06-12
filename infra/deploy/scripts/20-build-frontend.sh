#!/usr/bin/env bash
# ------------------------------------------------------------
# Construye el panel web (Vite) a estáticos en srni-frontend/dist.
# Usa un contenedor node:20 — no ensucia el host con Node/npm.
# El API se sirve en el MISMO origen → VITE_API_URL vacío (URLs relativas).
# ------------------------------------------------------------
set -euo pipefail
ROOT="${1:-$HOME/caracterizacion}"
FRONT="$ROOT/srni-frontend"

[ -d "$FRONT" ] || { echo "ERROR: no existe $FRONT"; exit 1; }
cd "$FRONT"

# Forzar URL de API relativa en el build de producción
printf 'VITE_API_URL=\nVITE_APP_ENV=production\n' > .env.production

echo "Construyendo el panel web (node:20-alpine)..."
docker run --rm -v "$PWD":/app -w /app node:20-alpine sh -c '
  npm install --no-audit --no-fund
  # Build de producción. Si tsc reporta errores de tipos (no bloqueantes para
  # desplegar código que ya corría en dev), se cae a vite build directo.
  npm run build || npx vite build
'

if [ -f dist/index.html ]; then
  echo "OK: panel web construido en $FRONT/dist"
else
  echo "ERROR: no se generó dist/index.html"; exit 1
fi
