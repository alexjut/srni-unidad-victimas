"""
Tests de la recarga programada del padrón.

Lo que se protege, en orden de gravedad:

1. **Que nunca se use `--carga-inicial`.** Esa variante inserta con `bulk_create`
   sin deduplicar: en una recarga periódica duplicaría el padrón entero — 5,9
   millones de personas repetidas en la base que consulta la APK.
2. **Que no corran dos recargas a la vez.** Una corrida dura del orden de un día;
   beat dispara igual. Dos cargas simultáneas contra el Oracle de producción.
3. **Que el orden del encadenamiento sea el correcto.** Las fechas cuelgan de las
   filas que crea la carga, y el SQLite es la foto final. Cualquier otro orden
   publica un padrón incoherente.
4. **Que no arranque sola al desplegar.** Leer millones de filas del Oracle de la
   UARIV es una decisión operativa, igual que la escritura.
"""
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management.base import CommandError
from django.test import override_settings

from apps.victimas import tasks

HABILITADA = {"HABILITADA": True, "HORA": 20, "DIA_SEMANA": "saturday",
              "DIAS_MES": "1-7", "HORA_REFRESCO": 3}


@pytest.fixture(autouse=True)
def cache_limpia():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def comandos():
    """Intercepta `call_command`: los comandos reales tocan el Oracle de producción."""
    with mock.patch.object(tasks, "call_command") as cc:
        yield cc


def _llamados(comandos):
    """[(nombre, opciones), …] en el orden en que se ejecutaron."""
    return [(c.args[0], c.kwargs) for c in comandos.call_args_list]


# ── 1. jamás la carga inicial ────────────────────────────────────────────────
def test_ninguna_tarea_usa_carga_inicial():
    """
    `--carga-inicial` no deduplica. En una recarga periódica duplica el padrón.
    Se afirma sobre las constantes, así que también protege de que alguien lo
    agregue en el futuro "para que vaya más rápido".
    """
    for pasos in (tasks.PASOS_RECARGA_COMPLETA, tasks.PASOS_REFRESCO_FECHAS):
        for _comando, opciones in pasos:
            assert "carga_inicial" not in opciones
            assert "carga-inicial" not in opciones


@override_settings(PADRON_RECARGA=HABILITADA)
def test_la_recarga_ejecutada_no_pasa_carga_inicial(comandos):
    tasks.recargar_padron()
    for _comando, opciones in _llamados(comandos):
        assert opciones.get("carga_inicial") is not True


# ── 2. orden del encadenamiento ──────────────────────────────────────────────
def test_el_orden_de_la_cadena_completa_es_el_correcto():
    """padrón → fechas → snapshot. Las fechas actualizan las filas que crea el
    padrón, y el SQLite fotografía el resultado de ambos."""
    assert [c for c, _ in tasks.PASOS_RECARGA_COMPLETA] == [
        "cargar_padron_oracle",
        "cargar_fechas_caracterizacion",
        "generar_padron",
    ]


def test_los_dos_pasos_que_escriben_van_confirmados():
    """Sin `--confirmar` los comandos son DRY-RUN: la tarea correría durante horas
    y no escribiría ni una fila, sin que nada avise."""
    pasos = dict(tasks.PASOS_RECARGA_COMPLETA)
    assert pasos["cargar_padron_oracle"]["confirmar"] is True
    assert pasos["cargar_fechas_caracterizacion"]["confirmar"] is True


@override_settings(PADRON_RECARGA=HABILITADA)
def test_la_recarga_llama_a_los_tres_comandos_en_orden(comandos):
    res = tasks.recargar_padron()
    assert [c for c, _ in _llamados(comandos)] == [
        "cargar_padron_oracle", "cargar_fechas_caracterizacion", "generar_padron"]
    assert res["estado"] == "OK"


@override_settings(PADRON_RECARGA=HABILITADA)
def test_el_refresco_diario_salta_la_carga_pesada(comandos):
    """El padrón poblacional no cambia de un día para otro; ese paso es el que
    cuesta un día entero."""
    tasks.refrescar_fechas_padron()
    assert [c for c, _ in _llamados(comandos)] == [
        "cargar_fechas_caracterizacion", "generar_padron"]


# ── 3. fail-fast ─────────────────────────────────────────────────────────────
@override_settings(PADRON_RECARGA=HABILITADA)
def test_si_falla_la_carga_no_se_publica_el_snapshot(comandos):
    """
    El paso 3 reemplaza el archivo que descargan todas las APKs. Con la carga
    cortada a mitad, el padrón quedó a medio actualizar: publicar esa foto cambiaría
    un snapshot bueno por uno de completitud desconocida sin que nadie lo decidiera.
    """
    comandos.side_effect = CommandError("se cayó el dblink a Vivanto")
    res = tasks.recargar_padron()
    assert res["estado"] == "FALLIDA"
    assert res["fallo_en"] == "cargar_padron_oracle"
    assert [c for c, _ in _llamados(comandos)] == ["cargar_padron_oracle"]


@override_settings(PADRON_RECARGA=HABILITADA)
def test_un_fallo_no_deja_el_bloqueo_tomado(comandos):
    """Si lo dejara tomado, la tarea no volvería a correr en 48 h (el TTL)."""
    comandos.side_effect = CommandError("boom")
    assert tasks.recargar_padron()["estado"] == "FALLIDA"
    with mock.patch.object(tasks, "call_command"):
        # La corrida siguiente entra: si el bloqueo hubiera quedado tomado, esto
        # diría "SALTADA" y nadie se enteraría hasta dos meses después.
        assert tasks.recargar_padron()["estado"] == "OK"


# ── 4. exclusión mutua ───────────────────────────────────────────────────────
@override_settings(PADRON_RECARGA=HABILITADA)
def test_no_corren_dos_recargas_a_la_vez(comandos):
    """
    El caso real: la corrida del mes pasado sigue viva (dura más de un día) y beat
    dispara la de este mes. La segunda tiene que saltarse, no encimarse.
    """
    adentro = {}

    def _mientras_corre(*a, **k):
        # Se dispara la segunda corrida DESDE dentro de la primera: es exactamente
        # lo que pasa cuando dos workers toman el mensaje a la vez.
        adentro["resultado"] = tasks.recargar_padron()

    comandos.side_effect = _mientras_corre
    tasks.recargar_padron()

    assert adentro["resultado"]["estado"] == "SALTADA"
    assert "en curso" in adentro["resultado"]["motivo"]


@override_settings(PADRON_RECARGA=HABILITADA)
def test_el_refresco_diario_tampoco_se_mete_si_la_mensual_corre(comandos):
    """Comparten bloqueo a propósito: las dos escriben la misma tabla y publican el
    mismo SQLite. Saltarse el refresco no pierde nada — la mensual ya lo hace."""
    adentro = {}
    comandos.side_effect = lambda *a, **k: adentro.setdefault(
        "resultado", tasks.refrescar_fechas_padron())
    tasks.recargar_padron()
    assert adentro["resultado"]["estado"] == "SALTADA"


# ── 5. el interruptor ────────────────────────────────────────────────────────
@override_settings(PADRON_RECARGA={"HABILITADA": False})
def test_apagada_no_toca_oracle(comandos):
    """El default. Desplegar no puede desencadenar una lectura de millones de filas
    del Oracle de producción."""
    res = tasks.recargar_padron()
    comandos.assert_not_called()
    assert res["estado"] == "OMITIDA"


@override_settings(PADRON_RECARGA={"HABILITADA": False})
def test_el_refresco_tambien_respeta_el_interruptor(comandos):
    assert tasks.refrescar_fechas_padron()["estado"] == "OMITIDA"
    comandos.assert_not_called()


def test_el_default_del_proyecto_es_apagado():
    """Sin `PADRON_RECARGA_HABILITADA` en el entorno, nada corre solo."""
    from django.conf import settings
    assert settings.PADRON_RECARGA["HABILITADA"] is False
