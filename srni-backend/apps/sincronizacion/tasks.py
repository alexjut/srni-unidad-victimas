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

from celery import shared_task
from django.conf import settings

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
