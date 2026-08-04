"""
Las rutas de entrevista que omiten la regla de vigencia.

Manual UARIV §5.1.1 (pág. 22): de las cuatro rutas, **tres omiten** la regla y
solo la General la respeta. Hasta que esto existió, `ruta_entrevista` era una
etiqueta en `SesionEncuesta` y no omitía nada — una tutela no habilitaba
absolutamente nada, que es lo contrario de para lo que existe la ruta.
"""

import datetime

import pytest

from apps.victimas.homologacion import (
    RUTAS_QUE_OMITEN_VIGENCIA,
    ruta_omite_vigencia,
)
from apps.victimas.repository.base import (
    MotivoNoElegible,
    describir_elegibilidad,
)


class _Victima:
    """Lo mínimo que mira `describir_elegibilidad`."""

    def __init__(self, *, estado_ruv='INCLUIDO', habilitado=False, fecha_ult=None):
        self.estado_ruv = estado_ruv
        self.habilitado_para_caracterizacion = habilitado
        self.fecha_ult_caracterizacion = fecha_ult


FECHA = datetime.date(2026, 3, 14)


def _con_ficha_vigente():
    return _Victima(habilitado=False, fecha_ult=FECHA)


# ── Lo que dice el manual ────────────────────────────────────────────────────

def test_son_tres_las_rutas_que_omiten_la_vigencia_no_una():
    """
    El reporte del territorio hablaba solo de acción constitucional, pero el
    manual da la misma excepción a modificación de núcleo y a ruta especial.
    """
    assert RUTAS_QUE_OMITEN_VIGENCIA == {
        'ACCIONES_CONSTITUCIONALES',
        'MODIFICACION_NUCLEO',
        'ESPECIAL',
    }


def test_la_ruta_general_respeta_la_vigencia():
    """«En esta ruta entran todos los casos que no presentan ficha vigente, por
    lo cual, en este caso se respeta la regla de vigencia»."""
    assert ruta_omite_vigencia('GENERAL') is False
    assert ruta_omite_vigencia(None) is False
    assert ruta_omite_vigencia('') is False


@pytest.mark.parametrize('ruta', sorted(RUTAS_QUE_OMITEN_VIGENCIA))
def test_cada_ruta_de_excepcion_levanta_el_bloqueo(ruta):
    veredicto = describir_elegibilidad(_con_ficha_vigente(), ruta=ruta)

    assert veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_POR_EXCEPCION
    assert veredicto.exige_soporte


def test_sin_ruta_el_bloqueo_sigue_en_pie():
    """
    La búsqueda normal no pasa ruta: primero se ve el estado real, y recién si
    hay ficha vigente el encuestador elige una ruta de excepción.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente())

    assert not veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert not veredicto.exige_soporte


def test_la_ruta_general_no_levanta_nada():
    veredicto = describir_elegibilidad(_con_ficha_vigente(), ruta='GENERAL')
    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE


def test_el_nombre_de_la_ruta_no_depende_de_mayusculas_ni_espacios():
    """Llega desde el móvil y desde el panel web; no se confía en el formato."""
    assert ruta_omite_vigencia('  acciones_constitucionales  ') is True


# ── Los límites de la excepción ──────────────────────────────────────────────

def test_ninguna_ruta_habilita_a_una_persona_excluida_del_RUV():
    """
    El manual da la excepción para **fichas vigentes**, no para revertir una
    decisión del RUV. Si una ruta pudiera habilitar a un excluido, la ruta
    dejaría de ser una excepción de vigencia y pasaría a reescribir el RUV.
    """
    excluida = _Victima(estado_ruv='EXCLUIDO', habilitado=False)

    for ruta in RUTAS_QUE_OMITEN_VIGENCIA:
        veredicto = describir_elegibilidad(excluida, ruta=ruta)
        assert not veredicto.elegible
        assert veredicto.motivo == MotivoNoElegible.EXCLUIDA_RUV


def test_ninguna_ruta_inventa_a_quien_no_esta_en_el_padron():
    for ruta in RUTAS_QUE_OMITEN_VIGENCIA:
        veredicto = describir_elegibilidad(None, ruta=ruta)
        assert veredicto.motivo == MotivoNoElegible.NO_EN_PADRON


def test_una_persona_ya_elegible_no_pasa_por_la_excepcion():
    """Si no tenía ficha vigente, la ruta no cambia nada y NO exige soporte."""
    libre = _Victima(habilitado=True)

    veredicto = describir_elegibilidad(libre, ruta='ACCIONES_CONSTITUCIONALES')
    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE
    assert not veredicto.exige_soporte


# ── Lo que ve el encuestador ─────────────────────────────────────────────────

def test_la_excepcion_igual_le_dice_que_habia_ficha_vigente():
    """
    Que pueda continuar no significa ocultarle el dato: tiene que saber que
    está recaracterizando a alguien con entrevista vigente.
    """
    v = describir_elegibilidad(_con_ficha_vigente(), ruta='ACCIONES_CONSTITUCIONALES')

    assert '14/03/2026' in v.mensaje
    assert '14/03/2028' in v.mensaje
    assert 'soporte' in v.mensaje.lower()
    assert v.disponible_desde == datetime.date(2028, 3, 14)


def test_el_bloqueado_nombra_las_tres_rutas_que_lo_levantan():
    """
    Sin esto el mensaje es un callejón: el encuestador no sabe que existe una
    salida y escala a soporte, que es exactamente lo que pasó en campo.
    """
    mensaje = describir_elegibilidad(_con_ficha_vigente()).mensaje.lower()

    assert 'constitucional' in mensaje
    assert 'núcleo' in mensaje
    assert 'especial' in mensaje
    assert 'no es una falla' in mensaje
