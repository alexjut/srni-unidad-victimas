#!/bin/bash
#
# Respaldo FISICO semanal de la base de SICAV, con rotacion de 3 copias.
#
# ─────────────────────────────────────────────────────────────────────────────
# POR QUE FISICO Y NO pg_dump
# ─────────────────────────────────────────────────────────────────────────────
# victimas_victima tiene 26 indices (5,9 GB) sobre 5,9 M de filas, mas los del
# universo de 12 M. Un dump logico no guarda indices, solo su definicion: al
# restaurar hay que reconstruirlos todos, y esta maquina escribe indices lento
# (medido en la migracion 0021: ~10.300 filas/min, 260 MB de WAL/min). O sea que
# un pg_dump se restaura en muchas horas.
#
# pg_basebackup copia el directorio tal cual, indices incluidos: restaurar es
# descomprimir sobre un PGDATA vacio y arrancar. Minutos.
#
# `-X fetch` mete dentro del tar el WAL generado durante la copia, para que el
# respaldo sea consistente y arranque solo, sin depender de archivos sueltos.
#
# ─────────────────────────────────────────────────────────────────────────────
# POR QUE NO SOBRESCRIBE EL ANTERIOR DIRECTAMENTE
# ─────────────────────────────────────────────────────────────────────────────
# Se pidio "rotacion de 3, sobrescribiendo el anterior". El efecto es ese —nunca
# hay mas de 3 y el espacio se recicla— pero el orden importa: se escribe a un
# `.parcial`, se VERIFICA, y solo entonces se borra el mas antiguo.
#
# Si se pisara la copia vieja de entrada y el respaldo fallara a la mitad —disco
# lleno, contenedor caido, la VPN— el resultado seria quedarse sin ninguna copia
# buena. Un respaldo a medias es peor que no tener respaldo, porque parece uno.
#
# ─────────────────────────────────────────────────────────────────────────────
# DONDE ESCRIBE
# ─────────────────────────────────────────────────────────────────────────────
# En /datos, nunca en el disco raiz: el raiz vive al 76% y ahi no cabe.
# OJO: /datos es de root. El directorio /datos/respaldos se creo una vez a
# nombre del uid 1001 pasando por Docker, porque `sudo` en este servidor pide
# autenticacion interactiva y desde cron/SSH no hay donde escribirla:
#
#   docker run --rm -v /datos:/host postgres:16-alpine \
#     sh -c 'mkdir -p /host/respaldos && chown 1001:1001 /host/respaldos'
#
# ─────────────────────────────────────────────────────────────────────────────
# COMO SE PROGRAMA: systemd, NO cron
# ─────────────────────────────────────────────────────────────────────────────
# Este servidor NO tiene cron instalado —ni el binario `crontab` ni el servicio—,
# asi que va con un timer de usuario de systemd. Sale ganando: `Persistent=true`
# recupera la ejecucion si el servidor estuvo apagado el domingo a las 2, cosa
# que cron no hace.
#
#   respaldo-sicav.service  +  respaldo-sicav.timer   (en este mismo directorio)
#   se copian a ~/.config/systemd/user/ y:
#     systemctl --user daemon-reload
#     systemctl --user enable --now respaldo-sicav.timer
#
# ⚠️ Hace falta UNA vez, y solo esto necesita root:
#     sudo loginctl enable-linger admin_rni
# Sin `linger`, el systemd del usuario se apaga al cerrar la sesion SSH y el
# timer no dispara nunca. Se comprueba con `loginctl show-user admin_rni`.

# cron arranca con un PATH minimo y sin docker en el.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

set -uo pipefail

DEST=/datos/respaldos
COPIAS=3                 # cuantas se conservan
MINIMO_LIBRE_GB=25       # si no cabe una copia entera, ni se empieza

STAMP=$(date +%Y%m%d_%H%M)
TAR="$DEST/base_$STAMP.tar.gz"
PARCIAL="$TAR.parcial"
LOG="$DEST/base_$STAMP.log"

mkdir -p "$DEST" 2>/dev/null

registrar() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" >> "$LOG"; }

registrar "=== respaldo semanal de SICAV ==="

# ── Comprobaciones antes de tocar nada ──────────────────────────────────────
if ! docker inspect -f '{{.State.Running}}' cz_postgres 2>/dev/null | grep -q true; then
    registrar "ABORTA: el contenedor cz_postgres no esta corriendo"
    exit 1
fi

libre_gb=$(df -BG --output=avail "$DEST" | tail -1 | tr -dc '0-9')
if [ "${libre_gb:-0}" -lt "$MINIMO_LIBRE_GB" ]; then
    registrar "ABORTA: solo ${libre_gb} GB libres en $DEST, se exigen $MINIMO_LIBRE_GB"
    registrar "        (no se borra ninguna copia: preferimos quedarnos sin la nueva)"
    exit 1
fi
registrar "espacio libre: ${libre_gb} GB — adelante"

# Restos de una corrida anterior que se corto a la mitad.
rm -f "$DEST"/*.parcial 2>/dev/null

# ── La copia ────────────────────────────────────────────────────────────────
registrar "copiando a $(basename "$PARCIAL") ..."
docker exec cz_postgres sh -c 'pg_basebackup -U $POSTGRES_USER -D - -Ft -z -X fetch -P' \
    > "$PARCIAL" 2>> "$LOG"
rc=$?

if [ $rc -ne 0 ]; then
    mv -f "$PARCIAL" "$DEST/base_$STAMP.FALLIDO" 2>/dev/null
    registrar "FALLO: pg_basebackup salio con codigo $rc"
    registrar "       NO se borro ninguna copia anterior; quedan las que habia"
    exit $rc
fi

# ── Verificar antes de darlo por bueno ──────────────────────────────────────
# Lee el archivo entero y comprueba los CRC. Un respaldo que nadie abrio no
# cuenta como respaldo.
registrar "verificando integridad (gzip -t) ..."
if ! gzip -t "$PARCIAL" 2>>"$LOG"; then
    mv -f "$PARCIAL" "$DEST/base_$STAMP.CORRUPTO" 2>/dev/null
    registrar "FALLO: el archivo no pasa la verificacion, se marca CORRUPTO"
    registrar "       NO se borro ninguna copia anterior"
    exit 1
fi

mv -f "$PARCIAL" "$TAR"
registrar "OK: $(ls -lh "$TAR" | awk '{print $5}') — verificado"

# ── Rotacion: recien ahora se suelta lo viejo ───────────────────────────────
sobrantes=$(ls -1t "$DEST"/base_*.tar.gz 2>/dev/null | tail -n +$((COPIAS + 1)))
if [ -n "$sobrantes" ]; then
    while IFS= read -r viejo; do
        [ -z "$viejo" ] && continue
        registrar "rotacion: se elimina $(basename "$viejo")"
        rm -f "$viejo" "${viejo%.tar.gz}.log"
    done <<< "$sobrantes"
else
    registrar "rotacion: nada que eliminar (hay $(ls -1 "$DEST"/base_*.tar.gz 2>/dev/null | wc -l) copias)"
fi

registrar "copias disponibles:"
ls -lht "$DEST"/base_*.tar.gz 2>/dev/null | awk '{print "    ", $9, $5, $6, $7, $8}' >> "$LOG"
df -h "$DEST" | tail -1 >> "$LOG"
registrar "fin"

exit 0
