#!/usr/bin/env bash
# Prueba el módulo de administración de usuarios con un admin (ALEXJUT).
set -uo pipefail
BASE="http://localhost:8090"

TOKEN=$(curl -s -X POST "$BASE/api/auth/login/" -H 'Content-Type: application/json' \
  --data-binary '{"codigo_usuario":"alexjut","password":"alexjut1030"}' \
  | sed -n 's/.*"access":"\([^"]*\)".*/\1/p')
[ -z "$TOKEN" ] && { echo "ERROR: sin token"; exit 1; }
AUTH="Authorization: Bearer $TOKEN"
echo "Login admin OK"

echo "GET /api/usuarios/ (lista)"
curl -s -H "$AUTH" "$BASE/api/usuarios/" -w "\n-> HTTP %{http_code}\n" | head -c 400
echo ""
echo "GET /api/usuarios/perfiles/"
curl -s -H "$AUTH" "$BASE/api/usuarios/perfiles/" -w "\n-> HTTP %{http_code}\n" | head -c 400
echo ""
echo "Control: un encuestador NO debe poder (espera 403)"
T2=$(curl -s -X POST "$BASE/api/auth/login/" -H 'Content-Type: application/json' \
  --data-binary '{"codigo_usuario":"ENC001","password":"SrniTest2026!"}' \
  | sed -n 's/.*"access":"\([^"]*\)".*/\1/p')
curl -s -o /dev/null -w "  ENC001 -> /api/usuarios/ -> HTTP %{http_code}\n" -H "Authorization: Bearer $T2" "$BASE/api/usuarios/"
