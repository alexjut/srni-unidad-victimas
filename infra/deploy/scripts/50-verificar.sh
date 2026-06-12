#!/usr/bin/env bash
# ------------------------------------------------------------
# Verifica el despliegue: contenedores, HTTP local y conteos en BD.
# ------------------------------------------------------------
set -uo pipefail
ROOT="${1:-$HOME/caracterizacion}"
cd "$ROOT"
COMPOSE="docker compose --env-file $ROOT/.env -f infra/deploy/docker-compose.caracterizacion.yml"

echo "===== CONTENEDORES ====="
$COMPOSE ps

echo "===== HTTP LOCAL (puerto 8090) ====="
curl -sS -o /dev/null -w "  Panel web (/)        -> HTTP %{http_code}\n" http://localhost:8090/ || echo "  panel web: sin respuesta"
curl -sS -o /dev/null -w "  API (/api/)          -> HTTP %{http_code}\n" http://localhost:8090/api/ || true
curl -sS -o /dev/null -w "  Static (/static/)    -> HTTP %{http_code}\n" http://localhost:8090/static/admin/css/base.css || true

echo "===== CONTEOS EN BD ====="
$COMPOSE exec -T cz_backend python manage.py shell -c "
from apps.parametricas.models import Municipio, Departamento, TipoDocumento
from apps.formulario.models import Pregunta, Instrumento
print('  Departamentos:', Departamento.objects.count())
print('  Municipios:   ', Municipio.objects.count())
print('  Tipos doc:    ', TipoDocumento.objects.count())
print('  Instrumentos: ', Instrumento.objects.count())
print('  Preguntas:    ', Pregunta.objects.count())
"

echo "===== PRUEBA DE LOGIN (usuario ENC001) ====="
curl -sS -X POST http://localhost:8090/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"codigo_usuario":"ENC001","password":"SrniTest2026!"}' \
  -o /dev/null -w "  POST /api/auth/login/ -> HTTP %{http_code}\n" || true

echo "Verificación finalizada."
