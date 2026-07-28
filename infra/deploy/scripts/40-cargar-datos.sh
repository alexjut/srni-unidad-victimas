#!/usr/bin/env bash
# ------------------------------------------------------------
# Carga paramétricas, instrumentos y un usuario de prueba.
# Tolerante a fallos: si un comando falla, lo reporta y sigue.
# ------------------------------------------------------------
set -uo pipefail
ROOT="${1:-$HOME/caracterizacion}"
cd "$ROOT"
COMPOSE="docker compose --env-file $ROOT/.env -f infra/deploy/docker-compose.caracterizacion.yml"

run() {
  echo ">>> manage.py $*"
  if $COMPOSE exec -T cz_backend python manage.py "$@"; then
    echo "    OK"
  else
    echo "    (FALLÓ — revisar): $*"
  fi
}

echo "===== PARAMÉTRICAS ====="
run cargar_tipos_documento
run cargar_departamentos_municipios
run cargar_direcciones_territoriales
# Catálogo REAL de Oracle (266 puntos, pendiente 3a.11). Sustituye al placeholder
# `cargar_puntos_atencion` (2 puntos inventados por DT): sus nombres no existen en
# Oracle y el cruce territorial es por nombre, así que un hogar atendido en uno de
# ellos no resolvía su territorio. El comando nuevo desactiva los que queden.
run cargar_puntos_atencion_oracle

echo "===== INSTRUMENTOS ====="
run crear_instrumentos_base
# TODOS los perfiles se cargan desde su FIXTURE con `cargar_perfil --reemplazar`.
# Los fixtures traen UUID de PREGUNTA deterministas que COINCIDEN con los bundles
# empaquetados en el APK (ver srni-backend/scripts/sincronizar_ids_fixture_desde_bundle.py).
# Sin esto, los comandos legacy (cargar_<perfil>_v*) hardcodeaban otra versión con uuid4
# aleatorio y el backend rechazaba TODAS las respuestas del móvil con HTTP 400
# (ver docs/sprints/sprint-15.md). NO reintroducir cargar_buenaventura_v7/etc.
# --reemplazar purga los capítulos previos (cascade) para no dejar preguntas huérfanas
# al cambiar de versión/reconstrucción.
for COD in TERRITORIAL BUENAVENTURA SAN_ANDRES URBANO_ETNICO ASISTENCIA RURAL_ETNICO TELEFONICO VICTIMAS_EXTERIOR; do
  run cargar_perfil --instrumento "$COD" --reemplazar
done
# El capítulo de control se re-agrega DESPUÉS del reemplazo (si no, lo purgaría).
run cargar_capitulo_control

echo "===== USUARIO DE PRUEBA ====="
run crear_usuario_prueba --codigo ENC001 --password "SrniTest2026!"

echo "Carga de datos finalizada."
