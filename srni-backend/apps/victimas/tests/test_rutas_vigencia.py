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


class _Habilitacion:
    """
    Lo mínimo que mira `describir_elegibilidad` de una habilitación autorizada.

    Se usa un doble y no el modelo real para que los tests de la regla no
    necesiten base de datos: la decisión es pura, y meterle `django_db` a
    cuarenta casos por un objeto de tres atributos los vuelve lentos sin
    verificar nada más.
    """

    def __init__(self, *, ruta='ACCIONES_CONSTITUCIONALES', radicado='T-2026-451',
                 autorizada_por='KLMUÑOZM'):
        self.ruta = ruta
        self.radicado = radicado
        self.autorizada_por = type('U', (), {'codigo_usuario': autorizada_por})()

    def get_ruta_display(self):
        return self.ruta.replace('_', ' ').capitalize()


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
def test_ninguna_ruta_levanta_el_bloqueo_por_si_sola(ruta):
    """
    Cambio del 14-ago-2026. La ruta sigue siendo la que omite la vigencia según
    el manual, pero **elegirla ya no basta**: hace falta que la excepción esté
    autorizada desde el front.

    Antes alcanzaba con elegirla en el celular y adjuntar una foto, o sea que
    quien ejecutaba el salto de control era el mismo que lo autorizaba. La
    operación además indicó que el caracterizador no debe tener el documento.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(), ruta=ruta,
                                       habilitacion=None)

    assert not veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert not veredicto.por_excepcion
    # El mensaje tiene que decir a dónde ir. Sin esto el encuestador cree que la
    # app falló, que es exactamente lo que reportó el territorio la vez pasada.
    assert 'plataforma web' in veredicto.mensaje


@pytest.mark.parametrize('ruta', sorted(RUTAS_QUE_OMITEN_VIGENCIA))
def test_con_la_excepcion_autorizada_si_se_levanta(ruta):
    """Autorizada desde el front, la persona pasa — por cualquiera de las tres."""
    habilitacion = _Habilitacion(ruta=ruta)

    veredicto = describir_elegibilidad(_con_ficha_vigente(), ruta=ruta,
                                       habilitacion=habilitacion)

    assert veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_POR_EXCEPCION
    assert veredicto.por_excepcion


def test_la_habilitacion_levanta_el_bloqueo_aunque_no_se_pase_ruta():
    """
    El encuestador no tiene que volver a elegir la ruta: ya la eligió quien
    autorizó. Si hubiera que elegirla otra vez en el celular, una habilitación
    otorgada se vería como bloqueo hasta acertar con la misma opción.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(),
                                       habilitacion=_Habilitacion())

    assert veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_POR_EXCEPCION


def test_el_mensaje_de_la_habilitacion_dice_quien_autorizo_y_con_que_radicado():
    """
    Es lo que convierte "puede continuar" en algo que el encuestador puede
    defender si alguien le pregunta por qué recaracterizó a una persona con
    ficha vigente.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(),
                                       habilitacion=_Habilitacion(radicado='T-2026-451'))

    assert 'T-2026-451' in veredicto.mensaje
    assert 'KLMUÑOZM' in veredicto.mensaje


def test_sin_ruta_ni_habilitacion_el_bloqueo_sigue_en_pie():
    """
    La búsqueda normal no pasa ruta: primero se ve el estado real, y recién si
    hay ficha vigente se solicita la excepción.
    """
    veredicto = describir_elegibilidad(_con_ficha_vigente(), habilitacion=None)

    assert not veredicto.elegible
    assert veredicto.motivo == MotivoNoElegible.FICHA_VIGENTE
    assert not veredicto.por_excepcion


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
    """Si no tenía ficha vigente, la ruta no cambia nada: es elegible a secas."""
    libre = _Victima(habilitado=True)

    veredicto = describir_elegibilidad(libre, ruta='ACCIONES_CONSTITUCIONALES')
    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE
    assert not veredicto.por_excepcion


# ── Lo que ve el encuestador ─────────────────────────────────────────────────

def test_la_excepcion_igual_le_dice_que_habia_ficha_vigente():
    """
    Que pueda continuar no significa ocultarle el dato: tiene que saber que
    está recaracterizando a alguien con entrevista vigente.
    """
    v = describir_elegibilidad(_con_ficha_vigente(), habilitacion=_Habilitacion())

    assert '14/03/2026' in v.mensaje
    assert '14/03/2028' in v.mensaje
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


# ── El cable: que la ruta llegue de verdad desde la API ──────────────────────
#
# La lógica de arriba estaba escrita y probada, pero NADIE le pasaba la ruta:
# los tres llamados a `describir_elegibilidad` iban sin ella y el serializer no
# la aceptaba. O sea que la excepción era inalcanzable desde la app — la parte
# más fácil de olvidar y la única que el encuestador nota.

@pytest.fixture
def victima_con_ficha_vigente(db):
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    return Victima.objects.create(
        tipo_documento=tipo,
        numero_documento='1115724047',
        primer_nombre='ANA', primer_apellido='GOMEZ',
        fecha_nacimiento='1990-01-01', genero='F',
        estado_ruv='INCLUIDO',
        habilitado_para_caracterizacion=False,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )


def _autorizar(victima, ruta='ACCIONES_CONSTITUCIONALES'):
    """Lo que hace el front en `POST /api/habilitaciones/`."""
    from apps.encuestas.models import ExcepcionVigencia

    return ExcepcionVigencia.objects.create(
        victima=victima, ruta=ruta, radicado='T-2026-451',
        observacion='Fallo de tutela que ordena caracterizar de nuevo.',
        estado=ExcepcionVigencia.VIGENTE,
    )


def test_el_repositorio_bloquea_hasta_que_la_excepcion_este_autorizada(
        victima_con_ficha_vigente):
    """
    El recorrido completo del cambio: la ruta sola no alcanza; cuando el front
    autoriza, la misma búsqueda pasa a devolver elegible.
    """
    from apps.victimas.repository import DjangoVictimaRepository

    repo = DjangoVictimaRepository()

    sin_ruta = repo.buscar_por_documento('CC', '1115724047')
    assert sin_ruta.motivo == MotivoNoElegible.FICHA_VIGENTE

    con_ruta = repo.buscar_por_documento('CC', '1115724047',
                                         ruta='ACCIONES_CONSTITUCIONALES')
    assert con_ruta.motivo == MotivoNoElegible.FICHA_VIGENTE, (
        'elegir la ruta en el celular ya no habilita — 14-ago-2026')

    _autorizar(victima_con_ficha_vigente)

    autorizada = repo.buscar_por_documento('CC', '1115724047')
    assert autorizada.motivo == MotivoNoElegible.ELEGIBLE_POR_EXCEPCION
    assert 'T-2026-451' in autorizada.mensaje

    # El defecto que encontro el trazado E2E: el motivo cambiaba, pero
    # habilitado_para_caracterizacion seguia en False, y la APK decide por ESE
    # campo -> la persona autorizada quedaba bloqueada en linea. El DTO debe
    # reflejar que si puede caracterizarse ahora.
    assert autorizada.victima.habilitado_para_caracterizacion is True, (
        'la excepcion vigente debe habilitar en el DTO que lee la APK')
    assert autorizada.victima.habilitada_por_excepcion is True


def test_una_habilitacion_ya_usada_no_vuelve_a_habilitar(victima_con_ficha_vigente):
    """
    Es de un solo uso. Si siguiera sirviendo, esa persona quedaría con permiso
    permanente para saltarse la regla de los dos años.
    """
    from apps.victimas.repository import DjangoVictimaRepository

    habilitacion = _autorizar(victima_con_ficha_vigente)
    habilitacion.marcar_usada()

    r = DjangoVictimaRepository().buscar_por_documento('CC', '1115724047')
    assert r.motivo == MotivoNoElegible.FICHA_VIGENTE


def test_una_habilitacion_anulada_no_habilita(victima_con_ficha_vigente):
    from apps.victimas.repository import DjangoVictimaRepository

    habilitacion = _autorizar(victima_con_ficha_vigente)
    habilitacion.anular(None, 'Se autorizó sobre la persona equivocada.')

    r = DjangoVictimaRepository().buscar_por_documento('CC', '1115724047')
    assert r.motivo == MotivoNoElegible.FICHA_VIGENTE


def test_verificar_habilitacion_ve_lo_mismo_que_la_busqueda(victima_con_ficha_vigente):
    """
    Las dos puertas de entrada tienen que responder igual sobre la misma
    persona. Ya divergieron una vez en el texto, y una app que dice una cosa en
    la búsqueda y otra en la ficha es un defecto esperando a ocurrir.
    """
    from apps.victimas.repository import DjangoVictimaRepository

    repo = DjangoVictimaRepository()
    assert repo.verificar_habilitacion('CC', '1115724047').habilitado is False
    assert repo.verificar_habilitacion(
        'CC', '1115724047', ruta='ESPECIAL').habilitado is False

    _autorizar(victima_con_ficha_vigente, ruta='ESPECIAL')

    assert repo.verificar_habilitacion('CC', '1115724047').habilitado is True


def test_el_serializer_de_entrada_acepta_la_ruta():
    """Sin esto la app no tiene por dónde mandarla y el resto no sirve."""
    from apps.victimas.serializers import ConsultarFuenteInputSerializer

    s = ConsultarFuenteInputSerializer(data={
        'tipo_documento': 'cc',
        'numero_documento': '1115724047',
        'ruta_entrevista': 'acciones_constitucionales',
    })
    assert s.is_valid(), s.errors
    assert s.validated_data['ruta_entrevista'] == 'ACCIONES_CONSTITUCIONALES'


def test_la_ruta_es_opcional_y_su_ausencia_no_rompe_nada():
    from apps.victimas.serializers import ConsultarFuenteInputSerializer

    s = ConsultarFuenteInputSerializer(data={
        'tipo_documento': 'CC', 'numero_documento': '1115724047'})
    assert s.is_valid(), s.errors
    assert s.validated_data.get('ruta_entrevista', '') == ''


# ── La regla de 2 años es real y NO se deroga ───────────────────────────────
#
# Confirmado por Javier el 5-ago-2026. Un análisis previo la marcó como "sin
# fuente citada" y esa observación era incorrecta. Estos tests la fijan: si
# alguien la cambia, tiene que ser una decisión, no un descuido.

def test_la_vigencia_es_de_dos_anios():
    from apps.victimas.homologacion import ANIOS_VIGENCIA_CARACTERIZACION
    assert ANIOS_VIGENCIA_CARACTERIZACION == 2


def test_la_ruta_general_SIEMPRE_respeta_la_vigencia():
    """
    Es el caso por defecto y el que sostiene la regla. Si la General dejara de
    respetarla, la vigencia dejaría de existir en la práctica: es la ruta que
    usa la inmensa mayoría de las entrevistas.
    """
    assert 'GENERAL' not in RUTAS_QUE_OMITEN_VIGENCIA
    assert ruta_omite_vigencia('GENERAL') is False

    v = describir_elegibilidad(_con_ficha_vigente(), ruta='GENERAL')
    assert not v.elegible
    assert v.motivo == MotivoNoElegible.FICHA_VIGENTE


def test_una_ficha_de_hace_menos_de_dos_anios_sigue_vigente():
    from apps.victimas.homologacion import debe_recaracterizarse

    hoy = datetime.date(2026, 8, 5)
    assert debe_recaracterizarse(datetime.date(2025, 8, 5), hoy=hoy) is False   # 1 año
    assert debe_recaracterizarse(datetime.date(2024, 8, 6), hoy=hoy) is False   # 1 año 364 d
    assert debe_recaracterizarse(datetime.date(2024, 8, 5), hoy=hoy) is True    # 2 años justos
    assert debe_recaracterizarse(datetime.date(2020, 1, 1), hoy=hoy) is True    # vencida


def test_sin_fecha_se_debe_recaracterizar():
    """Nunca caracterizada es justamente a quien hay que caracterizar."""
    from apps.victimas.homologacion import debe_recaracterizarse
    assert debe_recaracterizarse(None) is True
