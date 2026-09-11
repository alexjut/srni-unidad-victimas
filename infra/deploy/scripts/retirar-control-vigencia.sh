#!/usr/bin/env bash
# ============================================================
# Retira (o repone) el control de vigencia de la caracterización en prod
# ------------------------------------------------------------
#   bash infra/deploy/scripts/retirar-control-vigencia.sh retirar
#   bash infra/deploy/scripts/retirar-control-vigencia.sh reponer
#   bash infra/deploy/scripts/retirar-control-vigencia.sh estado
#
# ─── Qué hace ──────────────────────────────────────────────────────────
# Mueve UNA variable en ~/caracterizacion/.env del servidor y recrea los
# contenedores que la leen:
#
#   VIGENCIA_BLOQUEO_ACTIVO=True    → la regla de los dos años está en pie
#   VIGENCIA_BLOQUEO_ACTIVO=False   → retirada: cualquier persona del padrón
#                                     se caracteriza sin autorización, sin
#                                     radicado y sin soporte
#
# NO reconstruye la imagen, NO toca el código, NO toca la base de datos.
# Volver atrás es correr este mismo script con `reponer`.
#
# ─── Por qué es un script aparte del despliegue ───────────────────────
# La regla la define el Manual de Usuario §5.1.1, que es documento
# misional. Retirarla es una decisión del proceso de caracterización, no
# de la ingeniería, y no puede ocurrir como efecto secundario de que
# alguien despliegue. Separarlo deja el acto con su propia fecha, su
# propio responsable y su propia línea en el historial del servidor.
#
# Lo pidió el equipo de caracterización el 11-sep-2026. La constancia de
# los efectos está en docs/gestion/correo_retiro_control_vigencia_2026-09-11.md
# y el detalle técnico en docs/operacion/plan_registro_silencioso_vigencia.md
#
# ─── Lo que NO se pierde al retirarlo ─────────────────────────────────
# Cada caracterización hecha sobre una ficha que aún estaba vigente queda
# en `encuestas.RecaracterizacionVigente`, escrita por el sistema al
# cerrar la encuesta: quién, cuándo, sobre quién, por qué ruta, la fecha
# anterior y cuántos días le faltaban por vencer.
#
# ─── Ni la APK ni el panel necesitan versión nueva ────────────────────
# La precarga de la jornada entrega el campo que el celular usa SIN SEÑAL
# para decidir si deja continuar, así que mover esta variable alcanza para
# que el cambio llegue al territorio en las aplicaciones ya instaladas.
# Lo que un teléfono ya precargado necesita es volver a iniciar sesión.
# ============================================================
set -euo pipefail

ACCION="${1:-estado}"
KEY="${SSH_KEY:-$HOME/.ssh/id_srni_servidor}"
HOST="${DEPLOY_HOST:-admin_rni@30.0.1.109}"
RAIZ='$HOME/caracterizacion'
COMPOSE="docker compose --env-file .env -f infra/deploy/docker-compose.caracterizacion.yml"
#: Los cuatro contenedores que corren el código Python y leen esta variable.
#: Dejar fuera a los trabajadores los deja decidiendo con el criterio viejo.
SERVICIOS='cz_backend cz_celery cz_celery_padron cz_beat'
VAR='VIGENCIA_BLOQUEO_ACTIVO'

[ -f "$KEY" ] || { echo "ERROR: no se encuentra la llave SSH: $KEY" >&2; exit 1; }

case "$ACCION" in
  retirar) VALOR='False' ;;
  reponer) VALOR='True'  ;;
  estado)  VALOR='' ;;
  *) echo "Uso: $0 {retirar|reponer|estado}" >&2; exit 2 ;;
esac

echo ">> Verificando conexión SSH a $HOST (¿VPN conectada?) ..."
if ! ssh -i "$KEY" -o ConnectTimeout=12 -o BatchMode=yes "$HOST" 'echo ok' >/dev/null 2>&1; then
  echo "ERROR: no hay conexión SSH. Conecta la VPN e inténtalo de nuevo." >&2
  exit 1
fi

mostrar_estado() {
  echo ">> Valor en el .env del servidor:"
  ssh -i "$KEY" "$HOST" "grep -E '^${VAR}=' $RAIZ/.env || echo '  (no está en el .env → vale True, el default del código)'"
  echo ">> Valor que efectivamente ve Django:"
  # Se pregunta al proceso, no al archivo: un .env editado sin recrear los
  # contenedores no cambia nada, y esa diferencia es justo la que engaña.
  # `manage.py shell -c` resuelve el módulo de settings por su cuenta (en prod es
  # `srni.settings.servidor`, que hereda de production y de base). Escribirlo a mano
  # acá sería un segundo lugar donde ese nombre puede quedar desactualizado.
  ssh -i "$KEY" "$HOST" "docker exec cz_backend python manage.py shell -c \"
from django.conf import settings
activo = settings.VIGENCIA['BLOQUEO_ACTIVO']
print('  BLOQUEO_ACTIVO =', activo, '->', 'la regla de los dos anios ESTA EN PIE' if activo else 'el control esta RETIRADO')
\"" 2>/dev/null || echo "  (no se pudo consultar el proceso)"
}

if [ "$ACCION" = 'estado' ]; then
  mostrar_estado
  exit 0
fi

echo ">> Estado ANTES del cambio:"
mostrar_estado

echo ""
echo ">> Escribiendo ${VAR}=${VALOR} en $RAIZ/.env ..."
# Respaldo con marca de la acción, no con fecha: el historial de shell del
# servidor ya tiene la hora, y un nombre estable no llena el disco de copias.
ssh -i "$KEY" "$HOST" "
  cd $RAIZ &&
  cp .env .env.antes-de-${ACCION}-vigencia &&
  if grep -qE '^${VAR}=' .env; then
    sed -i 's/^${VAR}=.*/${VAR}=${VALOR}/' .env
  else
    printf '\n# Control de vigencia (Manual de Usuario 5.1.1) — ver plan_registro_silencioso_vigencia.md\n${VAR}=${VALOR}\n' >> .env
  fi &&
  grep -E '^${VAR}=' .env
"

echo ">> Recreando los contenedores que leen la variable ..."
ssh -i "$KEY" "$HOST" "cd $RAIZ && $COMPOSE up -d --force-recreate $SERVICIOS"

echo ">> Reiniciando cz_nginx (al recrear el backend cambia su IP en la red docker) ..."
ssh -i "$KEY" "$HOST" 'docker restart cz_nginx'

sleep 6
echo ""
echo ">> Estado DESPUÉS del cambio:"
mostrar_estado

CODIGO="$(ssh -i "$KEY" "$HOST" 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/')"
echo ">> /api/ responde $CODIGO"
if [ "$CODIGO" != "200" ]; then
  echo "   ⚠️  Se esperaba 200. Revisar: ssh -i $KEY $HOST 'docker logs --tail 50 cz_backend'" >&2
  echo "   Si es 502, confirmar que el .env sigue completo:" >&2
  echo "     ssh -i $KEY $HOST 'grep -c . $RAIZ/.env; diff $RAIZ/.env $RAIZ/.env.antes-de-${ACCION}-vigencia'" >&2
  exit 1
fi

echo ""
if [ "$ACCION" = 'retirar' ]; then
  cat <<'FIN'
>> Control de vigencia RETIRADO ✅

   Qué verificar en la APK, en este orden:
     1. Cerrar sesión y volver a entrar — la precarga se rehace y es ella la
        que le dice al teléfono quién puede caracterizarse sin señal.
     2. Buscar una persona con caracterización de hace menos de dos años:
        debe salir habilitada, sin el mensaje de excepción.
     3. Conformar el hogar: si lo creó otro encuestador, debe continuar sin
        el aviso de reasignación.
     4. Cerrar una caracterización y confirmar que quedó la fila del libro:
        docker exec cz_backend python manage.py shell -c \
          "from apps.encuestas.models import RecaracterizacionVigente as R; print(R.objects.count())"

   Para volver atrás:  bash infra/deploy/scripts/retirar-control-vigencia.sh reponer
FIN
else
  echo ">> Control de vigencia REPUESTO ✅ — la regla de los dos años vuelve a aplicar."
  echo "   Las filas del libro de recaracterizaciones se conservan: son el histórico."
fi
