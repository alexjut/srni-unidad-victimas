"""
El cliente no decide la vigencia. Es lo que salva el libro de auditoría.

─── El defecto, que no se veía por ninguna parte ────────────────────────────
`registrar-desde-fuente` hace *upsert*: crea la ficha si no existe y la actualiza
si existe. Actualizaba `habilitado_para_caracterizacion` con el valor que mandó el
cliente, y eso, con el control de vigencia retirado, **vaciaba el registro de
recaracterizaciones sin que nada fallara**.

La cadena, medida:

  1. con el control retirado, la búsqueda responde `habilitado=True` para quien
     tiene ficha vigente — y es correcto: significa «puede caracterizarse ahora»;
  2. la aplicación reenvía ese resumen COMPLETO al conformar el hogar;
  3. si se escribía, la columna quedaba en `True`;
  4. `describir_elegibilidad` corta en la columna antes de evaluar la vigencia, así
     que el veredicto pasaba de `ELEGIBLE_SIN_CONTROL_VIGENCIA` a `ELEGIBLE`;
  5. al cerrar la encuesta, `RecaracterizacionVigente.registrar` exige
     `veredicto.sobre_ficha_vigente` y **no anotaba nada**.

La recaracterización ocurría, el encuestador no veía diferencia, y el libro —lo
único que se conservó al retirar el control— quedaba vacío. Ninguna prueba de humo
lo habría notado: todo respondía 200.

─── Qué se fija ─────────────────────────────────────────────────────────────
El campo se acepta solo en un alta NUEVA, donde el payload es el único dato que
existe y no hay fila previa cuyo estado pisar. Sobre una ficha del padrón que ya
existe, el estado de vigencia lo decide `describir_elegibilidad` y nadie más.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/victimas/registrar-desde-fuente/'

CARACTERIZADA_EL = datetime.datetime(2026, 3, 14, 10, 0,
                                    tzinfo=datetime.timezone.utc)


@pytest.fixture
def escenario(db):
    from apps.autenticacion.models import Perfil, Usuario
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')

    perfil = Perfil.objects.create(
        codigo='ENC_AV', nombre='Encuestador', activo=True,
        puede_caracterizar=True, puede_buscar_rni=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='AVTEST', password='SrniTest2026!', nombre_completo='AV Test',
        email='av@srni.dev', perfil=perfil, activo=True)

    # Ficha vigente: caracterizada hace menos de dos años y por tanto bloqueada
    # por la columna cuando el control está activo.
    con_ficha = Victima.objects.create(
        tipo_documento=tipo, numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', primer_apellido='PEREZ', genero='F',
        estado_ruv='INCLUIDO', habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        fecha_ult_caracterizacion=CARACTERIZADA_EL)

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return {'cliente': cliente, 'con_ficha': con_ficha, 'tipo': tipo}


def _reenviar(escenario, documento='1030547250', habilitado=True, **extra):
    """
    Lo que la aplicación manda al conformar el hogar: el resumen COMPLETO de la
    persona, tal como lo recibió de la búsqueda.
    """
    cuerpo = {
        'tipo_documento': 'CC',
        'numero_documento': documento,
        'primer_nombre': 'MARIA',
        'primer_apellido': 'PEREZ',
        'genero': 'F',
        'estado_ruv': 'INCLUIDO',
        'habilitado_para_caracterizacion': habilitado,
        'fuente_origen': 'RUV',
    }
    cuerpo.update(extra)
    return escenario['cliente'].post(URL, cuerpo, format='json')


# ── Lo esencial ──────────────────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_reenviar_el_resumen_no_pisa_la_columna_de_una_ficha_existente(escenario):
    """
    El aserto que salva el libro. Si la columna queda en True,
    `describir_elegibilidad` deja de ver la ficha vigente y la recaracterización no
    se anota — sin error, sin aviso y sin forma de notarlo después.
    """
    from apps.victimas.models import Victima

    r = _reenviar(escenario, habilitado=True)

    assert r.status_code in (200, 201), r.data
    v = Victima.objects.get(id=escenario['con_ficha'].id)
    assert v.habilitado_para_caracterizacion is False


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_veredicto_sigue_diciendo_que_habia_ficha_vigente(escenario):
    """
    La consecuencia de lo anterior, comprobada donde importa: en el veredicto, que
    es lo que decide si se escribe el registro al cerrar la encuesta.
    """
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import (MotivoNoElegible,
                                               describir_elegibilidad)

    _reenviar(escenario, habilitado=True)

    v = Victima.objects.get(id=escenario['con_ficha'].id)
    veredicto = describir_elegibilidad(v, habilitacion=None)

    assert veredicto.motivo == MotivoNoElegible.ELEGIBLE_SIN_CONTROL_VIGENCIA
    assert veredicto.sobre_ficha_vigente is True
    assert veredicto.elegible is True          # puede caracterizarse, y se anota


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_la_fecha_de_la_caracterizacion_anterior_no_se_borra(escenario):
    """
    Es el otro dato del que depende el registro: sin la fecha anterior no se puede
    calcular con cuánta anticipación se recaracterizó.
    """
    from apps.victimas.models import Victima

    _reenviar(escenario, habilitado=True)

    v = Victima.objects.get(id=escenario['con_ficha'].id)
    assert v.fecha_ult_caracterizacion is not None


# ── Lo que sí se sigue actualizando ──────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_los_demas_campos_si_se_actualizan(escenario):
    """
    No se congela la ficha: lo que el encuestador corrige en campo con la persona
    enfrente sigue entrando. Lo único que el cliente no decide es la vigencia.
    """
    from apps.victimas.models import Victima

    _reenviar(escenario, habilitado=True, segundo_nombre='LUCIA',
              segundo_apellido='GOMEZ')

    v = Victima.objects.get(id=escenario['con_ficha'].id)
    assert v.segundo_nombre == 'LUCIA'
    assert v.segundo_apellido == 'GOMEZ'


# ── El alta nueva sí lo acepta ───────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_en_un_alta_nueva_se_acepta_el_valor_del_cliente(escenario):
    """
    Ahí el payload es el único dato que existe: la persona está enfrente del
    encuestador, no hay fila previa y nada que pisar. Negárselo dejaría al alta
    manual sin poder decir que la persona puede caracterizarse.
    """
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    r = _reenviar(escenario, documento='9990100099', habilitado=True)

    assert r.status_code in (200, 201), r.data
    # Por el hash y no por el número: `numero_documento` es un campo cifrado, así
    # que filtrar por su valor en claro no cruza con el texto cifrado que hay en la
    # columna y la consulta no devuelve nada.
    nueva = Victima.objects.get(
        numero_documento_hash=doc_hash('CC', '9990100099'))
    assert nueva.habilitado_para_caracterizacion is True


# ── Con el control activo tampoco se pisa ────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_tampoco_se_pisa(escenario):
    """
    El defecto no era propio del retiro: un cliente que mandara True liberaba una
    ficha vigente igual, y ahí el daño era mayor —se saltaba la regla de los dos
    años sin autorización y sin registro de ningún tipo—. Solo era más difícil de
    provocar, porque la búsqueda no devolvía True.
    """
    from apps.victimas.models import Victima

    _reenviar(escenario, habilitado=True)

    v = Victima.objects.get(id=escenario['con_ficha'].id)
    assert v.habilitado_para_caracterizacion is False
