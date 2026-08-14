"""
El estado RUV no se lee solo: se lee con su procedencia.

Lo que estos tests protegen no es un campo, es una distinción: **"no lo sabemos"
tiene que ser distinguible de "lo sabemos y está incluido"**. Sin ella, el padrón
afirmó durante meses que 5.926.004 personas estaban incluidas en el RUV porque un
join las emparejó con la caracterización de otra persona — y no había forma de
notarlo mirando el dato.
"""
import datetime

import pytest

from apps.parametricas.models import TipoDocumento
from apps.victimas.models import Victima


@pytest.fixture
def tipo_cc(db):
    return TipoDocumento.objects.create(codigo='CC', nombre='Cédula', activo=True)


def _victima(tipo_cc, documento='1000000001', **extra):
    return Victima.objects.create(
        tipo_documento=tipo_cc, numero_documento=documento,
        primer_nombre='ROSA', primer_apellido='BUSTOS',
        fecha_nacimiento='1975-03-14', genero='F', **extra)


# ── El default es el valor honesto ──────────────────────────────────────────

@pytest.mark.django_db
def test_por_defecto_el_estado_no_esta_verificado(tipo_cc):
    """
    Quien no diga de dónde sacó el estado, no lo sabe.

    El default NO puede ser una fuente confiable: eso convertiría cualquier
    escritura descuidada en una afirmación sobre el RUV.
    """
    v = _victima(tipo_cc)

    assert v.estado_ruv_fuente == 'SIN_VERIFICAR'
    assert v.estado_ruv_fecha is None
    assert not v.es_estado_ruv_confiable


@pytest.mark.django_db
def test_el_universo_si_es_confiable(tipo_cc):
    """El snapshot del RUV cruzado por documento — la fuente buena."""
    v = _victima(tipo_cc, estado_ruv='INCLUIDO',
                 estado_ruv_fuente='UNIVERSO_RUV',
                 estado_ruv_fecha=datetime.date(2026, 7, 1))

    assert v.es_estado_ruv_confiable
    assert v.estado_ruv_fecha == datetime.date(2026, 7, 1)


@pytest.mark.django_db
def test_lo_declarado_en_campo_es_confiable(tipo_cc):
    """La persona estaba enfrente del encuestador: eso vale."""
    v = _victima(tipo_cc, estado_ruv='INCLUIDO', estado_ruv_fuente='MANUAL')

    assert v.es_estado_ruv_confiable


@pytest.mark.django_db
def test_la_caracterizacion_del_legado_NO_es_confiable(tipo_cc):
    """
    `LEGACY_CARACT` es la fuente del defecto: `CONS_PERONA` resultó ser un
    contador de filas, no un identificador de persona. Aunque el estado diga
    `INCLUIDO`, no se puede afirmar.
    """
    v = _victima(tipo_cc, estado_ruv='INCLUIDO', estado_ruv_fuente='LEGACY_CARACT')

    assert not v.es_estado_ruv_confiable


@pytest.mark.django_db
def test_un_INCLUIDO_sin_procedencia_no_vale(tipo_cc):
    """
    El corazón del asunto. Antes, esto era indistinguible de un INCLUIDO real
    —de hecho eran los 5,9 M— y el sistema lo trataba como verdad.
    """
    v = _victima(tipo_cc, estado_ruv='INCLUIDO', estado_ruv_fuente='SIN_VERIFICAR')

    assert v.estado_ruv == 'INCLUIDO'
    assert not v.es_estado_ruv_confiable, (
        'un estado sin procedencia no se puede afirmar, diga lo que diga'
    )


# ── La distinción se puede consultar en SQL, no solo en Python ──────────────

@pytest.mark.django_db
def test_se_pueden_separar_en_una_consulta(tipo_cc):
    """
    Tiene que poder responderse "¿de cuántos sabemos el estado de verdad?" con un
    filtro, porque esa pregunta va en reportes sobre millones de filas y no se
    puede contestar instanciando objetos.
    """
    _victima(tipo_cc, '1000000001', estado_ruv='INCLUIDO',
             estado_ruv_fuente='UNIVERSO_RUV')
    _victima(tipo_cc, '1000000002', estado_ruv='INCLUIDO',
             estado_ruv_fuente='SIN_VERIFICAR')
    _victima(tipo_cc, '1000000003', estado_ruv='NO_VERIFICADO',
             estado_ruv_fuente='SIN_VERIFICAR')

    confiables = Victima.objects.filter(
        estado_ruv_fuente__in=Victima.FUENTES_RUV_CONFIABLES)

    assert confiables.count() == 1
    assert Victima.objects.filter(estado_ruv='INCLUIDO').count() == 2, (
        'hay dos INCLUIDO, pero solo uno se puede afirmar'
    )


# ── Que la limpieza no rompa la operación ──────────────────────────────────

@pytest.mark.django_db
def test_no_verificado_NO_impide_caracterizar(tipo_cc):
    """
    Verificado antes de tocar 5,9 M de filas: `describir_elegibilidad` solo corta
    con `EXCLUIDO`. Marcar el estado como no verificado dice la verdad sobre
    nuestro dato SIN dejar a nadie sin poder caracterizarse.
    """
    from apps.victimas.repository.base import (MotivoNoElegible,
                                               describir_elegibilidad)

    v = _victima(tipo_cc, estado_ruv='NO_VERIFICADO',
                 habilitado_para_caracterizacion=True)

    assert describir_elegibilidad(v).motivo == MotivoNoElegible.ELEGIBLE


@pytest.mark.django_db
def test_excluido_sigue_bloqueando(tipo_cc):
    """La única regla que sí depende del estado no se toca."""
    from apps.victimas.repository.base import (MotivoNoElegible,
                                               describir_elegibilidad)

    v = _victima(tipo_cc, estado_ruv='EXCLUIDO',
                 habilitado_para_caracterizacion=True)

    assert describir_elegibilidad(v).motivo == MotivoNoElegible.EXCLUIDA_RUV


@pytest.mark.django_db
def test_no_verificado_no_es_lo_mismo_que_no_incluido(tipo_cc):
    """
    Distinción que ya estaba documentada en el modelo y que este diseño refuerza:
    'no lo hemos verificado' es una afirmación sobre NUESTRO dato; 'no incluido'
    lo es sobre la persona. Confundirlas le graba a alguien un estado falso que
    viaja al hogar y a los reportes.
    """
    estados = dict(Victima.ESTADO_RUV)

    assert 'NO_VERIFICADO' in estados and 'NO_INCLUIDO' in estados
    assert estados['NO_VERIFICADO'] != estados['NO_INCLUIDO']
