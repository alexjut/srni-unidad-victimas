"""
El interruptor que retira la regla de los dos años.

─── Qué se prueba ───────────────────────────────────────────────────────────
`settings.VIGENCIA['BLOQUEO_ACTIVO'] = False` retira el bloqueo por ficha
vigente, pedido por el equipo de caracterización el 11-sep-2026.

Las dos propiedades que importan, y que son fáciles de romper sin notarlo:

1. **El default no retira nada.** Un despliegue no puede levantar por su cuenta un
   control del Manual de Usuario §5.1.1. Si alguien cambia el default a `False`,
   el primer test de este archivo falla.
2. **Retirar el bloqueo no borra el dato.** El veredicto conserva que la ficha
   estaba vigente y hasta cuándo, porque son los dos campos con los que se
   escribe `RecaracterizacionVigente` al cerrar la encuesta. Si alguien
   "simplifica" el veredicto a `ELEGIBLE` a secas, se pierde para siempre la
   única constancia de la recaracterización anticipada — y no falla nada más.

No tocan base de datos: la decisión es pura y el doble de tres atributos alcanza.
"""

import datetime

import pytest
from django.test import override_settings

from apps.victimas.repository.base import (
    MotivoNoElegible,
    describir_elegibilidad,
)

FECHA_ULT = datetime.date(2026, 3, 14)
#: Dos años después de FECHA_ULT — hasta cuándo estaba vigente esa ficha.
VIGENTE_HASTA = datetime.date(2028, 3, 14)


class _Victima:
    """Lo mínimo que mira `describir_elegibilidad`."""

    def __init__(self, *, estado_ruv='INCLUIDO', habilitado=False, fecha_ult=None):
        self.estado_ruv = estado_ruv
        self.habilitado_para_caracterizacion = habilitado
        self.fecha_ult_caracterizacion = fecha_ult


def _con_ficha_vigente():
    return _Victima(habilitado=False, fecha_ult=FECHA_ULT)


# ── El default: el control sigue en pie ──────────────────────────────────────

def test_por_defecto_el_bloqueo_sigue_activo():
    """
    Sin configurar nada, la regla de los dos años bloquea.

    Este test existe para que cambiar el default sea imposible por accidente:
    retirar un control del Manual tiene que ser una decisión explícita, con fecha
    y responsable, no el efecto de que alguien desplegara.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert not veredicto.elegible


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_bloqueo_encendido_nada_cambia():
    """El interruptor encendido es exactamente el comportamiento histórico."""
    veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert not veredicto.elegible


# ── El interruptor apagado ───────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_la_ficha_vigente_ya_no_detiene():
    veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_SIN_CONTROL_VIGENCIA
    assert veredicto.elegible


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_el_veredicto_conserva_que_la_ficha_estaba_vigente():
    """
    Lo que este archivo existe para proteger.

    Con el control retirado sería tentador devolver `ELEGIBLE` y acabar. Pero
    entonces quien cierra la encuesta no tendría cómo saber que esta persona SÍ
    tenía ficha vigente, y el registro del §1.3 del correo del 11-sep-2026 se
    quedaría vacío sin que nada falle.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert veredicto.sobre_ficha_vigente
    assert veredicto.disponible_desde == VIGENTE_HASTA
    # El mensaje dice las dos fechas: es lo que el encuestador ve en pantalla.
    assert '14/03/2026' in veredicto.mensaje
    assert '14/03/2028' in veredicto.mensaje


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_no_se_menciona_autorizacion_ni_radicado():
    """
    El mensaje no puede mandar a pedir un permiso que ya no existe.

    Con el control retirado no hay coordinación a la que solicitar nada. Dejar el
    texto viejo mandaría al encuestador a hacer una gestión imposible, que es la
    forma más segura de que el cambio se reporte como falla.
    """
    mensaje = describir_elegibilidad(
        _con_ficha_vigente(), habilitacion=None).mensaje.lower()

    assert 'radicado' not in mensaje
    assert 'coordinación' not in mensaje
    assert 'excepción' not in mensaje


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_no_se_consulta_la_habilitacion():
    """
    Con el control retirado, buscar habilitaciones sería una consulta inútil en el
    camino más caliente de la aplicación — la búsqueda por documento, que corre
    con la VPN intermitente y el celular en la mano.

    Se prueba pasando el centinela `_SIN_CONSULTAR` (o sea, NO pasando
    `habilitacion`): si el código intentara buscarla, tocaría base de datos y este
    test fallaría por falta de `django_db`.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente())

    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_SIN_CONTROL_VIGENCIA


# ── Lo que el interruptor NO debe tocar ──────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_la_excluida_del_RUV_sigue_excluida():
    """
    Retirar la vigencia no es abrir todo.

    La exclusión del RUV es una decisión jurídica sobre la condición de víctima,
    no un control de frescura del dato. Ninguna ruta la habilitaba antes y el
    interruptor tampoco: confundir las dos cosas caracterizaría a personas que la
    entidad determinó que no son víctimas.
    """
    excluida = _Victima(estado_ruv='EXCLUIDO', fecha_ult=FECHA_ULT)

    veredicto = describir_elegibilidad(excluida, habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.EXCLUIDA_RUV
    assert not veredicto.elegible


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_quien_no_esta_en_el_padron_sigue_sin_estar():
    """No estar en el padrón no es un bloqueo de vigencia: es no tener ficha."""
    veredicto = describir_elegibilidad(None, habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.NO_EN_PADRON


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_el_dato_roto_sigue_siendo_dato_roto():
    """
    Marcada como no habilitada y sin fecha que lo explique. Son 0 casos en
    producción, pero si aparecen hay que seguir viéndolos: el interruptor retira
    una regla, no tapa una inconsistencia.
    """
    rota = _Victima(habilitado=False, fecha_ult=None)

    veredicto = describir_elegibilidad(rota, habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.BLOQUEADA_SIN_MOTIVO


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_bloqueo_quien_ya_estaba_habilitado_no_entra_al_registro():
    """
    El caso corriente, y el que evita un libro inútil.

    Una persona nunca caracterizada —o con la ficha ya vencida— está habilitada
    por la vía normal. No es una recaracterización anticipada y **no** debe quedar
    en el registro: si entrara, el libro tendría millones de filas y ninguna
    diría nada.
    """
    habilitada = _Victima(habilitado=True, fecha_ult=None)

    veredicto = describir_elegibilidad(habilitada, habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE
    assert not veredicto.sobre_ficha_vigente


# ── La propiedad compartida ──────────────────────────────────────────────────

@pytest.mark.parametrize('bloqueo_activo, motivo_esperado', [
    (True, MotivoNoElegible.FICHA_VIGENTE),
    (False, MotivoNoElegible.ELEGIBLE_SIN_CONTROL_VIGENCIA),
])
def test_el_interruptor_es_lo_unico_que_cambia_el_veredicto(bloqueo_activo,
                                                            motivo_esperado):
    """Misma persona, mismos datos: lo único distinto es la configuración."""
    with override_settings(VIGENCIA={'BLOQUEO_ACTIVO': bloqueo_activo}):
        veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert veredicto.motivo == motivo_esperado
