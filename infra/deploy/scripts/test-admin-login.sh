#!/usr/bin/env bash
# Prueba el login del /admin/ de Django (CSRF) con mayúsculas y minúsculas.
set -uo pipefail
BASE="https://prod-caracterizacion.ngrok.app"

try_login() {
  local USER="$1"; local J="/tmp/cj_${USER}.txt"; rm -f "$J"
  local HTML TOKEN code
  HTML=$(curl -s -c "$J" "$BASE/admin/login/")
  TOKEN=$(echo "$HTML" | sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p' | head -1)
  code=$(curl -s -o /dev/null -w '%{http_code}' -b "$J" \
    -e "$BASE/admin/login/" -H "Origin: $BASE" \
    --data "csrfmiddlewaretoken=${TOKEN}&username=${USER}&password=alexjut1030&next=/admin/" \
    "$BASE/admin/login/")
  echo "  usuario '${USER}' -> HTTP ${code}  (302 = LOGIN OK · 200 = credencial falla · 403 = CSRF falla)"
  rm -f "$J"
}

echo "Probando login al /admin/:"
try_login ALEXJUT
try_login alexjut
