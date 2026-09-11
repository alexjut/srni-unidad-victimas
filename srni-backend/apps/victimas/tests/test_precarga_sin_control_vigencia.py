"""
La precarga de la jornada tiene que reflejar el retiro del control.

─── Por qué esto es lo que hace que el interruptor sirva ────────────────────
En campo la APK no pregunta: consulta el padrón que descargó al iniciar sesión.
Si el servidor retira el control pero la precarga sigue entregando
`habilitada=False`, el celular sigue bloqueando **justo donde no hay red para
preguntar de nuevo** — o sea, donde se pidió el cambio. El retiro se notaría en
la oficina y no en el territorio.

Resolverlo en el servidor y no en la app tiene una ventaja concreta: **funciona
con las APK ya instaladas**. Mover el interruptor no exige una build nueva.

─── Lo que no se abre ───────────────────────────────────────────────────────
Retirar la vigencia no es abrir todo. Quien está excluida del RUV sigue
bloqueada: eso es una decisión jurídica sobre la condición de víctima, no un
control de frescura del dato, y ninguna ruta de excepción la habilitaba tampoco.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

# `VICTIMA_REPOSITORY` cae en 'MOCK' por defecto (ver `get_repository`), y el mock
# entrega fichas estáticas con `habilitada` fija. Este archivo mide el padrón REAL
# —el que la precarga entrega en producción—, así que se fija el repositorio de
# Django para todos los casos. Sin esto los asertos miden el mock y pasan o fallan
# por razones que no tienen nada que ver con el interruptor.
pytestmark = [pytest.mark.django_db,
              pytest.mark.usefixtures('repositorio_django')]


@pytest.fixture
def repositorio_django(settings):
    settings.VICTIMA_REPOSITORY = 'DJANGO'

URL = '/api/victimas/precarga/'

CARACTERIZADA_EL = datetime.datetime(2026, 3, 14, 10, 0,
                                     tzinfo=datetime.timezone.utc)


@pytest.fixture
def escenario(db):
    from apps.autenticacion.models import Perfil, Usuario
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')

    def victima(doc, nombre, **extra):
        campos = dict(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            pertenencia_etnica='NINGUNA', discapacidad=False,
        )
        campos.update(extra)
        return Victima.objects.create(**campos)

    perfil = Perfil.objects.create(
        codigo='ENC_PRE', nombre='Encuestador', activo=True,
        puede_caracterizar=True, puede_buscar_rni=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='PRETEST', password='SrniTest2026!',
        nombre_completo='Pre Test', email='pre@srni.dev', perfil=perfil,
        activo=True)

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)

    return {
        'cliente': cliente,
        # Ficha vigente: caracterizada hace menos de dos años.
        'vigente': victima('1030547250', 'MARIA',
                           habilitado_para_caracterizacion=False,
                           fecha_ult_caracterizacion=CARACTERIZADA_EL),
        # Excluida del RUV **y** con ficha vigente: los dos motivos a la vez, para
        # que se vea que el interruptor levanta uno y no el otro.
        'excluida': victima('9990100002', 'LUZ', estado_ruv='EXCLUIDO',
                            habilitado_para_caracterizacion=False,
                            fecha_ult_caracterizacion=CARACTERIZADA_EL),
        # Nunca caracterizada: ya estaba habilitada por la vía normal.
        'nueva': victima('9990100003', 'SOFIA',
                         habilitado_para_caracterizacion=True),
    }


def _padron(escenario):
    r = escenario['cliente'].get(URL)
    assert r.status_code == 200, r.data
    return {fila['documento']: fila for fila in r.data['padron']}


# ── Con el control activo: nada cambia ───────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_la_ficha_vigente_va_bloqueada(escenario):
    """El default. Si esto falla, el cambio se filtró a producción sin firma."""
    padron = _padron(escenario)

    assert padron['1030547250']['habilitada'] is False


# ── Con el control retirado ──────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_la_ficha_vigente_viaja_habilitada(escenario):
    """
    Lo esencial: es este campo el que la APK usa sin señal para decidir si deja
    continuar. Sin esto, el encuestador en territorio seguiría viendo «No
    habilitado» con el control ya retirado en el servidor.
    """
    padron = _padron(escenario)

    assert padron['1030547250']['habilitada'] is True


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_la_excluida_del_RUV_sigue_bloqueada(escenario):
    padron = _padron(escenario)

    assert padron['9990100002']['habilitada'] is False


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_quien_ya_estaba_habilitada_sigue_habilitada(escenario):
    padron = _padron(escenario)

    assert padron['9990100003']['habilitada'] is True


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_dato_de_que_ya_fue_caracterizada_no_se_pierde(escenario):
    """
    `habilitada` cambia; `ya_caracterizada` no. Son dos cosas distintas y la APK
    usa la segunda para el mensaje: el encuestador tiene que poder ver que a esta
    persona ya la caracterizaron, aunque el sistema lo deje continuar.

    Perderlo dejaría al encuestador recaracterizando sin saber que lo hace.
    """
    padron = _padron(escenario)

    fila = padron['1030547250']
    assert fila['habilitada'] is True
    assert fila['ya_caracterizada'] is True
