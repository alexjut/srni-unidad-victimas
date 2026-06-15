#!/usr/bin/env bash
# Verifica qué devuelven los endpoints del panel (con token admin).
set -uo pipefail
BASE="http://localhost:8090"
TOKEN=$(curl -s -X POST "$BASE/api/auth/login/" -H 'Content-Type: application/json' \
  --data-binary '{"codigo_usuario":"alexjut","password":"alexjut1030"}' \
  | sed -n 's/.*"access":"\([^"]*\)".*/\1/p')
[ -z "$TOKEN" ] && { echo "sin token"; exit 1; }
A="Authorization: Bearer $TOKEN"
for ep in "/api/hogares/" "/api/encuestas/" "/api/reportes/" "/api/hogares/?estado=ACTIVO"; do
  echo "== GET $ep =="
  curl -s -H "$A" "$BASE$ep" -w "\n[HTTP %{http_code}]\n" | head -c 350
  echo ""
done
