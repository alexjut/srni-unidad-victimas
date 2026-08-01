"""
Tareas Celery de la sincronización SICAV → Oracle legacy.

Este módulo es el **eslabón que faltaba**: hasta el 2026-07-28 la escritura hacia
Oracle solo existía como comando de management, así que había que lanzarla a mano,
un hogar por vez. La cadena quedaba cortada justo después de PostgreSQL.

Cómo encaja:

    APK ──▶ /api/encuestas/{id}/finalizar/ ──▶ PostgreSQL
                                                 │
                                                 └─▶ sincronizar_hogar_a_oracle  (aquí)
                                                        └─▶ procedures GIC_* ──▶ Oracle
                                                              ▲
    celery beat ──▶ reintentar_sincronizaciones_pendientes ───┘
                    (la red que recoge lo que el disparo automático dejó atrás)

Tres cosas que esta capa NO hace, a propósito:

1. **No decide escribir.** Si `settings.ORACLE_SYNC['AUTOMATICA']` está apagado, la
   tarea se marca omitida y no toca Oracle. Escribir en la base de la UARIV es
   irreversible; encenderlo es una decisión operativa, no un efecto del despliegue.
2. **No reintenta un error de datos.** Un mapeo que no cruza (municipio inexistente,
   pregunta sin equivalente) va a fallar igual las cinco veces siguientes: reintentar
   solo llena la cola y el log. Solo se reintenta lo transitorio — la red, la BD caída.
3. **No inventa idempotencia propia.** El `EscritorOracle` ya la lleva en el ledger, y
   ahora por destino. Re-ejecutar esta tarea sobre un hogar ya escrito no duplica.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from srni.bloqueos import bloqueo_exclusivo

logger = logging.getLogger(__name__)

# Errores que SÍ vale la pena reintentar: la base estaba caída, la red se cortó.
# Los de mapeo (MapeoDesconocido / MapeoPendienteNegocio) no entran aquí.
ERRORES_TRANSITORIOS = ("DatabaseError", "OperationalError", "InterfaceError",
                        "ConnectionError", "TimeoutError")


def _es_transitorio(exc) -> bool:
    """Por nombre de clase: evita importar oracledb solo para clasificar el error."""
    jerarquia = {c.__name__ for c in type(exc).__mro__}
    return bool(jerarquia & set(ERRORES_TRANSITORIOS))


@shared_task(bind=True, max_retries=5, default_retry_delay=60, queue="sync")
def sincronizar_hogar_a_oracle(self, hogar_id, destino=None):
    """
    Escribe un hogar en Oracle legacy vía los procedures oficiales.

    Devuelve un dict con el resultado — nunca lanza por un error de datos, para no
    dejar la tarea en un ciclo de reintentos que no puede arreglar nada.
    """
    from apps.hogares.models import Hogar
    from apps.sincronizacion.oracle import mapeo
    from apps.sincronizacion.oracle.escritor import EscritorOracle

    cfg = getattr(settings, "ORACLE_SYNC", {}) or {}
    destino = destino or cfg.get("DESTINO") or ""

    if not cfg.get("AUTOMATICA"):
        logger.info("sync Oracle omitida (ORACLE_SYNC.AUTOMATICA=False) hogar=%s", hogar_id)
        return {"hogar": str(hogar_id), "estado": "OMITIDA",
                "motivo": "la escritura automática está desactivada"}

    if destino not in ("local", "produccion"):
        logger.error("sync Oracle sin destino válido (%r) hogar=%s", destino, hogar_id)
        return {"hogar": str(hogar_id), "estado": "OMITIDA",
                "motivo": f"ORACLE_SYNC.DESTINO inválido: {destino!r}"}

    try:
        hogar = Hogar.objects.get(pk=hogar_id)
    except Hogar.DoesNotExist:
        logger.error("sync Oracle: el hogar %s ya no existe", hogar_id)
        return {"hogar": str(hogar_id), "estado": "FALLIDA", "motivo": "hogar inexistente"}

    try:
        catalogos = mapeo.ResolverCatalogos.desde_settings(estricto=True)
        with EscritorOracle(confirmar=True, destino=destino, catalogos=catalogos) as escritor:
            resultado = escritor.procesar_hogar(hogar)
    except Exception as exc:                                   # noqa: BLE001
        if _es_transitorio(exc) and self.request.retries < self.max_retries:
            # Backoff exponencial: 1, 2, 4, 8, 16 minutos.
            espera = 60 * (2 ** self.request.retries)
            logger.warning("sync Oracle transitorio (%s) hogar=%s, reintento en %ss",
                           type(exc).__name__, hogar.codigo_hogar, espera)
            raise self.retry(exc=exc, countdown=espera)
        # Error de datos o reintentos agotados: queda registrado y no se insiste.
        logger.exception("sync Oracle FALLIDA hogar=%s", hogar.codigo_hogar)
        return {"hogar": hogar.codigo_hogar, "estado": "FALLIDA",
                "motivo": f"{type(exc).__name__}: {exc}"[:500]}

    resumen = resultado.resumen()
    logger.info("sync Oracle hogar=%s destino=%s → %s",
                hogar.codigo_hogar, destino, resumen)
    return {"hogar": hogar.codigo_hogar, "destino": destino,
            "hog_codigo_oracle": _hog_codigo_oracle(resultado),
            "estado": "PROCESADA", "resumen": {str(k): v for k, v in resumen.items()}}


def _hog_codigo_oracle(resultado) -> str:
    """
    El HOG_CODIGO que Oracle asignó, sacado del paso HOGAR.

    `ResultadoHogar` no lo expone como campo: guarda el código SICAV de origen. El
    de Oracle lo genera `FN_GET_CODIGOENCUESTA` durante la escritura y viaja en el
    detalle del paso, que es donde el ledger lo deja.
    """
    for paso in resultado.pasos:
        if str(paso.paso).endswith("HOGAR") and isinstance(paso.detalle, dict):
            codigo = paso.detalle.get("hog_codigo")
            if codigo:
                return codigo
    return ""


def encolar_hogar(hogar_id) -> bool:
    """
    Encola la sincronización de un hogar. Devuelve si se encoló de verdad.

    Se llama desde `transaction.on_commit`, nunca en medio de la transacción: si se
    encolara antes del commit, el worker podría empezar a leer un hogar que la base
    todavía no tiene visible (o que va a desaparecer si la transacción revierte).

    Nunca propaga la excepción: que el broker esté caído no puede impedir que un
    encuestador cierre su encuesta. La sesión ya está guardada en PostgreSQL, y el
    hogar se puede reprocesar después con el comando.
    """
    try:
        sincronizar_hogar_a_oracle.delay(str(hogar_id))
        return True
    except Exception:                                          # noqa: BLE001
        logger.exception("no se pudo encolar la sync a Oracle del hogar %s "
                         "(la encuesta SÍ quedó guardada; reprocesar con "
                         "`escribir_a_oracle --hogar <codigo>`)", hogar_id)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Barrida periódica: lo que el disparo automático dejó atrás
# ═══════════════════════════════════════════════════════════════════════════════
#
# `encolar_hogar` corre al cerrar la encuesta y NO propaga errores — por diseño: el
# encuestador tiene que poder cerrar aunque el broker esté caído. El precio de esa
# decisión es que hay hogares que quedan sin escribirse y nadie se entera. Hay cuatro
# formas de caer en ese hueco, y las cuatro pasaron o van a pasar:
#
#   1. Redis caído en el momento del cierre → nunca se encoló.
#   2. `ORACLE_SYNC.AUTOMATICA` apagado cuando se cerró la encuesta (el default) y
#      encendido después: esos hogares se marcaron OMITIDA y ahí quedaron. Es el caso
#      MASIVO — todo lo capturado antes de encender la escritura.
#   3. Error transitorio que agotó los 5 reintentos de la tarea.
#   4. Máquina de estados a medias: el procedure de un paso falló y el hogar quedó
#      con unos pasos VERIFICADO y otros no.
#
# Esta barrida es la red que recoge los cuatro. No reemplaza al disparo automático
# —que sigue siendo la vía rápida—, lo respalda.

BLOQUEO_REINTENTO = "sincronizacion:reintento"

# TTL corto: si el worker muere, quiero que la próxima corrida (15 min después) pueda
# entrar. Lo que protege es solo el barrido y el encolado, no la escritura en sí —
# esa la serializa el propio ledger, que es idempotente por (hogar, paso, destino).
TTL_BLOQUEO_REINTENTO = 30 * 60


def _config_reintento() -> dict:
    return getattr(settings, "SYNC_REINTENTO", {}) or {}


def hogares_pendientes_de_oracle(destino, *, enfriamiento_minutos, limite,
                                 max_intentos):
    """
    Hogares con la encuesta cerrada que NO están escritos en `destino`.

    Se separa de la tarea para poder afirmar el criterio en tests sin Celery de por
    medio, y para que un comando de reproceso manual pueda reutilizarlo tal cual en
    vez de reinventar una definición paralela de "pendiente".

    Tres decisiones que valen la pena explicar:

    * **Se filtra por `destino_entorno`.** Un hogar escrito contra la réplica local
      NO está escrito en producción. Sin este filtro la barrida daría por hecho lo
      que se ensayó en local — el mismo fallo silencioso que costó encontrar el
      2026-07-28 y que motivó meter el destino en la clave del ledger.
      Como los DRY-RUN se registran con `destino_entorno=''`, quedan fuera solos.

    * **Enfriamiento.** Un hogar que falló hace dos minutos casi seguro vuelve a
      fallar; y uno recién cerrado probablemente tenga su tarea normal EN VUELO en
      este instante. Reencolarlo no rompe nada (el ledger deduplica) pero gasta una
      conexión a Oracle y ensucia el log con un fallo repetido cada 15 minutos.

    * **Tope de intentos.** Si un paso lleva N intentos sin verificarse, no se
      arregla insistiendo: es un mapeo que no cruza, un municipio inexistente, un
      dato que alguien tiene que mirar. Se abandona el hogar ENTERO (no solo el paso)
      porque los pasos dependen unos de otros, y se lo deja visible en el admin.
    """
    from apps.encuestas.models import SesionEncuesta
    from apps.hogares.models import Hogar
    from apps.sincronizacion.models import EstadoPaso, RegistroEscrituraOracle

    corte = timezone.now() - timedelta(minutes=enfriamiento_minutos)

    # "Hay algo que escribir" = la encuesta se cerró. Es la misma señal que dispara
    # `encolar_hogar` en la vista de finalizar, así que la barrida cubre exactamente
    # el mismo universo que el camino automático — ni más ni menos.
    #
    # Va como `Exists` y no como JOIN porque un hogar puede tener varias sesiones: con
    # JOIN aparecería repetido y habría que arrastrar un `distinct()` que además
    # complica el `order_by`.
    cerradas = SesionEncuesta.objects.filter(
        hogar=OuterRef("pk"), estado="COMPLETADA",
    ).filter(
        # `updated_at` es el respaldo para sesiones antiguas que quedaron COMPLETADA
        # sin `fecha_fin`: sin él, esos hogares nunca entrarían a la barrida.
        Q(fecha_fin__lte=corte) | Q(fecha_fin__isnull=True, updated_at__lte=corte)
    )

    del_destino = RegistroEscrituraOracle.objects.filter(
        hogar=OuterRef("pk"), destino_entorno=destino)
    incompletos = del_destino.exclude(estado=EstadoPaso.VERIFICADO)

    return list(
        Hogar.objects
        .annotate(
            encuesta_cerrada=Exists(cerradas),
            tiene_registros=Exists(del_destino),
            reintentable=Exists(incompletos.filter(intento__lt=max_intentos,
                                                   actualizado_en__lte=corte)),
            agotado=Exists(incompletos.filter(intento__gte=max_intentos)),
        )
        .filter(encuesta_cerrada=True)
        # Nunca intentado en este destino, o intentado y quedó a medias.
        .filter(Q(tiene_registros=False) | Q(reintentable=True))
        .exclude(agotado=True)
        # El más viejo primero: sin un orden estable, un padrón de pendientes mayor
        # que `limite` haría que los mismos hogares se reencolen siempre y la cola
        # de atrás no avance nunca.
        .order_by("created_at")
        .values_list("pk", flat=True)[:limite]
    )


@shared_task(max_retries=0, queue="sync")
def reintentar_sincronizaciones_pendientes(limite=None):
    """
    Reencola los hogares que quedaron sin escribirse en Oracle.

    Devuelve un dict con el resumen. No escribe en Oracle: solo pone tareas en la
    cola, y cada una es la misma `sincronizar_hogar_a_oracle` del camino normal —
    con su ledger, su idempotencia y su clasificación de errores. Duplicar esa
    lógica aquí sería tener dos escrituras que un día divergen.

    Sin reintentos propios (`max_retries=0`): si esta corrida falla, la siguiente es
    dentro de unos minutos y va a encontrar exactamente los mismos pendientes.
    """
    cfg_sync = getattr(settings, "ORACLE_SYNC", {}) or {}
    cfg = _config_reintento()
    destino = cfg_sync.get("DESTINO") or ""

    if not cfg.get("HABILITADO", False):
        logger.info("barrida de reintento omitida (SYNC_REINTENTO.HABILITADO=False)")
        return {"estado": "OMITIDA", "motivo": "la barrida está desactivada"}

    if not cfg_sync.get("AUTOMATICA"):
        # Encolar igual sería inofensivo —la tarea individual se auto-omite— pero
        # llenaría la cola de no-ops cada pocos minutos y taparía el log real.
        logger.info("barrida de reintento omitida (ORACLE_SYNC.AUTOMATICA=False)")
        return {"estado": "OMITIDA",
                "motivo": "la escritura automática a Oracle está desactivada"}

    if destino not in ("local", "produccion"):
        logger.error("barrida de reintento sin destino válido (%r)", destino)
        return {"estado": "OMITIDA",
                "motivo": f"ORACLE_SYNC.DESTINO inválido: {destino!r}"}

    limite = int(limite or cfg.get("LIMITE", 50))

    with bloqueo_exclusivo(BLOQUEO_REINTENTO, ttl_segundos=TTL_BLOQUEO_REINTENTO) as bl:
        if not bl.adquirido:
            # Con la barrida cada pocos minutos y una base grande, el barrido puede
            # tardar más que el intervalo. Dos barridas a la vez encolarían los
            # mismos hogares dos veces: no rompe nada (el ledger deduplica) pero
            # duplica conexiones a Oracle justo cuando ya va lento.
            return {"estado": "SALTADA",
                    "motivo": f"ya hay una barrida en curso ({bl.dueño_actual})"}

        pendientes = hogares_pendientes_de_oracle(
            destino,
            enfriamiento_minutos=int(cfg.get("ENFRIAMIENTO_MINUTOS", 30)),
            limite=limite,
            max_intentos=int(cfg.get("MAX_INTENTOS", 5)),
        )
        encolados = sum(1 for hogar_id in pendientes if encolar_hogar(hogar_id))

        if pendientes:
            logger.info("barrida de reintento destino=%s: %s pendientes, %s encolados "
                        "(tope %s)", destino, len(pendientes), encolados, limite)
        return {"estado": "PROCESADA", "destino": destino,
                "pendientes": len(pendientes), "encolados": encolados,
                # Que el barrido haya llegado al tope significa que quedan más
                # esperando: es la señal de que el intervalo o el límite se quedaron
                # cortos frente al volumen.
                "tope_alcanzado": len(pendientes) >= limite}
