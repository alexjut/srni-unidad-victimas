"""
La excepción de vigencia se autoriza desde el front, no desde el celular.

Cambio del 14-ago-2026. Hasta entonces el encuestador elegía la ruta en campo y
adjuntaba una foto del fallo desde el teléfono. La operación indicó que **el
caracterizador no debe tener ese documento**: llega por canal institucional al
nivel central.

Lo que estos tests fijan es el reparto de poder que resultó del cambio — quien
autoriza el salto de un control dejó de ser quien lo ejecuta— y que la
habilitación no se convierta en un permiso permanente.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/habilitaciones/'


@pytest.fixture
def escenario(db):
    import datetime

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
            habilitado_para_caracterizacion=False,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            fecha_ult_caracterizacion=datetime.datetime(
                2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc),
        )
        campos.update(extra)
        return Victima.objects.create(**campos)

    def usuario(codigo, **flags):
        perfil = Perfil.objects.create(
            codigo=f'P_{codigo}', nombre=codigo, activo=True, **flags)
        return Usuario.objects.create_user(
            codigo_usuario=codigo, password='SrniTest2026!',
            nombre_completo=codigo, email=f'{codigo}@srni.dev',
            perfil=perfil, activo=True)

    coordinador = usuario('COORDTEST', puede_caracterizar=True, puede_buscar_rni=True,
                          puede_ver_reportes=True, puede_autorizar_excepciones=True)
    encuestador = usuario('ENCTEST', puede_caracterizar=True, puede_buscar_rni=True)
    documentador = usuario('DOCTEST', puede_caracterizar=False, puede_buscar_rni=True,
                           puede_ver_reportes=True)

    def cliente_de(u):
        c = APIClient()
        c.force_authenticate(user=u)
        return c

    return {
        'victima': victima('1115724047', 'ANA'),
        'coordinador': cliente_de(coordinador),
        'encuestador': cliente_de(encuestador),
        'documentador': cliente_de(documentador),
        'usuario_coordinador': coordinador,
        'usuario_encuestador': encuestador,
    }


def _payload(victima, **extra):
    datos = {
        'victima_id': str(victima.id),
        'ruta': 'ACCIONES_CONSTITUCIONALES',
        'radicado': 'T-2026-451',
        'observacion': 'Fallo de tutela que ordena caracterizar de nuevo al hogar.',
    }
    datos.update(extra)
    return datos


# ── Quién puede y quién no ───────────────────────────────────────────────────

def test_la_coordinacion_autoriza_la_excepcion(escenario):
    r = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                      format='json')

    assert r.status_code == 201, r.data
    assert r.data['estado'] == 'VIGENTE'
    assert r.data['radicado'] == 'T-2026-451'
    assert r.data['autorizada_por_codigo'] == 'COORDTEST'
    # La situación que la justificó queda congelada: si después se
    # recaracteriza, la fecha de la víctima cambia y se perdería el motivo.
    assert r.data['vigente_hasta'] == '2028-03-14'


def test_el_encuestador_NO_puede_autorizarse_a_si_mismo(escenario):
    """
    El corazón del cambio. Si el que ejecuta puede autorizar, la regla de
    vigencia vuelve a ser opcional en la práctica — que es como estaba antes.
    """
    r = escenario['encuestador'].post(URL, _payload(escenario['victima']),
                                      format='json')

    assert r.status_code == 403


def test_el_documentador_tampoco_aunque_vea_reportes(escenario):
    """
    Se creó de solo lectura a propósito (11-ago). Habilitar una excepción altera
    la caracterización de una víctima: colgar este permiso de `ver_reportes` le
    daría por la puerta de atrás justo lo que se le negó de frente.
    """
    r = escenario['documentador'].post(URL, _payload(escenario['victima']),
                                       format='json')

    assert r.status_code == 403


# ── Lo que exige para autorizar ──────────────────────────────────────────────

def test_sin_radicado_no_se_autoriza(escenario):
    r = escenario['coordinador'].post(URL, _payload(escenario['victima'], radicado=''),
                                      format='json')
    assert r.status_code == 400
    assert 'radicado' in r.data


def test_un_motivo_de_dos_palabras_no_es_un_motivo(escenario):
    r = escenario['coordinador'].post(
        URL, _payload(escenario['victima'], observacion='ok'), format='json')
    assert r.status_code == 400


def test_la_ruta_general_no_tiene_excepcion_que_autorizar(escenario):
    """La General respeta la vigencia: no hay nada que levantar."""
    r = escenario['coordinador'].post(
        URL, _payload(escenario['victima'], ruta='GENERAL'), format='json')

    assert r.status_code == 400
    assert 'no omite' in str(r.data['ruta']).lower()


def test_el_archivo_es_opcional(escenario):
    """
    Decidido el 14-ago: exigirlo dejaría fuera los casos que llegan por correo o
    por teléfono, y el radicado ya permite ir a buscar el documento.
    """
    r = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                      format='json')
    assert r.status_code == 201
    assert r.data['soporte_nombre'] == ''


def test_no_se_habilita_a_una_excluida_del_RUV(escenario):
    """
    El manual da la excepción para fichas vigentes, no para revertir una
    decisión del RUV. Sin esta guarda el front otorgaría una habilitación que la
    app después ignora, y nadie entendería por qué.
    """
    victima = escenario['victima']
    victima.estado_ruv = 'EXCLUIDO'
    victima.save(update_fields=['estado_ruv'])

    r = escenario['coordinador'].post(URL, _payload(victima), format='json')

    assert r.status_code == 409
    assert 'excluida del RUV' in r.data['detail']


def test_no_se_apilan_dos_habilitaciones_sobre_la_misma_persona(escenario):
    primera = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                            format='json')
    assert primera.status_code == 201

    segunda = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                            format='json')

    assert segunda.status_code == 409
    # Devuelve la que ya existe: quien intentó autorizar de nuevo necesita ver
    # cuál es, no solo que no se pudo.
    assert segunda.data['habilitacion']['radicado'] == 'T-2026-451'


# ── Anular ───────────────────────────────────────────────────────────────────

def test_anular_deja_rastro_y_no_borra(escenario):
    from apps.encuestas.models import ExcepcionVigencia

    creada = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                           format='json')
    hid = creada.data['id']

    r = escenario['coordinador'].post(
        f'{URL}{hid}/anular/',
        {'motivo': 'Se autorizó sobre la persona equivocada.'}, format='json')

    assert r.status_code == 200
    assert r.data['estado'] == 'ANULADA'
    # Sigue existiendo: una autorización otorgada y retirada es justamente lo
    # que una auditoría necesita poder ver.
    assert ExcepcionVigencia.objects.filter(pk=hid).exists()


def test_no_se_anula_dos_veces(escenario):
    creada = escenario['coordinador'].post(URL, _payload(escenario['victima']),
                                           format='json')
    hid = creada.data['id']
    cuerpo = {'motivo': 'Se autorizó sobre la persona equivocada.'}

    escenario['coordinador'].post(f'{URL}{hid}/anular/', cuerpo, format='json')
    segunda = escenario['coordinador'].post(f'{URL}{hid}/anular/', cuerpo, format='json')

    assert segunda.status_code == 409


# ── La vía vieja quedó cerrada ───────────────────────────────────────────────

def test_el_endpoint_del_celular_responde_410_y_dice_a_donde_ir(escenario):
    """
    410 y no 404: una APK anterior a la v1.2.0 sigue instalada en campo, y un
    404 se lee como "falló la red" — manda al encuestador a buscar señal por un
    endpoint que no va a volver.
    """
    import datetime

    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import Departamento, Municipio

    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)
    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_H', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    hogar = Hogar.objects.create(autorizado=escenario['victima'], municipio=muni)

    from apps.encuestas.models import SesionEncuesta
    sesion = SesionEncuesta.objects.create(hogar=hogar, instrumento=instrumento,
                                           estado='INICIADA')

    r = escenario['encuestador'].post(
        f'/api/encuestas/{sesion.id}/excepcion-vigencia/',
        {'victima_id': str(escenario['victima'].id),
         'ruta': 'ACCIONES_CONSTITUCIONALES'})

    assert r.status_code == 410
    assert 'coordinación' in r.data['detail']


# ── El celular la ve sin señal ───────────────────────────────────────────────

def test_la_habilitacion_viaja_en_la_precarga_de_la_jornada(escenario, settings):
    """
    Si solo se pudiera consultar en línea, el caso quedaría igual de bloqueado
    que antes: la habilitación se otorga en la web y el encuestador está en
    territorio, donde muchas veces no hay señal.
    """
    # El default de tests es MOCK, que devuelve un padrón inventado. Acá hace
    # falta el repositorio real: lo que se verifica es justamente que el dato
    # salga de la base y llegue hasta la respuesta.
    settings.VICTIMA_REPOSITORY = 'DJANGO'
    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    r = escenario['encuestador'].get('/api/victimas/precarga/')

    assert r.status_code == 200
    fila = next(p for p in r.data['padron'] if p['documento'] == '1115724047')
    assert fila['habilitada_por_excepcion'] is True
    assert fila['excepcion_radicado'] == 'T-2026-451'


def test_al_finalizar_la_encuesta_la_habilitacion_se_consume(escenario):
    """
    De un solo uso. Si quedara vigente, esa persona tendría permiso permanente
    para saltarse la regla de los dos años.
    """
    import datetime

    from apps.encuestas.models import ExcepcionVigencia, SesionEncuesta
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar
    from apps.parametricas.models import Departamento, Municipio

    escenario['coordinador'].post(URL, _payload(escenario['victima']), format='json')

    depto = Departamento.objects.create(codigo_dane='08', nombre='Atlántico')
    muni = Municipio.objects.create(codigo_dane='08001', nombre='Barranquilla',
                                    departamento=depto)
    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL_C', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))
    hogar = Hogar.objects.create(autorizado=escenario['victima'], municipio=muni)
    # Con encuestador: el ViewSet le muestra al perfil de campo solo sus propias
    # sesiones, así que sin esto la finalización responde 404.
    sesion = SesionEncuesta.objects.create(
        hogar=hogar, instrumento=instrumento, estado='INICIADA',
        encuestador=escenario['usuario_encuestador'])

    r = escenario['encuestador'].post(f'/api/encuestas/{sesion.id}/finalizar/',
                                      {}, format='json')
    assert r.status_code in (200, 201), r.data

    habilitacion = ExcepcionVigencia.objects.get(victima=escenario['victima'])
    assert habilitacion.estado == ExcepcionVigencia.USADA
    assert habilitacion.usada_en_sesion_id == sesion.id
