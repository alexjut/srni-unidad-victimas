"""
El segundo muro: la sesión de encuesta del compañero.

─── Lo que este archivo protege ─────────────────────────────────────────────
Retirar el control de vigencia abrió tres puertas en cadena, y cada una tapaba a
la siguiente:

    1. ficha vigente        → «no se puede recaracterizar»
    2. un hogar activo      → «ya tiene un hogar de otro encuestador»
    3. una sesión activa    → «ya tiene una sesión iniciada por otro encuestador»

Se abrieron las dos primeras y la tercera quedó viva, con el mismo mensaje sin
salida: «solicita su reasignación al supervisor», un trámite que no existe. El
encuestador recibía el hogar en la mano, podía abrirlo y agregar integrantes, y al
iniciar la entrevista chocaba.

El caso no es raro: basta que el compañero haya dejado una entrevista sin cerrar,
o que su cierre siga en la cola esperando señal.

**Y falla peor de lo que parece.** En la aplicación esto ocurre dentro de la
sincronización: la creación de la sesión queda en error y las respuestas y el
cierre esperan detrás de un identificador que nunca llega. No se pierde un paso,
se pierde la entrevista completa.
"""
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/encuestas/'


@pytest.fixture
def escenario(db):
    """
    Un hogar de ENCUNO con una entrevista **sin cerrar**, y ENCDOS enfrente de la
    misma persona.

    La sesión va EN_PROGRESO y no COMPLETADA a propósito: el `create` excluye las
    completadas, así que con una cerrada el caso pasa limpio y la prueba no mediría
    nada. El bloqueo vive exactamente en la entrevista abandonada.
    """
    from apps.autenticacion.models import Perfil, Usuario
    from apps.encuestas.models import SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)

    def usuario(codigo):
        perfil = Perfil.objects.create(
            codigo=f'P_{codigo}', nombre=codigo, activo=True,
            puede_caracterizar=True, puede_buscar_rni=True)
        return Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!', nombre_completo=codigo,
            email=f'{codigo}@srni.dev', perfil=perfil, activo=True)

    uno, dos = usuario('ENCUNO'), usuario('ENCDOS')

    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento='1030547250',
        numero_documento_hash=doc_hash('CC', '1030547250'),
        primer_nombre='MARIA', primer_apellido='PEREZ', genero='F',
        estado_ruv='INCLUIDO', habilitado_para_caracterizacion=False,
        pertenencia_etnica='NINGUNA', discapacidad=False,
        municipio_residencia=muni,
        fecha_ult_caracterizacion=datetime.datetime(
            2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
    )

    hogar = Hogar.objects.create(autorizado=victima, creado_por=uno,
                                 municipio=muni, estado='ACTIVO')
    MiembroHogar.objects.create(hogar=hogar, victima=victima, es_autorizado=True,
                                rol='MIEMBRO', estado_inclusion='INCLUIDO',
                                creado_por=uno)

    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))

    # La entrevista que ENCUNO dejó abierta.
    abandonada = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=instrumento, encuestador=uno,
        estado='EN_PROGRESO')

    def cliente_de(u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return {
        'hogar': hogar, 'instrumento': instrumento, 'abandonada': abandonada,
        'uno': uno, 'dos': dos,
        'cli_uno': cliente_de(uno), 'cli_dos': cliente_de(dos),
    }


def _crear_sesion(cliente, escenario):
    return cliente.post(URL, {
        'hogar': str(escenario['hogar'].id),
        'instrumento': str(escenario['instrumento'].id),
    }, format='json')


# ── Con el control activo: el comportamiento histórico ───────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True})
def test_con_el_control_activo_la_sesion_ajena_sigue_dando_409(escenario):
    """El default no cambia. Si esto falla, el cambio se filtró sin firma."""
    r = _crear_sesion(escenario['cli_dos'], escenario)

    assert r.status_code == 409
    assert 'otro encuestador' in r.data['detail']


# ── Con el control retirado ──────────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_sin_control_el_segundo_encuestador_puede_iniciar_su_entrevista(escenario):
    """
    El aserto que cierra la cadena. Sin él, abrir el hogar sirve de poco: el
    encuestador llega con la persona enfrente hasta el último paso y ahí se detiene.
    """
    r = _crear_sesion(escenario['cli_dos'], escenario)

    assert r.status_code == 201, r.data


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_la_sesion_nueva_queda_a_nombre_de_quien_la_creo(escenario):
    """
    La autoría vive en la sesión, que es donde siempre debió estar. Es lo que
    permite que el hogar deje de tener dueño exclusivo sin perder quién hizo qué.
    """
    from apps.encuestas.models import SesionEncuesta

    r = _crear_sesion(escenario['cli_dos'], escenario)

    nueva = SesionEncuesta.objects.get(id=r.data['id'])
    assert nueva.encuestador_id == escenario['dos'].id


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_la_entrevista_del_companero_no_se_toca(escenario):
    """
    No se reasigna ni se cierra la del otro: es trabajo suyo, a medias, y puede
    volver a terminarlo. Dos sesiones sobre el mismo hogar es exactamente lo que el
    libro de recaracterizaciones va a mostrar.
    """
    from apps.encuestas.models import SesionEncuesta

    _crear_sesion(escenario['cli_dos'], escenario)

    previa = SesionEncuesta.objects.get(id=escenario['abandonada'].id)
    assert previa.encuestador_id == escenario['uno'].id
    assert previa.estado == 'EN_PROGRESO'
    assert SesionEncuesta.objects.filter(hogar=escenario['hogar']).count() == 2


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_el_segundo_encuestador_puede_navegar_su_propia_sesion(escenario):
    """
    Crearla y no poder abrirla sería el mismo callejón un paso más adelante: el
    listado de encuestas filtra por encuestador, así que la suya tiene que aparecer.
    """
    r = _crear_sesion(escenario['cli_dos'], escenario)

    detalle = escenario['cli_dos'].get(f"{URL}{r.data['id']}/")
    assert detalle.status_code == 200


# ── La idempotencia no se pierde ─────────────────────────────────────────────

@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_pedir_dos_veces_la_sesion_devuelve_la_misma(escenario):
    """
    La aplicación reintenta cuando la red se corta. Si el segundo intento creara
    otra sesión, el mismo hogar acumularía entrevistas vacías del mismo encuestador
    y el porcentaje de avance se repartiría entre ellas.
    """
    from apps.encuestas.models import SesionEncuesta

    primera = _crear_sesion(escenario['cli_dos'], escenario)
    segunda = _crear_sesion(escenario['cli_dos'], escenario)

    assert segunda.status_code == 200
    assert segunda.data['id'] == primera.data['id']
    assert SesionEncuesta.objects.filter(
        hogar=escenario['hogar'], encuestador=escenario['dos']).count() == 1


@override_settings(VIGENCIA={'BLOQUEO_ACTIVO': False})
def test_una_sesion_completada_del_companero_nunca_estorbo(escenario):
    """
    Contracara, para dejar claro dónde estaba el problema: el `create` excluye las
    COMPLETADAS, así que ese caso pasaba limpio desde antes. El bloqueo era la
    entrevista ABANDONADA, que es la que ocurre de verdad en campo.
    """
    escenario['abandonada'].estado = 'COMPLETADA'
    escenario['abandonada'].save(update_fields=['estado'])

    with override_settings(VIGENCIA={'BLOQUEO_ACTIVO': True}):
        r = _crear_sesion(escenario['cli_dos'], escenario)

    assert r.status_code == 201, r.data
