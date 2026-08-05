#!/usr/bin/env bash
# Vigilante de la carga del universo de víctimas — 5-ago-2026.
#
# Por qué existe
# ─────────────
# `cargar_universo_victimas` termina la fase 1 (cargar) y entra sola a la fase 2,
# cuya primera instrucción es un UPDATE sobre las 12 M de filas
# (`es_preferida=True`). Con `es_preferida` indexada, Postgres reescribe el heap y
# los 12 índices: pide ~19 GB y al terminar la carga quedarán ~6 GB libres.
# El disco es COMPARTIDO con sidi, catalogo-si, uariv-auth y el proxy manager: un
# Postgres sin espacio se detiene y se lleva servicios de otros equipos.
#
# Este script mata el proceso cuando la fase 1 termina, ANTES de ese UPDATE.
# La fase 2 se corre después, aparte, con el parche que acota el reset.
#
# Ventana: entre el fin de la carga y el primer UPDATE hay varios minutos de solo
# lectura (el count de verificación, el GROUP BY sobre 12 M y el bucle de ~55 K
# grupos). El polling de 20 s entra de sobra.

set -u

LOG="${1:-/tmp/carga_universo_20260805_1623.log}"
VLOG=/tmp/vigilante_universo.log
MIN_GB_LIBRES=4          # último recurso: proteger el disco compartido
INTERVALO=20

decir() { echo "[$(date -u '+%F %T UTC')] $*" >> "$VLOG"; }

matar() {
  decir "MATANDO la carga: $1"
  # pkill puede no estar en la imagen (python:slim no trae procps), así que el
  # camino seguro es Python, que sí está. Manda SIGTERM al proceso cuyo cmdline
  # contiene el nombre del comando, sin tocar nada más.
  docker exec cz_backend python -c "
import os, signal
for pid in filter(str.isdigit, os.listdir('/proc')):
    try:
        cmd = open(f'/proc/{pid}/cmdline','rb').read().decode(errors='ignore')
    except OSError:
        continue
    if 'cargar_universo_victimas' in cmd and int(pid) != os.getpid():
        os.kill(int(pid), signal.SIGTERM)
        print('SIGTERM ->', pid)
" >> "$VLOG" 2>&1
  sleep 5
  decir "procesos que quedan: $(pgrep -fc cargar_universo_victimas || echo 0)"
  decir "disco: $(df -h / | tail -1)"
}

decir "vigilante arriba · log vigilado: $LOG · umbral disco: ${MIN_GB_LIBRES}G"

while true; do
  if ! pgrep -f 'manage.py cargar_universo_victimas' > /dev/null; then
    decir "el proceso ya no está (terminó o lo mataron). Vigilante fuera."
    decir "últimas líneas del log: $(tail -4 "$LOG" | tr '\n' ' | ')"
    exit 0
  fi

  # Fin de la fase 1: el resumen final imprime "  cargadas        : N".
  # El progreso periódico NO lleva dos puntos, así que no hay falso positivo.
  # Segundo patrón, por si acaso: el encabezado de la fase 2, que se imprime
  # antes del bucle de grupos y por tanto sigue estando antes del UPDATE.
  if grep -qE '^[[:space:]]+cargadas[[:space:]]+:' "$LOG" \
     || grep -q 'Documentos compartidos por' "$LOG"; then
    matar "la fase 1 terminó — se evita el UPDATE de 12 M filas"
    exit 0
  fi

  libres=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
  if [ "${libres:-99}" -lt "$MIN_GB_LIBRES" ]; then
    matar "quedan ${libres}G libres (<${MIN_GB_LIBRES}G): se corta para no tumbar Postgres"
    exit 0
  fi

  sleep "$INTERVALO"
done
