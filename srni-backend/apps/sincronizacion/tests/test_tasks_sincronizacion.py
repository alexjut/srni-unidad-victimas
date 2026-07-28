"""
Tests del disparador automático SICAV → Oracle.

Lo que se protege, en orden de gravedad:

1. **Que no escriba en Oracle sin que alguien lo haya encendido.** Escribir en la
   base de la UARIV es irreversible; el interruptor está apagado por defecto y no
   debe encenderse por el simple hecho de desplegar.
2. **Que cerrar una encuesta nunca falle por culpa de la sincronización.** El
   encuestador está en campo; si el broker está caído, la encuesta igual se guarda.
3. **Que no se reintente eternamente un error de datos.** Un municipio que no cruza
   va a fallar igual las cinco veces siguientes.
"""
from unittest import mock

import pytest
from django.test import override_settings

from apps.sincronizacion import tasks

pytestmark = pytest.mark.django_db


@pytest.fixture
def hogar(db):
    from apps.hogares.models import Hogar
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento="900002",
        primer_nombre="A", primer_apellido="B",
        fecha_nacimiento="1990-01-01", genero="F",
    )
    return Hogar.objects.create(codigo_hogar="SYNC-TEST-1", autorizado=victima,
                                estado="BORRADOR")


# ── 1. el interruptor ────────────────────────────────────────────────────────
@override_settings(ORACLE_SYNC={"AUTOMATICA": False, "DESTINO": "produccion"})
def test_apagado_no_toca_oracle(hogar):
    """El default. Ni siquiera se construye el escritor."""
    with mock.patch("apps.sincronizacion.oracle.escritor.EscritorOracle") as escritor:
        res = tasks.sincronizar_hogar_a_oracle(str(hogar.pk))
    escritor.assert_not_called()
    assert res["estado"] == "OMITIDA"
    assert "desactivada" in res["motivo"]


@override_settings(ORACLE_SYNC={"AUTOMATICA": True, "DESTINO": ""})
def test_encendido_pero_sin_destino_no_escribe(hogar):
    """Encender la sincronización sin decir a QUÉ base no puede resolverse solo."""
    with mock.patch("apps.sincronizacion.oracle.escritor.EscritorOracle") as escritor:
        res = tasks.sincronizar_hogar_a_oracle(str(hogar.pk))
    escritor.assert_not_called()
    assert res["estado"] == "OMITIDA"
    assert "DESTINO" in res["motivo"]


@override_settings(ORACLE_SYNC={"AUTOMATICA": True, "DESTINO": "servidor-random"})
def test_destino_desconocido_no_escribe(hogar):
    res = tasks.sincronizar_hogar_a_oracle(str(hogar.pk))
    assert res["estado"] == "OMITIDA"


# ── 2. clasificación de errores ──────────────────────────────────────────────
def test_error_de_datos_no_es_transitorio():
    """Un mapeo que no cruza no se arregla reintentando."""
    from apps.sincronizacion.oracle.mapeo import MapeoDesconocido
    assert tasks._es_transitorio(MapeoDesconocido("municipio 99999 no existe")) is False


@pytest.mark.parametrize("exc", [
    ConnectionError("se cayó la red"),
    TimeoutError("no respondió"),
])
def test_error_de_infraestructura_si_es_transitorio(exc):
    assert tasks._es_transitorio(exc) is True


@override_settings(ORACLE_SYNC={"AUTOMATICA": True, "DESTINO": "local"})
def test_error_de_datos_devuelve_fallida_sin_reintentar(hogar):
    from apps.sincronizacion.oracle.mapeo import MapeoDesconocido
    with mock.patch("apps.sincronizacion.oracle.escritor.EscritorOracle",
                    side_effect=MapeoDesconocido("municipio inexistente")):
        res = tasks.sincronizar_hogar_a_oracle(str(hogar.pk))
    assert res["estado"] == "FALLIDA"
    assert "MapeoDesconocido" in res["motivo"]


@override_settings(ORACLE_SYNC={"AUTOMATICA": True, "DESTINO": "local"})
def test_hogar_inexistente_no_revienta():
    import uuid
    res = tasks.sincronizar_hogar_a_oracle(str(uuid.uuid4()))
    assert res["estado"] == "FALLIDA"


# ── 3. encolar nunca rompe el cierre de la encuesta ──────────────────────────
def test_encolar_devuelve_true_cuando_puede(hogar):
    with mock.patch.object(tasks.sincronizar_hogar_a_oracle, "delay") as delay:
        assert tasks.encolar_hogar(hogar.pk) is True
    delay.assert_called_once_with(str(hogar.pk))


def test_encolar_no_propaga_si_el_broker_esta_caido(hogar):
    """
    El caso real: Redis caído a mitad de jornada. El encuestador tiene que poder
    cerrar su encuesta igual — el dato ya está en PostgreSQL y se reprocesa después.
    """
    with mock.patch.object(tasks.sincronizar_hogar_a_oracle, "delay",
                           side_effect=OSError("no hay broker")):
        assert tasks.encolar_hogar(hogar.pk) is False


# ── 4. el HOG_CODIGO de Oracle se extrae del paso HOGAR ──────────────────────
def test_extrae_el_codigo_de_oracle_del_paso_hogar():
    class _Paso:
        def __init__(self, paso, detalle):
            self.paso = paso
            self.detalle = detalle

    class _Resultado:
        pasos = [_Paso("PasoEscritura.TERRITORIO", {"iddt": "7"}),
                 _Paso("PasoEscritura.HOGAR", {"hog_codigo": "999999-2W832"})]

    assert tasks._hog_codigo_oracle(_Resultado()) == "999999-2W832"


def test_sin_paso_hogar_devuelve_vacio_en_vez_de_reventar():
    class _Resultado:
        pasos = []
    assert tasks._hog_codigo_oracle(_Resultado()) == ""
