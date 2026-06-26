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
run cargar_puntos_atencion

echo "===== INSTRUMENTOS ====="
run crear_instrumentos_base
run cargar_capitulo_control
# Territorial V7: cargar desde el FIXTURE (UUIDs deterministas uuid5 que coinciden
# con el bundle del APK), NO desde cargar_territorial_v7 (comando hardcodeado con
# uuid4 aleatorio). Si se siembra con el comando viejo en una BD limpia, los UUIDs
# del backend no coinciden con los del APK y el backend rechaza TODAS las respuestas
# del móvil con HTTP 400. Ver docs/sprints/sprint-15.md.
run cargar_perfil --instrumento TERRITORIAL
run cargar_buenaventura_v7
run cargar_san_andres_v7
run cargar_telefonico_v8
run cargar_diccionario_v8
run cargar_rural_etnico_v1
run cargar_urbano_etnico_v1

echo "===== USUARIO DE PRUEBA ====="
run crear_usuario_prueba --codigo ENC001 --password "SrniTest2026!"

echo "Carga de datos finalizada."
