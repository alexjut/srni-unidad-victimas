#!/usr/bin/env bash
# Verifica salida a internet del servidor para pulls de Docker / npm / pip.
set -uo pipefail
ok()  { echo "  OK   $1"; }
bad() { echo "  ---  $1 (sin acceso)"; }

echo "=== DNS ==="
getent hosts registry-1.docker.io >/dev/null 2>&1 && ok "DNS docker.io" || bad "DNS docker.io"

echo "=== HTTPS salientes (curl 5s) ==="
for url in https://registry-1.docker.io/v2/ https://pypi.org/simple/ https://registry.npmjs.org/ https://github.com; do
  code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  if [ "$code" != "000" ]; then ok "$url -> HTTP $code"; else bad "$url"; fi
done

echo "=== Imágenes Docker ya presentes en el servidor ==="
docker images --format '  {{.Repository}}:{{.Tag}}' | sort
