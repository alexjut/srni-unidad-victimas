#!/usr/bin/env bash
# Prueba autenticada end-to-end contra el despliegue local (puerto 8090).
set -uo pipefail
BASE="http://localhost:8090"

echo "1) Login ENC001..."
TOKEN=$(curl -s -X POST "$BASE/api/auth/login/" \
  -H 'Content-Type: application/json' \
  --data-binary '{"codigo_usuario":"ENC001","password":"SrniTest2026!"}' \
  | sed -n 's/.*"access":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then echo "   ERROR: no se obtuvo token"; exit 1; fi
echo "   OK (token de ${#TOKEN} chars)"
AUTH="Authorization: Bearer $TOKEN"

echo "2) GET /api/parametricas/departamentos/"
curl -s -o /dev/null -w "   -> HTTP %{http_code}\n" -H "$AUTH" "$BASE/api/parametricas/departamentos/"

echo "3) Buscar victima mock CC 9990100001"
curl -s -H "$AUTH" "$BASE/api/victimas/buscar/?tipo_documento=CC&numero_documento=9990100001" \
  -w "\n   -> HTTP %{http_code}\n" | head -c 400
echo ""

echo "4) GET /api/auditoria/logs/ (requiere permiso)"
curl -s -o /dev/null -w "   -> HTTP %{http_code}\n" -H "$AUTH" "$BASE/api/auditoria/logs/"

echo "Prueba autenticada finalizada."
