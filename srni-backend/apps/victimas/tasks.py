"""
Tareas periódicas del padrón de víctimas.

El circuito completo, y dónde entra cada tarea:

    Oracle .9 ──▶ cargar_padron_oracle ──────┐
    (quién es víctima incluida)              │
                                             ├──▶ Victima (PostgreSQL) ──▶ generar_padron ──▶ APK
    Oracle .9 ──▶ cargar_fechas_caracteriz. ─┘                             (SQLite offline)
    (cuándo se le caracterizó)

Hasta ahora los tres comandos se corrían A MANO, en orden, por SSH. Eso funciona
una vez —la carga inicial— pero no como régimen: el padrón envejece en silencio y
nadie se entera hasta que un encuestador en campo ve a alguien que ya no debería
estar habilitado.

Dos tareas, no una — por qué
-----------------------------
Los tres pasos NO cambian al mismo ritmo, así que forzarlos a la misma
periodicidad obliga a elegir entre dos males: correr una carga de más de un día
todas las semanas, o dejar las fechas desactualizadas un mes entero.

| Qué | Cuánto tarda | Cada cuánto cambia el dato de origen |
|---|---|---|
| padrón (quién es víctima incluida) | horas — `update_or_create` fila a fila sobre 5,9 M | lento: altas del RUV |
| fechas de caracterización | ~12 min (`COPY` + un `UPDATE`) | **todos los días**: la app legacy sigue caracterizando |
| SQLite descargable | minutos | cada vez que cambia cualquiera de los dos |

De ahí:

* `recargar_padron` — la cadena completa, MENSUAL.
* `refrescar_fechas_padron` — solo fechas + snapshot, DIARIA. Es lo que evita que
  la APK ofrezca recaracterizar a alguien que la app vieja atendió ayer.

Ambas comparten el MISMO bloqueo: si la mensual está corriendo, la diaria se
saltea. No es una pérdida — la mensual incluye el trabajo de la diaria.

Nunca `--carga-inicial`
------------------------
`cargar_padron_oracle --carga-inicial` usa `bulk_create`, que NO deduplica: es
para poblar una tabla vacía. Repetirlo duplicaría el padrón entero. El propio
comando tiene una guarda que lo impide, pero estas tareas ni siquiera se acercan:
la recarga periódica es SIEMPRE la variante idempotente (más lenta, repetible).
"""
import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.management import call_command

from srni.bloqueos import bloqueo_exclusivo

logger = logging.getLogger(__name__)

# Un solo bloqueo para las dos tareas: las dos escriben sobre `victimas_victima` y
# las dos publican el mismo SQLite. Solaparlas no es solo ineficiente, es incorrecto
# (una generaría el snapshot mientras la otra está a mitad de actualizar la tabla).
BLOQUEO_PADRON = "padron:recarga"

# TTL del bloqueo — red de seguridad para el caso "el worker murió sin liberar".
# 48 h porque la carga idempotente completa está medida en ~51 filas/s sobre 5,9 M
# de personas: del orden de un día y medio. Un TTL más corto vencería A MITAD de una
# corrida sana y dejaría entrar a la siguiente, que es exactamente lo que se evita.
TTL_BLOQUEO_SEGUNDOS = 48 * 3600

# Límites de tiempo PROPIOS de estas tareas.
#
# Sin esto heredarían `CELERY_TASK_TIME_LIMIT = 600` (10 minutos), pensado para las
# escrituras a Oracle de un hogar: el worker mataría la recarga del padrón a los diez
# minutos, todos los meses, y en el log solo quedaría un `SoftTimeLimitExceeded` sin
# contexto. El soft va antes que el hard para que el comando alcance a cerrar la
# conexión a Oracle y dejar la bitácora `CargaPadron` en FALLIDA en vez de en curso.
LIMITE_BLANDO_RECARGA = 47 * 3600
LIMITE_DURO_RECARGA = 48 * 3600
LIMITE_BLANDO_REFRESCO = 3 * 3600
LIMITE_DURO_REFRESCO = 3 * 3600 + 600

# El ORDEN es la parte que importa y por eso vive en una constante, no enterrado en
# el cuerpo de la tarea (así se puede afirmar en un test):
#
#   1. el padrón trae QUIÉN es víctima incluida — crea las filas;
#   2. las fechas cuelgan de esas filas (`UPDATE ... FROM` por `cons_persona`): si
#      corrieran antes, actualizarían un padrón viejo y las personas nuevas
#      quedarían sin fecha hasta el mes siguiente;
#   3. el SQLite es una FOTO de lo que haya en PostgreSQL: al final, o publica un
#      estado intermedio.
PASOS_RECARGA_COMPLETA = (
    ("cargar_padron_oracle", {"confirmar": True}),
    ("cargar_fechas_caracterizacion", {"confirmar": True}),
    ("generar_padron", {}),
)

# La diaria salta el paso 1: el padrón poblacional no cambia de un día para otro, y
# ese paso es el que cuesta un día entero.
PASOS_REFRESCO_FECHAS = (
    ("cargar_fechas_caracterizacion", {"confirmar": True}),
    ("generar_padron", {}),
)


def _config() -> dict:
    return getattr(settings, "PADRON_RECARGA", {}) or {}


def _ejecutar_pasos(pasos, *, etiqueta) -> dict:
    """
    Corre los comandos en orden y ABORTA en el primer fallo.

    Fail-fast y no "seguir con los que se pueda", porque el paso 3 publica el
    archivo que descargan todas las APKs. Si la carga se cortó a mitad, el padrón
    en PostgreSQL quedó a medio actualizar; publicar una foto de ese estado
    reemplazaría un snapshot bueno por uno de completitud desconocida sin que nadie
    lo haya decidido. Al abortar, el manifiesto sigue apuntando al último padrón
    íntegro y el operador ve en el log exactamente qué paso falló.
    """
    resultado = {"pasos": [], "estado": "OK"}
    for comando, opciones in pasos:
        inicio = time.monotonic()
        logger.info("[%s] ejecutando %s %s", etiqueta, comando, opciones or "")
        try:
            # `call_command` en vez de `subprocess`: corre en este mismo proceso, así
            # que hereda settings, conexiones y logging, y una excepción sube como
            # excepción de Python en vez de como un código de salida sin contexto.
            call_command(comando, **opciones)
        except Exception as exc:                                   # noqa: BLE001
            segundos = time.monotonic() - inicio
            logger.exception("[%s] FALLÓ %s tras %.0fs — se abortan los pasos "
                             "siguientes", etiqueta, comando, segundos)
            resultado["pasos"].append({"comando": comando, "estado": "FALLIDO",
                                       "segundos": round(segundos),
                                       "motivo": f"{type(exc).__name__}: {exc}"[:500]})
            resultado["estado"] = "FALLIDA"
            resultado["fallo_en"] = comando
            return resultado
        segundos = time.monotonic() - inicio
        logger.info("[%s] %s OK en %.0fs", etiqueta, comando, segundos)
        resultado["pasos"].append({"comando": comando, "estado": "OK",
                                   "segundos": round(segundos)})
    return resultado


def _correr_cadena(pasos, *, etiqueta) -> dict:
    """Interruptor + bloqueo + pasos. Lo común a las dos tareas del padrón."""
    if not _config().get("HABILITADA", False):
        # Mismo criterio que `ORACLE_SYNC.AUTOMATICA`: leer millones de filas del
        # Oracle de producción es una decisión operativa explícita, no algo que
        # deba empezar a pasar porque alguien desplegó. Se comprueba AQUÍ y no solo
        # en el schedule: un beat con configuración vieja igual encontraría el freno.
        logger.info("[%s] omitida (PADRON_RECARGA.HABILITADA=False)", etiqueta)
        return {"tarea": etiqueta, "estado": "OMITIDA",
                "motivo": "la recarga automática del padrón está desactivada"}

    with bloqueo_exclusivo(BLOQUEO_PADRON, ttl_segundos=TTL_BLOQUEO_SEGUNDOS) as bl:
        if not bl.adquirido:
            return {"tarea": etiqueta, "estado": "SALTADA",
                    "motivo": f"ya hay una recarga del padrón en curso ({bl.dueño_actual})"}
        inicio = time.monotonic()
        resultado = _ejecutar_pasos(pasos, etiqueta=etiqueta)
        resultado["tarea"] = etiqueta
        resultado["segundos_total"] = round(time.monotonic() - inicio)
        return resultado


@shared_task(
    queue="padron",
    # Sin reintentos automáticos, a propósito: reintentar una carga de un día y medio
    # que ya falló, sin que nadie mire por qué, es cómo se encadenan tres días de
    # lecturas inútiles contra el Oracle de producción. Falla, queda en el log y en
    # la bitácora `CargaPadron`, y la decisión de repetirla la toma una persona.
    max_retries=0,
    soft_time_limit=LIMITE_BLANDO_RECARGA,
    time_limit=LIMITE_DURO_RECARGA,
)
def recargar_padron():
    """
    Recarga completa: padrón + fechas + SQLite descargable, en ese orden.

    Mensual. Es la variante IDEMPOTENTE de la carga (`--confirmar` sin
    `--carga-inicial`): más lenta, pero repetible sin duplicar.
    """
    return _correr_cadena(PASOS_RECARGA_COMPLETA, etiqueta="recargar_padron")


@shared_task(
    queue="padron",
    max_retries=0,
    soft_time_limit=LIMITE_BLANDO_REFRESCO,
    time_limit=LIMITE_DURO_REFRESCO,
)
def refrescar_fechas_padron():
    """
    Refresco diario: fechas de última caracterización + SQLite descargable.

    Barato (~12 min) y es el que mantiene viva la regla de recaracterización a 2
    años frente a lo que la aplicación legacy caracteriza cada día.
    """
    return _correr_cadena(PASOS_REFRESCO_FECHAS, etiqueta="refrescar_fechas_padron")
