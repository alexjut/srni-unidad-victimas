"""
Tests de la programación (celery beat).

Un error aquí no rompe nada visible: simplemente la tarea no corre nunca, o corre
a una hora equivocada, y nadie se entera durante semanas. Eso es lo que se cubre —
que el reloj apunte a tareas que existen, en la cola que alguien está escuchando y
a la hora que dice el comentario.
"""
import pytest
from celery.schedules import crontab
from django.conf import settings

from srni.celery import app


@pytest.fixture(scope="module", autouse=True)
def tareas_importadas():
    """
    Fuerza el autodiscover, que normalmente es perezoso.

    Es exactamente lo que hace el worker al arrancar. Sin esto `app.tasks` está
    casi vacío y los tests pasarían sin comprobar nada.
    """
    app.loader.import_default_modules()


ESPERADAS = {
    "padron-recarga-mensual": ("apps.victimas.tasks.recargar_padron", "padron"),
    "padron-refresco-diario": ("apps.victimas.tasks.refrescar_fechas_padron", "padron"),
    "sincronizacion-reintento": (
        "apps.sincronizacion.tasks.reintentar_sincronizaciones_pendientes", "sync"),
}


@pytest.mark.parametrize("entrada", sorted(ESPERADAS))
def test_la_tarea_programada_existe(entrada):
    """
    Un nombre mal escrito en el schedule es un `NotRegistered` a la hora del
    disparo — dentro de un mes, en el log de un contenedor que nadie mira.
    """
    nombre, _cola = ESPERADAS[entrada]
    assert settings.CELERY_BEAT_SCHEDULE[entrada]["task"] == nombre
    assert nombre in app.tasks


@pytest.mark.parametrize("entrada", sorted(ESPERADAS))
def test_la_tarea_va_a_una_cola_que_alguien_escucha(entrada):
    """
    Encolar en una cola sin worker no da error: el mensaje se queda ahí para
    siempre. Las colas válidas son las que consumen los servicios del compose
    (cz_celery: sync,reports — cz_celery_padron: padron).
    """
    _nombre, cola = ESPERADAS[entrada]
    assert settings.CELERY_BEAT_SCHEDULE[entrada]["options"]["queue"] == cola
    assert cola in {"sync", "reports", "padron"}


def test_no_hay_entradas_de_mas():
    """Si aparece una entrada nueva sin test, este falla y obliga a documentarla."""
    assert set(settings.CELERY_BEAT_SCHEDULE) == set(ESPERADAS)


# ── horarios ─────────────────────────────────────────────────────────────────
def test_la_recarga_pesada_cae_el_primer_sabado_del_mes():
    """
    La cadena completa dura del orden de un día: tiene que arrancar en fin de
    semana para no competir con los encuestadores en campo ni con la aplicación
    legacy sobre el mismo Oracle.

    Ojo: en el crontab de Celery `day_of_month` y `day_of_week` se combinan con Y
    (en el cron de Unix es O), así que '1-7' + sábado = el primer sábado del mes.
    """
    programado = settings.CELERY_BEAT_SCHEDULE["padron-recarga-mensual"]["schedule"]
    assert isinstance(programado, crontab)
    assert programado.day_of_month == {1, 2, 3, 4, 5, 6, 7}
    assert programado.day_of_week == {6}          # sábado
    assert programado.hour == {settings.PADRON_RECARGA["HORA"]}


def _proxima_ejecucion(programado, desde):
    """
    La siguiente vez que dispararía `programado` a partir de `desde`.

    Se reconstruye el `crontab` con los mismos parámetros y un reloj fijo en vez de
    mutar el objeto de settings, que es compartido por todos los tests.
    """
    clon = crontab(minute=programado._orig_minute, hour=programado._orig_hour,
                   day_of_month=programado._orig_day_of_month,
                   day_of_week=programado._orig_day_of_week,
                   nowfun=lambda: desde)
    return desde + clon.remaining_estimate(desde)


@pytest.mark.parametrize("desde, esperado", [
    # Desde mitad de julio: el primer sábado de agosto.
    ((2026, 7, 20), "2026-08-01 20:00"),
    # Justo después de la corrida de agosto: salta los demás sábados del mes y va
    # al primero de septiembre. Aquí es donde se vería si la semántica fuera OR.
    ((2026, 8, 2), "2026-09-05 20:00"),
    # Arrancar el día 1 en martes no adelanta nada: espera al sábado.
    ((2026, 9, 1), "2026-09-05 20:00"),
])
def test_la_recarga_dispara_una_vez_al_mes_y_solo_en_sabado(desde, esperado):
    """
    Comprobado contra el propio calculador de Celery, no contra la lectura del
    comentario: si alguien "corrigiera" la expresión asumiendo la semántica de Unix
    (donde día-del-mes y día-de-semana se combinan con O), la carga pasaría a correr
    todos los sábados MÁS los siete primeros días del mes — once corridas de un día
    cada una, todos los meses, contra el Oracle de producción.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    inicio = datetime(*desde, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
    programado = settings.CELERY_BEAT_SCHEDULE["padron-recarga-mensual"]["schedule"]
    assert _proxima_ejecucion(programado, inicio).strftime("%Y-%m-%d %H:%M") == esperado


def test_el_refresco_diario_corre_todos_los_dias_de_madrugada():
    programado = settings.CELERY_BEAT_SCHEDULE["padron-refresco-diario"]["schedule"]
    assert programado.hour == {settings.PADRON_RECARGA["HORA_REFRESCO"]}
    # Sin restricción de día: `crontab` deja los conjuntos completos.
    assert len(programado.day_of_week) == 7


def test_la_barrida_de_reintento_corre_cada_pocos_minutos():
    programado = settings.CELERY_BEAT_SCHEDULE["sincronizacion-reintento"]["schedule"]
    minutos = settings.SYNC_REINTENTO["CADA_MINUTOS"]
    assert programado.total_seconds() == minutos * 60
    # Frecuente pero no un martilleo: cada corrida abre conexiones a Oracle.
    assert 5 <= minutos <= 60


@pytest.mark.parametrize("entrada", sorted(ESPERADAS))
def test_toda_entrada_expira(entrada):
    """
    Sin `expires`, un worker caído seis horas vuelve y ejecuta de un tirón todas
    las corridas acumuladas. Para la barrida son dos docenas seguidas; para el
    padrón, arrancar una carga de un día un lunes a las nueve de la mañana.
    """
    assert settings.CELERY_BEAT_SCHEDULE[entrada]["options"]["expires"] > 0


# ── configuración del reloj y del broker ─────────────────────────────────────
def test_el_reloj_esta_en_hora_de_colombia():
    """
    En UTC, un `crontab(hour=20)` se dispararía a las 15:00 hora local — en plena
    jornada de campo. Es el error clásico y es invisible hasta que pasa.
    """
    assert app.conf.timezone == settings.TIME_ZONE == "America/Bogota"


def test_redis_no_reentrega_la_carga_del_padron_a_mitad():
    """
    El `visibility_timeout` de Redis por defecto es 1 hora: una tarea que dura más
    se re-entrega a otro worker y termina corriendo varias veces en paralelo. Tiene
    que superar el límite duro de la tarea más larga.
    """
    from apps.victimas.tasks import LIMITE_DURO_RECARGA

    visibilidad = app.conf.broker_transport_options["visibility_timeout"]
    assert visibilidad > LIMITE_DURO_RECARGA


def test_las_tareas_del_padron_no_heredan_el_limite_de_diez_minutos():
    """
    `CELERY_TASK_TIME_LIMIT` global son 600 s, pensados para escribir un hogar en
    Oracle. Heredarlo mataría la recarga del padrón a los diez minutos, todos los
    meses, dejando en el log solo un `SoftTimeLimitExceeded` sin contexto.
    """
    for nombre in ("apps.victimas.tasks.recargar_padron",
                   "apps.victimas.tasks.refrescar_fechas_padron"):
        tarea = app.tasks[nombre]
        assert tarea.time_limit > settings.CELERY_TASK_TIME_LIMIT
        assert tarea.soft_time_limit < tarea.time_limit


def test_la_recarga_del_padron_no_se_reintenta_sola():
    """
    Reintentar una carga de un día y medio que ya falló, sin que nadie haya mirado
    por qué, encadena días de lecturas inútiles contra el Oracle de producción.
    """
    assert app.tasks["apps.victimas.tasks.recargar_padron"].max_retries == 0
